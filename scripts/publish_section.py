#!/usr/bin/env python3
"""Deterministic publisher for one research section.

This is the DETERMINISTIC half of the pipeline. The non-deterministic research
(web search + reasoning) happens in the Claude Code Action step, which returns a
schema-validated JSON object as its ``structured_output``. This script never
calls an LLM — it only formats that JSON into Markdown and publishes it.

ONE ITEM -> ONE ISSUE. The structured output is an array (news items, hypotheses,
or papers grouped under themes). This script iterates that array and opens a
SEPARATE GitHub Issue per item, so each news item / paper / hypothesis is its own
tracked Issue (and its own Slack line linking to that Issue):

    structured JSON  ->  per-item Markdown  ->  one GitHub Issue each (+ file + Slack)

Usage (run once per enabled section):

    SECTION_JSON='{...}' python3 scripts/publish_section.py <news|hypotheses|related>

Inputs (environment):
    SECTION_JSON          the structured_output JSON string from Claude (required)
    OUTPUT_LANGUAGE       en | ja  (scaffolding language; default en)
    RESEARCH_TOPIC        topic string (falls back to config/research_topics.md)
    GITHUB_ISSUE_LABELS   comma-separated base labels (default none)
    ENABLE_GITHUB_ISSUE   create the Issues? default true
    ENABLE_FILE_OUTPUT    also write outputs/<date>-<section>-<n>.md? default false
    GITHUB_TOKEN          provided automatically by Actions (for the Issue)
    SLACK_WEBHOOK_URL     optional; the Slack line is skipped if unset

Security: never prints tokens or the Slack webhook URL (the helpers enforce this).
"""

from __future__ import annotations

import datetime
import json
import os
import sys

import i18n
from github_issue import base_labels, create_issue
from notify import emit, primary_link, spooling
from site_url import item_url
from slack_post import slack_escape

# section key -> (issue label tag, i18n display-name key, Slack emoji, combined-run order)
SECTIONS: dict[str, dict[str, object]] = {
    "news": {"tag": "research-news", "name_key": "section_news", "emoji": "📰", "order": 1},
    "hypotheses": {"tag": "hypothesis", "name_key": "section_hypotheses", "emoji": "💡", "order": 2},
    "related": {"tag": "related-work", "name_key": "section_related", "emoji": "📚", "order": 3},
}

_TRUE = {"1", "true", "yes", "on"}

# GitHub caps issue titles at 256 chars; keep room for the section prefix.
_MAX_TITLE = 200


def flag(name: str, default: bool) -> bool:
    """Read a boolean env flag; empty/unset returns ``default``."""
    raw = os.environ.get(name, "").strip().lower()
    if raw == "":
        return default
    return raw in _TRUE


def topic_from_config() -> str:
    """Fallback topic from config/research_topics.md (first few bullets)."""
    path = os.path.join(os.path.dirname(__file__), "..", "config", "research_topics.md")
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return ""
    topics: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## notes"):
            break
        if stripped.startswith("- "):
            topics.append(stripped[2:].strip())
    return ", ".join(topics[:3])


def _trim(text: str, limit: int = _MAX_TITLE) -> str:
    """Collapse whitespace and cap length so a value is safe as a title."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _header(topic: str, date: str) -> str:
    return f"**{i18n.t('topic_label')}:** {topic}  \n**{i18n.t('pub_date')}:** {date}\n"


# An "item" is one publishable unit: its own Issue title, body, and Slack title.
Item = dict[str, str]


def _dicts(value: object) -> list[dict]:
    """Keep only the dict elements of a list (the LLM JSON is untrusted, so a
    stray string/number/null must not crash the whole section). Mirrors the
    guard in ``publish_watch.py``."""
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def items_news(data: dict, topic: str, date: str) -> list[Item]:
    """One Issue per news item."""
    out: list[Item] = []
    for item in _dicts(data.get("items")):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        url = str(item.get("url", "")).strip()
        source = str(item.get("source", "")).strip()
        date_str = str(item.get("date", "")).strip()
        takeaway = str(item.get("takeaway", "")).strip()

        lines = [_header(topic, date)]
        meta = " · ".join(part for part in (source, date_str) if part)
        if meta:
            lines.append(f"**{i18n.t('pub_source')}:** {meta}")
        if url:
            lines.append(f"**{i18n.t('pub_link')}:** {url}")
        if takeaway:
            lines.append("")
            lines.append(takeaway)
        lines.append("")
        lines.append(i18n.t("pub_footer"))
        out.append({"title": title, "body": "\n".join(lines), "slack": title, "url": url})
    return out


def items_hypotheses(data: dict, topic: str, date: str) -> list[Item]:
    """One Issue per hypothesis (the statement is the title)."""
    out: list[Item] = []
    for hyp in _dicts(data.get("hypotheses")):
        statement = str(hyp.get("statement", "")).strip()
        if not statement:
            continue
        rationale = str(hyp.get("rationale", "")).strip()
        experiment = str(hyp.get("experiment", "")).strip()
        risk = str(hyp.get("risk", "")).strip()
        cite_title = str(hyp.get("citation_title", "")).strip()
        cite_url = str(hyp.get("citation_url", "")).strip()

        lines = [_header(topic, date), ""]
        if rationale:
            lines.append(f"- **{i18n.t('pub_rationale')}:** {rationale}")
        if experiment:
            lines.append(f"- **{i18n.t('pub_experiment')}:** {experiment}")
        if risk:
            lines.append(f"- **{i18n.t('pub_risk')}:** {risk}")
        if cite_title:
            source = f"[{cite_title}]({cite_url})" if cite_url else cite_title
            lines.append(f"- **{i18n.t('pub_source')}:** {source}")
        lines.append("")
        lines.append(i18n.t("pub_footer"))
        out.append({"title": statement, "body": "\n".join(lines), "slack": statement, "url": cite_url})
    return out


def items_related(data: dict, topic: str, date: str) -> list[Item]:
    """One Issue per paper (flattened across themes), plus one for open gaps.

    Each paper carries its theme name and summary for context. The run's
    ``open_gaps`` are run-level (not tied to a single paper), so they collect
    into one trailing digest Issue when present.
    """
    out: list[Item] = []
    for theme in _dicts(data.get("themes")):
        name = str(theme.get("name", "")).strip()
        summary = str(theme.get("summary", "")).strip()
        for paper in _dicts(theme.get("papers")):
            title = str(paper.get("title", "")).strip()
            if not title:
                continue
            url = str(paper.get("url", "")).strip()
            note = str(paper.get("note", "")).strip()

            lines = [_header(topic, date)]
            if name:
                lines.append(f"**{i18n.t('pub_theme')}:** {name}")
            if summary:
                lines.append(summary)
            if url:
                lines.append(f"**{i18n.t('pub_link')}:** {url}")
            if note:
                lines.append("")
                lines.append(note)
            lines.append("")
            lines.append(i18n.t("pub_footer"))
            out.append({"title": title, "body": "\n".join(lines), "slack": title, "url": url})

    gaps = [str(gap).strip() for gap in (data.get("open_gaps") or []) if str(gap).strip()]
    if gaps:
        lines = [_header(topic, date), f"### {i18n.t('pub_open_gaps')}"]
        lines.extend(f"- {gap}" for gap in gaps)
        lines.append("")
        lines.append(i18n.t("pub_footer"))
        title = f"{i18n.t('pub_open_gaps')} — {date}"
        out.append({"title": title, "body": "\n".join(lines), "slack": title, "url": ""})
    return out


BUILDERS = {
    "news": items_news,
    "hypotheses": items_hypotheses,
    "related": items_related,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in SECTIONS:
        print("Usage: publish_section.py <news|hypotheses|related>")
        return 0
    section = sys.argv[1]

    raw = os.environ.get("SECTION_JSON", "").strip()
    if not raw:
        print(f"No structured output for '{section}'. Nothing to publish.")
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Structured output for '{section}' was not valid JSON. Skipping.")
        return 0
    if not isinstance(data, dict):
        print(f"Structured output for '{section}' was not a JSON object. Skipping.")
        return 0

    topic = os.environ.get("RESEARCH_TOPIC", "").strip() or topic_from_config() or "AI"
    date = os.environ.get("RUN_DATE", "").strip() or datetime.date.today().isoformat()

    meta = SECTIONS[section]
    name = i18n.t(str(meta["name_key"]))
    emoji = str(meta["emoji"])
    order = int(meta["order"])
    labels = list(dict.fromkeys([*base_labels(), str(meta["tag"])]))
    items = BUILDERS[section](data, topic, date)

    if not items:
        print(f"No items in structured output for '{section}'. Nothing to publish.")
        return 0

    make_issue = flag("ENABLE_GITHUB_ISSUE", True)
    write_file = flag("ENABLE_FILE_OUTPUT", False)
    # Default ON: bundle every item of this section into a SINGLE Slack post
    # instead of posting one message per item. Set SLACK_DIGEST=false to go back
    # to one Slack line per item.
    digest = flag("SLACK_DIGEST", True)
    if not make_issue:
        print("ENABLE_GITHUB_ISSUE is off. Skipping GitHub Issue creation.")
    if write_file:
        os.makedirs("outputs", exist_ok=True)

    print(f"Publishing {len(items)} item(s) for '{section}', one Issue each.")
    # Collected one-per-item Slack lines, used only when digest mode is on.
    digest_lines: list[str] = []
    for index, item in enumerate(items, start=1):
        issue_title = _trim(f"{name}: {item['title']}")
        body = item["body"]

        issue_url: str | None = None
        site_url: str | None = None
        if make_issue:
            issue = create_issue(issue_title, body, labels)
            if issue:
                issue_url = issue.get("html_url")
                # Link to this item's own page on the generated Pages site.
                site_url = item_url(issue)

        if write_file:
            path = os.path.join("outputs", f"{date}-{section}-{index:02d}.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(f"# {issue_title}\n\n{body}\n")
            print(f"Wrote {path}")

        # Primary link = the published site page, else the GitHub Issue. Readers
        # may have no repo access — Pages can be public while the repo is private,
        # and many never open GitHub — so the public site page leads; the Issue is
        # the fallback (and, when the site page leads, a secondary "↳" line). The
        # curated source URL stays inside the Issue body, not the notification.
        primary_url = primary_link(site_url, issue_url)
        secondary_issue = issue_url if (issue_url and issue_url != primary_url) else None
        issue_line = "\n" + i18n.t("slack_issue_link", url=secondary_issue) if secondary_issue else ""

        # Untrusted title → neutralise Slack mrkdwn link/format injection.
        slack_title = slack_escape(_trim(item["slack"], 160))
        if digest:
            # Compact per-item bullet; the section header is posted once below.
            key = "slack_digest_item" if primary_url else "slack_digest_item_nolink"
            digest_lines.append(i18n.t(key, title=slack_title, url=primary_url or "") + issue_line)
        elif primary_url:
            line = i18n.t("slack_item", emoji=emoji, section=name, title=slack_title, url=primary_url) + issue_line
            emit(line, subject=f"{name}: {slack_title}", order=order)
        else:
            line = i18n.t("slack_item_nolink", emoji=emoji, section=name, title=slack_title)
            emit(line, subject=f"{name}: {slack_title}", order=order)

    if digest and digest_lines:
        # In spool mode the run-level header carries "Auto Research", so each
        # section gets a compact sub-header; standalone (direct) sends keep the
        # full per-section header.
        header_key = "slack_section_header" if spooling() else "slack_digest_header"
        header = i18n.t(header_key, emoji=emoji, section=name, count=len(digest_lines))
        message = header + "\n\n" + "\n\n".join(digest_lines)
        emit(message, subject=header, order=order)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
