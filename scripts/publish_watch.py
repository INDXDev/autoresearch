#!/usr/bin/env python3
"""Deterministic publisher for the Site Watch section.

The DETERMINISTIC half of the Site Watch pipeline (mirrors ``publish_section.py``).
The non-deterministic part — reading the page diffs and deciding what actually
changed — happens in the Claude Code Action, which returns a schema-validated JSON
object as ``structured_output``: one entry per changed page. This script never
calls an LLM. For each page it formats ONE GitHub Issue (labelled ``site-watch`` +
``watch:<slug>`` so the static-site builder and de-dup share it) and posts one
Slack line linking to it.

So: one watched page that changed → one Issue summarising it, with the individual
changes listed inside.

Usage:
    SECTION_JSON='{"pages":[...]}' python3 scripts/publish_watch.py

Inputs (environment):
    SECTION_JSON          the structured_output JSON string from Claude (required)
    WATCH_MANIFEST        path to the fetch step's manifest.json (for line counts;
                          default .watch_diffs/manifest.json)
    OUTPUT_LANGUAGE       en | ja  (scaffolding language; default en)
    GITHUB_ISSUE_LABELS   comma-separated base labels (default none)
    ENABLE_GITHUB_ISSUE   create the Issues? default true
    GITHUB_TOKEN          provided automatically by Actions (for the Issue)
    SLACK_WEBHOOK_URL     optional; the Slack line is skipped if unset

Security: never prints tokens or the Slack webhook URL (the helpers enforce this).
"""

from __future__ import annotations

import datetime
import json
import os

import i18n
from github_issue import base_labels, create_issue
from notify import emit, primary_link
from site_url import item_url
from slack_post import slack_escape
from watch_targets import get_target, valid_slug

# Label tag the static-site builder (build_site.py) and de-dup match on.
WATCH_TAG = "site-watch"
EMOJI = "👀"
# Site Watch lands last in the combined run notification (see notify.emit).
ORDER = 4

_TRUE = {"1", "true", "yes", "on"}
_MAX_TITLE = 200


def flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return default if raw == "" else raw in _TRUE


def _trim(text: str, limit: int = _MAX_TITLE) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _load_manifest() -> dict:
    path = os.environ.get("WATCH_MANIFEST", "").strip() or os.path.join(".watch_diffs", "manifest.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _render_body(page: dict, name: str, url: str, counts: dict, date: str) -> str:
    summary = str(page.get("summary", "")).strip()
    changes = [c for c in (page.get("changes") or []) if isinstance(c, dict)]

    watched = f"[{name}]({url})" if url else name
    lines = [f"**{i18n.t('watch_url_label')}:** {watched}  ", f"**{i18n.t('pub_date')}:** {date}"]
    if counts:
        added = counts.get("added", 0)
        removed = counts.get("removed", 0)
        lines.append(f"**{i18n.t('watch_lines')}:** +{added} / -{removed}")
    if summary:
        lines.append("")
        lines.append(summary)
    if changes:
        lines.append("")
        lines.append(f"### {i18n.t('watch_changes')}")
        for change in changes:
            title = str(change.get("title", "")).strip()
            if not title:
                continue
            detail = str(change.get("detail", "")).strip()
            link = str(change.get("url", "")).strip()
            label = f"[{title}]({link})" if link else title
            lines.append(f"- {label}" + (f" — {detail}" if detail else ""))
    lines.append("")
    lines.append(i18n.t("pub_footer"))
    return "\n".join(lines)


def main() -> int:
    raw = os.environ.get("SECTION_JSON", "").strip()
    if not raw:
        print("No structured output for Site Watch. Nothing to publish.")
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("Site Watch structured output was not valid JSON. Skipping.")
        return 0
    if not isinstance(data, dict):
        print("Site Watch structured output was not a JSON object. Skipping.")
        return 0

    pages = [p for p in (data.get("pages") or []) if isinstance(p, dict)]
    if not pages:
        print("Site Watch structured output had no pages. Nothing to publish.")
        return 0

    manifest = _load_manifest()
    date = os.environ.get("RUN_DATE", "").strip() or datetime.date.today().isoformat()
    make_issue = flag("ENABLE_GITHUB_ISSUE", True)
    if not make_issue:
        print("ENABLE_GITHUB_ISSUE is off. Skipping GitHub Issue creation.")

    published = 0
    for page in pages:
        raw_slug = str(page.get("slug", "")).strip()
        changes = [c for c in (page.get("changes") or []) if isinstance(c, dict)]
        # Respect Claude's judgement that a diff was just noise.
        if page.get("no_meaningful_change") and not changes:
            print(f"Page '{raw_slug or '?'}' reported no meaningful change. Skipping.")
            continue

        target = get_target(raw_slug) or {}
        # Canonical, label-safe slug: the resolved target's, else a validated
        # form of the LLM's. Avoids a malformed `watch:<slug>` label that would
        # split this page off from its canonical group on the site.
        slug = str(target.get("slug", "")).strip() or valid_slug(raw_slug)
        name = str(page.get("name", "")).strip() or target.get("name") or slug or "Site Watch"
        url = str(page.get("url", "")).strip() or target.get("url", "")
        counts = manifest.get(slug) if isinstance(manifest.get(slug), dict) else None
        headline = str(page.get("headline", "")).strip()

        body = _render_body(page, name, url, counts or {}, date)
        issue_title = _trim(f"{name}: {headline or i18n.t('watch_default_headline')}")
        labels = list(dict.fromkeys([*base_labels(), WATCH_TAG, f"watch:{slug}" if slug else WATCH_TAG]))

        issue_url = None
        site_url = None
        if make_issue:
            issue = create_issue(issue_title, body, labels)
            if issue:
                issue_url = issue.get("html_url")
                # Link to this page's own item page on the generated Pages site.
                site_url = item_url(issue)

        # One Slack line per changed page. name / headline / change titles come
        # from the LLM or arbitrary web-page text → escape Slack mrkdwn control
        # syntax so they can't smuggle a clickable link or formatting.
        slack_lines = [i18n.t("watch_slack_header", emoji=EMOJI, name=slack_escape(_trim(name, 120)))]
        if headline:
            slack_lines.append(slack_escape(_trim(headline, 160)))
        for change in changes[:5]:
            title = str(change.get("title", "")).strip()
            if title:
                slack_lines.append(i18n.t("slack_digest_item_nolink", title=slack_escape(_trim(title, 160))))
        # Primary link = the on-site page, else the GitHub Issue (the repo may be
        # private while Pages is public, and many readers never open GitHub). When
        # the site page leads, the Issue is shown as a secondary "↳" line. The
        # watched-page URL stays inside the Issue body, not the notification.
        primary_url = primary_link(site_url, issue_url)
        secondary_issue = issue_url if (issue_url and issue_url != primary_url) else None
        if primary_url:
            slack_lines.append(primary_url)
        if secondary_issue:
            slack_lines.append(i18n.t("slack_issue_link", url=secondary_issue))
        message = "\n".join(slack_lines)
        emit(message, subject=i18n.t("section_watch") + f" — {_trim(name, 120)}", order=ORDER)
        published += 1

    print(f"Site Watch: published {published} changed page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
