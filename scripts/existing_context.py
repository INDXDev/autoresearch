#!/usr/bin/env python3
"""Summarise already-published Issues so the research step can avoid duplicates.

This runs BEFORE the Claude Code Action research step. It pulls the Issues that
previous runs created for this section (matched by the section's label), distils
them into a compact, human-readable digest, and writes that digest to a file.
The research prompt then tells Claude to ``Read`` this file and NOT re-propose
anything already covered — so each run surfaces genuinely new material instead of
re-publishing the same papers/news/hypotheses.

It also turns lightweight human feedback into steering for the next run: react to
a past Issue with 👍 / 👎 (or add a good/bad label) and the digest tells Claude to
produce MORE work like the 👍 ones and AVOID the 👎 ones.

This script never calls an LLM. It only reads the GitHub Issues API and writes a
plain-text file. It always exits 0: if the token/repo are missing or the API
fails, it writes an empty digest and the research step simply proceeds with no
prior context (degrading to the old behaviour rather than failing the run).

Usage:
    python3 scripts/existing_context.py <news|hypotheses|related> [output_path]

Inputs (environment):
    GITHUB_TOKEN          provided automatically by Actions (read access)
    GITHUB_REPOSITORY     'owner/name' (auto-set inside Actions)
    OUTPUT_LANGUAGE       en | ja  (digest scaffolding language; default en)
    EXISTING_CONTEXT_MAX  max Issues to summarise (default 40)
    GOOD_LABELS           comma-separated label names that mark an Issue "good"
    BAD_LABELS            comma-separated label names that mark an Issue "bad"

Security: never prints tokens or any secret.
"""

from __future__ import annotations

import os
import re
import sys

import i18n
from github_issue import list_issues

# section key -> the label tag publish_section.py stamps on that section's Issue.
SECTION_TAGS: dict[str, str] = {
    "news": "research-news",
    "hypotheses": "hypothesis",
    "related": "related-work",
}

# How many "covered item" lines to pull out of a single Issue body.
_MAX_ITEMS_PER_ISSUE = 8

# Default label names a human can add to a past Issue to steer future runs.
# Override with the GOOD_LABELS / BAD_LABELS env vars (comma-separated). A 👍 / 👎
# *reaction* on the Issue counts too (see _reaction_signal) — no label needed.
_DEFAULT_GOOD = ("good", "👍", "useful", "approved")
_DEFAULT_BAD = ("bad", "👎", "not-useful", "rejected")


def _labelset(name: str, default: tuple[str, ...]) -> set[str]:
    """Read a comma-separated label-name list from env, lowercased."""
    raw = os.environ.get(name, "").strip()
    names = [part.strip() for part in raw.split(",")] if raw else list(default)
    return {n.lower() for n in names if n}


def _issue_labels(issue: dict) -> set[str]:
    """The label names on an Issue, lowercased. Handles the GitHub API shape
    (a list of ``{"name": ...}`` dicts) and a plain list of strings."""
    out: set[str] = set()
    for label in issue.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if name:
            out.add(str(name).lower())
    return out


def _reaction_signal(issue: dict) -> str | None:
    """Classify an Issue from its 👍 / 👎 reactions: ``"good"``, ``"bad"``, or None.

    The GitHub Issues API returns a ``reactions`` summary object with ``"+1"`` and
    ``"-1"`` counts. We treat net-positive as good and net-negative as bad, so a
    human can steer the next run just by reacting — no label required. A tie (or no
    reactions) yields None, leaving the decision to labels.
    """
    reactions = issue.get("reactions")
    if not isinstance(reactions, dict):
        return None
    try:
        up = int(reactions.get("+1", 0) or 0)
        down = int(reactions.get("-1", 0) or 0)
    except (TypeError, ValueError):
        return None
    if up > down:
        return "good"
    if down > up:
        return "bad"
    return None


def build_feedback(issues: list[dict]) -> str:
    """Render a steering block from human feedback on past Issues.

    Feedback is either a good/bad *label* (names from GOOD_LABELS / BAD_LABELS) or a
    👍 / 👎 *reaction*. Labels win when both are present; otherwise the reaction
    decides. Returns an EMPTY string when no past Issue carries any feedback — in
    that case nothing extra is fed to the research step (the caller writes nothing).
    """
    good_labels = _labelset("GOOD_LABELS", _DEFAULT_GOOD)
    bad_labels = _labelset("BAD_LABELS", _DEFAULT_BAD)

    good: list[dict] = []
    bad: list[dict] = []
    for issue in issues:
        names = _issue_labels(issue)
        signal = _reaction_signal(issue)
        if names & good_labels:
            good.append(issue)
        elif names & bad_labels:
            bad.append(issue)
        elif signal == "good":
            good.append(issue)
        elif signal == "bad":
            bad.append(issue)

    if not good and not bad:
        return ""

    def _block(header: str, group: list[dict]) -> list[str]:
        rows = [header]
        for issue in group:
            title = str(issue.get("title", "")).strip()
            if title:
                rows.append(f"- {title}")
            for item in _covered_items(str(issue.get("body", ""))):
                rows.append(f"  - {item}")
        return rows

    lines: list[str] = []
    if good:
        lines += _block(i18n.t("fb_good"), good)
        lines.append("")
    if bad:
        lines += _block(i18n.t("fb_bad"), bad)
        lines.append("")
    return "\n".join(lines).rstrip()


def _covered_items(body: str) -> list[str]:
    """Extract the item titles already covered inside one Issue body.

    The publisher renders items as Markdown bullets (``- [Title](url)`` / ``- Title``)
    and hypotheses/themes as headings (``### 1. Statement`` / ``### Theme``). We
    pull the human-readable label out of each so the digest lists concrete,
    already-covered titles rather than raw Markdown.
    """
    items: list[str] = []
    for raw in (body or "").splitlines():
        # Skip indented continuation lines (takeaways / paper notes); we only want
        # the top-level titles, not their descriptions.
        if raw[:1].isspace():
            continue
        line = raw.strip()
        if line.startswith("###"):
            text = line.lstrip("#").strip()
            text = re.sub(r"^\d+\.\s*", "", text)  # drop "1. " numbering
        elif line.startswith("- "):
            text = line[2:].strip()
        else:
            continue
        # Reduce "[Title](url)" to "Title"; strip trailing " — note" / " (meta)".
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.split(r"\s+—\s+", text, maxsplit=1)[0].strip()
        # Skip our own scaffolding labels (Rationale/Experiment/...) and headers.
        if not text or text.startswith("**") or text.startswith("_"):
            continue
        items.append(text)
        if len(items) >= _MAX_ITEMS_PER_ISSUE:
            break
    return items


def build_digest(issues: list[dict]) -> str:
    """Render the prior-Issues digest the research step will read."""
    if not issues:
        return i18n.t("ctx_none")

    lines = [i18n.t("ctx_header", count=len(issues)), ""]
    for issue in issues:
        title = str(issue.get("title", "")).strip()
        if title:
            lines.append(f"- {title}")
        for item in _covered_items(str(issue.get("body", ""))):
            lines.append(f"  - {item}")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in SECTION_TAGS:
        print("Usage: existing_context.py <news|hypotheses|related> [output_path]")
        return 0
    section = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else f".research_context/{section}.md"

    try:
        limit = int(os.environ.get("EXISTING_CONTEXT_MAX", "40"))
    except ValueError:
        limit = 40

    issues = list_issues(SECTION_TAGS[section], state="all", limit=limit)

    # Human good/bad labels steer the next run; empty string adds nothing.
    feedback = build_feedback(issues)
    digest = build_digest(issues)
    parts = [block for block in (feedback, digest) if block.strip()]
    content = "\n\n".join(parts)

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(content + "\n")

    fb_note = " with good/bad feedback" if feedback else ""
    print(f"Wrote prior-context digest for '{section}' ({len(issues)} issue(s)){fb_note} to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
