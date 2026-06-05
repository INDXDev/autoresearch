"""Load and normalise the Site Watch target list (config/watch_targets.json).

Site Watch is a second, independent pipeline alongside the research sections. For
each configured web page it renders the page with Playwright, diffs the rendered
text against a snapshot committed in ``snapshots/<slug>.txt``, and — only when the
content actually changed — asks Claude Code to summarise the diff, which a small
Python publisher files as a GitHub Issue (+ optional Slack line).

This module is the shared, dependency-free loader used by both halves:

* ``watch_fetch.py`` reads a single target to fetch + diff it, and emits the
  Actions matrix of enabled targets.
* the publisher reads the same config for the human-readable name / URL.

It uses only the Python standard library and never calls an LLM.
"""

from __future__ import annotations

import json
import os
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "watch_targets.json")

# Where snapshots live in the working tree (one file per target, the run-to-run
# baseline). On CI these are restored from / saved to the unified
# `auto-research-state` orphan branch rather than committed to the default branch.
SNAPSHOT_DIR = "snapshots"
# Where the per-run diff is written for Claude to read (ephemeral, gitignored).
DIFF_DIR = ".watch_diffs"

_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*$")
_VALID_WAIT = {"load", "domcontentloaded", "networkidle", "commit"}

_TRUE = {"1", "true", "yes", "on"}


def _is_enabled(target: dict) -> bool:
    """``enabled`` defaults to True; accept bool or a truthy string."""
    raw = target.get("enabled", True)
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in _TRUE


def snapshot_path(slug: str) -> str:
    return os.path.join(SNAPSHOT_DIR, f"{slug}.txt")


def diff_path(slug: str) -> str:
    return os.path.join(DIFF_DIR, f"{slug}.diff")


def _normalise(target: dict) -> dict | None:
    """Validate one raw target dict into a clean record, or None if unusable."""
    if not isinstance(target, dict):
        return None
    slug = str(target.get("slug", "")).strip().lower()
    url = str(target.get("url", "")).strip()
    # A valid target needs a filename-safe slug and an http(s) URL.
    if not _SLUG_RE.fullmatch(slug) or not url.startswith(("http://", "https://")):
        return None
    wait_until = str(target.get("wait_until", "domcontentloaded")).strip().lower()
    if wait_until not in _VALID_WAIT:
        wait_until = "domcontentloaded"
    return {
        "slug": slug,
        "name": str(target.get("name", "")).strip() or slug,
        "url": url,
        "selector": str(target.get("selector", "")).strip(),
        "wait_until": wait_until,
        "enabled": _is_enabled(target),
    }


def load_targets(include_disabled: bool = False) -> list[dict]:
    """Return the normalised, de-duplicated target list from the JSON config.

    Invalid entries (bad slug, missing URL) are skipped. Keys beginning with
    ``//`` are treated as comments. Disabled targets are dropped unless
    ``include_disabled`` is set. Never raises: a missing or malformed config
    yields an empty list so the workflow degrades to "nothing to watch".
    """
    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []

    seen: set[str] = set()
    out: list[dict] = []
    for raw in data.get("targets") or []:
        record = _normalise(raw)
        if not record or record["slug"] in seen:
            continue
        if not include_disabled and not record["enabled"]:
            continue
        seen.add(record["slug"])
        out.append(record)
    return out


def valid_slug(slug: str) -> str:
    """Return the lowercased slug if it is filename/label-safe, else ``''``.

    Used by the publisher to keep an LLM-supplied slug from producing a label
    like ``watch:Hacker News`` that diverges from the canonical ``watch:<slug>``.
    """
    candidate = (slug or "").strip().lower()
    return candidate if _SLUG_RE.fullmatch(candidate) else ""


def get_target(slug: str) -> dict | None:
    """Look up a single target by slug (including disabled ones)."""
    slug = (slug or "").strip().lower()
    for target in load_targets(include_disabled=True):
        if target["slug"] == slug:
            return target
    return None
