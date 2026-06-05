#!/usr/bin/env python3
"""Fold every section's spooled notifications into ONE Slack post + ONE email.

The Auto Research workflow runs its four section jobs — Latest / Takes /
Foundations / Site Watch — in parallel. Each one spools its Slack/email blocks
into a shared ``.notify/`` directory (uploaded as an artifact) via
``notify.emit()`` instead of sending anything itself. This final step runs once,
AFTER all the sections, in the dedicated ``notify`` job: it reads every spooled
block, orders them, and sends a single combined Slack post and a single combined
email for the whole run. Deterministic — no LLM.

So the reader gets ONE digest per run instead of up to four scattered messages.

Usage:
    NOTIFY_SPOOL_DIR=.notify python3 scripts/notify_combined.py

Inputs (environment):
    NOTIFY_SPOOL_DIR   directory holding the spooled ``*.json`` blocks (default .notify)
    OUTPUT_LANGUAGE    en | ja (the run header / subject language; default en)
    RUN_DATE           ISO date for the header (default: today)
    SLACK_WEBHOOK_URL  optional; the Slack post is skipped if unset
    RESEND_API_KEY / EMAIL_TO  optional; the email is skipped if unset

Security: never prints tokens or the Slack webhook URL (the posters enforce this).
"""

from __future__ import annotations

import datetime
import glob
import json
import os

import i18n
from email_post import post_to_email
from slack_post import post_to_slack


def _load_blocks(spool: str) -> list[str]:
    """Return the spooled message blocks in run order (lexical filename order,
    which encodes section order + write sequence — see ``notify.emit``)."""
    blocks: list[str] = []
    for path in sorted(glob.glob(os.path.join(spool, "*.json"))):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            text = str(record.get("text", "")).strip()
            if text:
                blocks.append(text)
    return blocks


def main() -> int:
    spool = os.environ.get("NOTIFY_SPOOL_DIR", "").strip() or ".notify"
    blocks = _load_blocks(spool)
    if not blocks:
        print("No notifications were spooled this run. Nothing to send.")
        return 0

    date = os.environ.get("RUN_DATE", "").strip() or datetime.date.today().isoformat()
    header = i18n.t("slack_run_header", date=date)
    message = header + "\n\n" + "\n\n".join(blocks)

    post_to_slack(message)
    post_to_email(message, subject=i18n.t("slack_run_subject", date=date))
    print(f"Sent one combined notification covering {len(blocks)} section block(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
