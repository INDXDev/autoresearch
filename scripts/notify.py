"""Unified Slack + email dispatch, with an optional spool for combined sends.

Every publisher emits its Slack/email lines through ``emit()`` here instead of
calling ``post_to_slack`` / ``post_to_email`` directly. There are two modes:

* **Direct** (default) — post the message to Slack and email immediately, one
  send per call. This is the original per-section behaviour, kept for anyone who
  runs a publisher on its own.
* **Spool** (``NOTIFY_SPOOL_DIR`` set) — the Auto Research workflow runs its four
  section jobs (Latest / Takes / Foundations / Site Watch) in PARALLEL, and each
  would otherwise fire its own Slack post and its own email — up to four of each
  per run. Instead, every call APPENDS its block to a file under that directory;
  a final ``notify`` job runs ``notify_combined.py`` to fold every section's
  spooled blocks into ONE Slack post and ONE email for the whole run.

Also exposes ``primary_link`` — the single rule for which URL a notification line
points at: the item's page on the published Pages site, else its GitHub Issue.
(The curated source URL stays inside the Issue body; the notification drives the
reader to the public site, falling back to the Issue when Pages isn't enabled.)

Dependency-free (delegates to the urllib-based posters) so it works in both the
simple Python pipeline and the agentic Claude Code workflow.
"""

from __future__ import annotations

import json
import os

from email_post import post_to_email
from slack_post import post_to_slack

# Bumped on every spooled write so each block lands in its own file within a job.
_seq = 0


def _spool_dir() -> str | None:
    """The directory to spool notifications into, or None for direct sending."""
    directory = os.environ.get("NOTIFY_SPOOL_DIR", "").strip()
    return directory or None


def spooling() -> bool:
    """True when notifications are being collected for one combined run send."""
    return _spool_dir() is not None


def primary_link(site_url: str | None, issue_url: str | None) -> str | None:
    """The URL a notification line points at: the on-site Pages page, else the
    GitHub Issue. Returns None when neither exists."""
    return (site_url or "").strip() or (issue_url or "").strip() or None


def emit(text: str, *, subject: str | None = None, order: int = 50) -> None:
    """Send ``text`` to Slack + email now, or spool it for the combined run send.

    ``order`` decides where this block lands in the combined message (lower is
    earlier): Latest=1, Takes=2, Foundations=3, Site Watch=4. ``subject`` is the
    email subject used in direct mode; in spool mode the combined send uses one
    run-level subject instead.
    """
    global _seq
    text = (text or "").strip()
    if not text:
        return

    spool = _spool_dir()
    if spool is None:
        post_to_slack(text)
        post_to_email(text, subject=subject)
        return

    os.makedirs(spool, exist_ok=True)
    _seq += 1
    # Filename encodes (section order, write sequence) so a plain lexical sort of
    # the merged directory reproduces the intended run order. ``order`` differs
    # per section job, and ``_seq`` is unique within a job, so names never collide
    # once the four jobs' spools are merged into one directory.
    path = os.path.join(spool, f"{order:02d}-{_seq:03d}.json")
    record = {"order": order, "text": text, "subject": subject}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)
    print(f"Spooled one notification block ({path}) for the combined run send.")
