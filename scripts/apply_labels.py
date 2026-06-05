#!/usr/bin/env python3
"""Apply the auto-labeler's decisions to GitHub Issues (DETERMINISTIC half).

The Claude Code Action step reads ``.label_context/issues.md`` and returns a
schema-validated JSON object describing, per Issue, which labels to ADD. This
script never calls an LLM — it only iterates that JSON and calls the GitHub API.

Adds are ADDITIVE: an Issue's existing labels (e.g. ``auto-research``,
``research-news``) are kept; the new topical labels are appended. GitHub
auto-creates any label that does not yet exist.

Usage:
    LABELS_JSON='{"labels":[...]}' python3 scripts/apply_labels.py

Expected JSON shape (the workflow's --json-schema enforces it):
    {"labels": [ {"issue": 12, "add": ["agents", "rlhf"], "reason": "..."} ]}

Inputs (environment):
    LABELS_JSON           the structured_output JSON string from Claude (required)
    GITHUB_TOKEN          provided automatically by Actions
    GITHUB_REPOSITORY     owner/name (auto-set in Actions)
    LABEL_MAX_PER_ISSUE   cap on labels added to a single Issue (default 5)

Security: never prints the token (the helpers enforce this).
"""

from __future__ import annotations

import json
import os
import sys

from github_issue import add_labels

# GitHub caps a label name at 50 chars; trim defensively.
_MAX_LABEL_LEN = 50


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _clean(labels: object, cap: int) -> list[str]:
    """Normalise a raw label list: strings, trimmed, deduped, capped."""
    out: list[str] = []
    for raw in labels if isinstance(labels, list) else []:
        name = " ".join(str(raw).split())[:_MAX_LABEL_LEN].strip()
        if name and name not in out:
            out.append(name)
    return out[:cap]


def main() -> int:
    raw = os.environ.get("LABELS_JSON", "").strip()
    if not raw:
        print("No LABELS_JSON provided. Nothing to label.")
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("LABELS_JSON was not valid JSON. Skipping.")
        return 0
    if not isinstance(data, dict):
        print("LABELS_JSON was not a JSON object. Skipping.")
        return 0

    entries = data.get("labels")
    if not isinstance(entries, list) or not entries:
        print("LABELS_JSON had no 'labels' array. Nothing to label.")
        return 0

    cap = _int_env("LABEL_MAX_PER_ISSUE", 5)
    # Merge adds per issue number FIRST, so two entries for the same issue can't
    # together exceed the per-issue cap (and we hit the API once per issue).
    raw_by_issue: dict[int, list] = {}
    order: list[int] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        number = entry.get("issue")
        if not isinstance(number, int):
            try:
                number = int(number)
            except (TypeError, ValueError):
                print(f"Skipping entry with invalid issue number: {number!r}")
                continue
        add = entry.get("add")
        if not isinstance(add, list):
            continue
        if number not in raw_by_issue:
            raw_by_issue[number] = []
            order.append(number)
        raw_by_issue[number].extend(add)

    labelled = 0
    for number in order:
        names = _clean(raw_by_issue[number], cap)
        if not names:
            continue
        if add_labels(number, names):
            labelled += 1

    print(f"Applied labels to {labelled} issue(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
