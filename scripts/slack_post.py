"""Post the research summary to Slack via an Incoming Webhook.

Posting only happens when ``SLACK_WEBHOOK_URL`` is configured with a real value.
If it is missing, empty, or an obvious sample value, the post is skipped and the
workflow continues successfully.

Dependency-free (uses urllib) so it works in both the simple Python pipeline and
the agentic Claude Code workflow without installing anything.

Usage:
    python scripts/slack_post.py "my message"      # message from argv
    printf '%s' "my message" | python scripts/slack_post.py   # message from stdin

Security: the webhook URL is treated as a secret. It is never printed to the
logs -- only safe status messages are emitted.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Sample values that should be treated as "not configured".
_PLACEHOLDERS = {
    "",
    "dummy",
    "changeme",
    "change-me",
    "example",
    "https://hooks.slack.com/services/your/webhook/url",
    "https://hooks.slack.com/services/xxx/yyy/zzz",
}


def slack_escape(text: str) -> str:
    """Neutralise Slack mrkdwn link/control syntax in UNTRUSTED text.

    Item titles and Site Watch headlines come from the LLM's output or, for Site
    Watch, arbitrary web-page text — untrusted. Slack renders an incoming
    webhook's ``text`` as mrkdwn, so a raw ``<https://evil|click>`` in a title
    becomes a clickable attacker-controlled link. Escaping the three reserved
    characters ``< > &`` (Slack's documented rule) prevents that. Trusted
    decoration the publisher adds itself (the ``*Auto Research*`` bold, the
    section emoji) is applied AFTER this, so it still renders.

    The same escaped string is mirrored to the plain-text email; ``&lt;`` etc.
    only appear there in the rare case a title literally contains ``< > &``.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _webhook_url() -> str | None:
    """Return the configured webhook URL, or None if it is a placeholder."""
    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if url.lower() in _PLACEHOLDERS:
        return None
    # A real Slack incoming webhook always starts with this host.
    if not url.startswith("https://hooks.slack.com/"):
        return None
    return url


def post_to_slack(text: str) -> bool:
    """Post ``text`` to Slack. Returns True if a message was sent.

    Never raises and never logs the webhook URL.
    """
    url = _webhook_url()
    if not url:
        print("Slack webhook is not configured. Skipping Slack post.")
        return False

    request = urllib.request.Request(
        url,
        data=json.dumps({"text": text}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        # Do not echo the response body; it can contain the webhook in errors.
        print(f"Slack post returned HTTP {exc.code}. Skipping.")
        return False
    except urllib.error.URLError as exc:
        print(f"Slack post failed ({type(exc).__name__}). Continuing without failing the run.")
        return False

    if status == 200:
        print("Posted research summary to Slack.")
        return True
    print(f"Slack post returned HTTP {status}. Skipping.")
    return False


def _message_from_cli() -> str:
    """Read the message from argv[1], or stdin, or a default test string."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1]
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped
    return "Auto Research test message :wave:"


if __name__ == "__main__":
    post_to_slack(_message_from_cli())
