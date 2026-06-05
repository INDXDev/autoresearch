"""Send the research summary by email via the Resend API.

This is the email twin of ``slack_post.py``: wherever the publisher posts a line
to Slack, it can also send the very same text as an email — but only when both a
``RESEND_API_KEY`` and a destination ``EMAIL_TO`` are configured with real
values. If either is missing (or an obvious sample value), the send is skipped
and the workflow continues successfully.

Dependency-free (uses urllib) so it works in both the simple Python pipeline and
the agentic Claude Code workflow without installing anything.

Configuration (environment variables):

* ``RESEND_API_KEY`` — required. Your Resend API key (a secret).
* ``EMAIL_TO``       — required. One or more recipients (comma/space separated).
* ``EMAIL_FROM``     — optional. Sender; defaults to Resend's shared test sender
  ``Auto Research <onboarding@resend.dev>`` (only delivers to your own account
  until you verify a domain in Resend).
* ``EMAIL_SUBJECT_PREFIX`` — optional. Prepended to every subject; defaults to
  ``[Auto Research] ``.

Usage:
    python scripts/email_post.py "my message"     # message from argv
    printf '%s' "my message" | python scripts/email_post.py   # from stdin

Security: the API key is treated as a secret. It is never printed to the logs --
only safe status messages are emitted.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

_API_URL = "https://api.resend.com/emails"
_DEFAULT_FROM = "Auto Research <onboarding@resend.dev>"
_DEFAULT_SUBJECT_PREFIX = "[Auto Research] "

# Sample values that should be treated as "not configured".
_PLACEHOLDERS = {
    "",
    "dummy",
    "changeme",
    "change-me",
    "example",
    "your-api-key",
    "re_xxxxxxxx",
    "you@example.com",
    "someone@example.com",
    "to@example.com",
    "from@example.com",
}


def _clean(value: str) -> str:
    return value.strip()


def _api_key() -> str | None:
    """Return the configured Resend API key, or None if it is a placeholder."""
    key = _clean(os.environ.get("RESEND_API_KEY", ""))
    if key.lower() in _PLACEHOLDERS:
        return None
    return key or None


def _recipients() -> list[str]:
    """Return the list of recipient addresses (split on commas / whitespace)."""
    raw = _clean(os.environ.get("EMAIL_TO", ""))
    if raw.lower() in _PLACEHOLDERS:
        return []
    parts = [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]
    return [p for p in parts if p.lower() not in _PLACEHOLDERS and "@" in p]


def _sender() -> str:
    sender = _clean(os.environ.get("EMAIL_FROM", ""))
    if not sender or sender.lower() in _PLACEHOLDERS:
        return _DEFAULT_FROM
    return sender


def _subject_for(text: str, subject: str | None) -> str:
    """Build the email subject: explicit subject, else the first line of text."""
    prefix = os.environ.get("EMAIL_SUBJECT_PREFIX", _DEFAULT_SUBJECT_PREFIX)
    if subject is None:
        first_line = next((ln for ln in text.splitlines() if ln.strip()), "Update")
        subject = first_line
    # Slack mrkdwn uses ``*bold*``; strip the asterisks for a clean subject.
    subject = subject.replace("*", "").strip()
    if len(subject) > 150:
        subject = subject[:149].rstrip() + "…"
    return f"{prefix}{subject}"


def post_to_email(text: str, subject: str | None = None) -> bool:
    """Email ``text`` via Resend. Returns True if a message was sent.

    Never raises and never logs the API key. When ``subject`` is omitted the
    first non-empty line of ``text`` is used.
    """
    key = _api_key()
    recipients = _recipients()
    if not key or not recipients:
        print("Resend email is not configured (need RESEND_API_KEY + EMAIL_TO). Skipping email.")
        return False

    payload = {
        "from": _sender(),
        "to": recipients,
        "subject": _subject_for(text, subject),
        "text": text,
    }
    request = urllib.request.Request(
        _API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # api.resend.com sits behind Cloudflare, which blocks urllib's default
            # ``Python-urllib/x.y`` User-Agent (Cloudflare error 1010 → HTTP 403).
            # Send an explicit UA so the request is allowed through.
            "User-Agent": "auto-research/1.0 (+https://github.com/anthropics/claude-code)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        # The response body is the server's error message (never contains our
        # API key) — surface a short slice to make failures diagnosable. Keep
        # failures non-fatal.
        try:
            detail = exc.read().decode("utf-8", "replace").strip().replace("\n", " ")
        except Exception:
            detail = ""
        suffix = f" ({detail[:200]})" if detail else ""
        print(f"Resend email returned HTTP {exc.code}. Skipping.{suffix}")
        return False
    except urllib.error.URLError as exc:
        print(f"Resend email failed ({type(exc).__name__}). Continuing without failing the run.")
        return False

    if status in (200, 201):
        print(f"Sent research summary by email to {len(recipients)} recipient(s).")
        return True
    print(f"Resend email returned HTTP {status}. Skipping.")
    return False


def _message_from_cli() -> str:
    """Read the message from argv[1], or stdin, or a default test string."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1]
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped
    return "Auto Research test message"


if __name__ == "__main__":
    post_to_email(_message_from_cli())
