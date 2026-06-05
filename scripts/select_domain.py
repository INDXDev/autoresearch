#!/usr/bin/env python3
"""Pick the research DOMAIN (+ output language) for this run — stickily, no LLM.

Auto Research can cover several DOMAINS — research / tech / business / hobby /
finance — each described by a plain Markdown guide under ``config/domains/``.
This script is the DETERMINISTIC half of choosing which one a run covers; the
open-ended "read the menu and pick" half is a tiny Claude Code Action step that
only runs when a fresh choice is actually needed.

Two subcommands mirror the rest of the pipeline:

* ``prepare``  — work out the *effective topic*, hash it, and decide whether a
  past choice can be REUSED (pinned via ``RESEARCH_DOMAIN``, or remembered for
  this exact topic). Emits ``need_pick`` / ``need_lang`` so the workflow knows
  whether to run the Claude picker, and writes ``.auto_state/menu.md`` for it.
* ``finalize`` — merge the Claude pick (or the reused values), validate, persist
  the choice keyed by the topic hash, and emit the final ``domain`` + ``lang``.

State is one file — a map
``{ "<topic_hash>": {"domain": ..., "lang": ..., "topic": ...} }`` — restored
from / saved to the unified ``auto-research-state`` orphan branch by the
workflow. Its path is ``STATE_FILE`` (the workflow sets it to ``selection.json``
at the repo root; the default when unset is ``.auto_state/selection.json``).
This script only reads/writes that local file; it never calls git or an LLM, and
ALWAYS exits 0 so any failure degrades to sensible defaults (``research`` /
``en`` or ``OUTPUT_LANGUAGE``) instead of breaking the run.

Usage:
    python3 scripts/select_domain.py prepare
    SECTION_JSON='{"domain":"finance","lang":"ja"}' \
        python3 scripts/select_domain.py finalize

Inputs (environment):
    RESEARCH_TOPIC     the lab's topic string (falls back to config/research_topics.md)
    RESEARCH_DOMAIN    pin a domain, or 'auto'/unset to let Claude pick
    OUTPUT_LANGUAGE    en | ja — when set, fixes the language (else inferred/remembered)
    SECTION_JSON       finalize only: the Claude picker's structured_output JSON
    STATE_FILE         override the state path (default .auto_state/selection.json)
    GITHUB_OUTPUT      Actions step-output file; key=value lines are appended here

Security: never prints tokens or secrets.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

# The domains a run can cover. Each needs a config/domains/<name>.<lang>.md guide.
DOMAINS: tuple[str, ...] = ("research", "tech", "business", "hobby", "finance")
LANGS: tuple[str, ...] = ("en", "ja")
DEFAULT_DOMAIN = "research"
DEFAULT_LANG = "en"

_HERE = os.path.dirname(__file__)
_TOPICS_FILE = os.path.join(_HERE, "..", "config", "research_topics.md")
_INDEX_FILE = os.path.join(_HERE, "..", "config", "domains", "index.md")
_STATE_FILE = os.environ.get("STATE_FILE", "").strip() or ".auto_state/selection.json"
_MENU_FILE = os.path.join(".auto_state", "menu.md")


def _topic_from_config() -> str:
    """Fallback topic from config/research_topics.md (first few bullets).

    Mirrors ``publish_section.topic_from_config`` so the hash and the published
    Issues key off the SAME effective topic.
    """
    try:
        with open(_TOPICS_FILE, encoding="utf-8") as handle:
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


def effective_topic() -> str:
    """The topic this run is about: RESEARCH_TOPIC, else config, else 'AI'."""
    return os.environ.get("RESEARCH_TOPIC", "").strip() or _topic_from_config() or "AI"


def topic_hash(topic: str) -> str:
    """A short, stable fingerprint of the topic (whitespace/case-insensitive)."""
    normalised = " ".join(topic.split()).lower()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:12]


def norm_lang(value: str | None) -> str:
    """Normalise a language value to 'en' / 'ja', or '' if unrecognised."""
    raw = (value or "").strip().lower()
    if raw in {"ja", "jp", "japanese", "日本語"}:
        return "ja"
    if raw in {"en", "english"}:
        return "en"
    return ""


def norm_domain(value: str | None) -> str:
    """Normalise a domain value to one of DOMAINS, or '' if unrecognised."""
    raw = (value or "").strip().lower()
    return raw if raw in DOMAINS else ""


def load_state() -> dict:
    """Read the {hash: {...}} selection map; '{}' when missing or malformed."""
    try:
        with open(_STATE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict) -> None:
    """Persist the selection map, creating the parent directory as needed."""
    parent = os.path.dirname(_STATE_FILE)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_outputs(**kwargs: object) -> None:
    """Append key=value lines to $GITHUB_OUTPUT (and echo for local runs)."""
    path = os.environ.get("GITHUB_OUTPUT", "").strip()
    lines = [f"{key}={'' if value is None else value}" for key, value in kwargs.items()]
    for line in lines:
        print(line)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def resolve(state: dict, h: str, pick: dict | None) -> tuple[str, str, bool, bool]:
    """Resolve (domain, lang, need_domain, need_lang) from all sources.

    Authority — first non-empty wins:
        domain: RESEARCH_DOMAIN (pinned) > remembered > Claude pick
        lang:   OUTPUT_LANGUAGE        > remembered > Claude pick

    ``need_domain`` / ``need_lang`` report whether the value is still unknown
    (so ``prepare`` can ask the Claude picker to supply it). Returned domain/lang
    may be '' here; ``finalize`` applies the final defaults.
    """
    remembered = state.get(h) if isinstance(state.get(h), dict) else {}

    pinned = norm_domain(os.environ.get("RESEARCH_DOMAIN"))
    domain = pinned or norm_domain(remembered.get("domain"))
    if not domain and pick:
        domain = norm_domain(pick.get("domain"))

    output_lang = norm_lang(os.environ.get("OUTPUT_LANGUAGE"))
    lang = output_lang or norm_lang(remembered.get("lang"))
    if not lang and pick:
        lang = norm_lang(pick.get("lang"))

    return domain, lang, (not domain), (not lang)


def _write_menu(topic: str) -> None:
    """Write the picker's brief: the effective topic + the domain menu."""
    try:
        with open(_INDEX_FILE, encoding="utf-8") as handle:
            index = handle.read().strip()
    except OSError:
        index = "\n".join(f"- {name}" for name in DOMAINS)
    os.makedirs(os.path.dirname(_MENU_FILE), exist_ok=True)
    with open(_MENU_FILE, "w", encoding="utf-8") as handle:
        handle.write(
            f"# Pick the domain for this run\n\n"
            f"**Effective research topic:** {topic}\n\n"
            f"Choose exactly ONE domain from the menu below whose lens best fits "
            f"that topic, and the language to write in.\n\n"
            f"{index}\n"
        )


def cmd_prepare() -> int:
    topic = effective_topic()
    h = topic_hash(topic)
    state = load_state()
    domain, lang, need_domain, need_lang = resolve(state, h, pick=None)
    _write_menu(topic)
    write_outputs(
        topic_hash=h,
        domain=domain,
        lang=lang,
        need_pick="true" if need_domain else "false",
        need_lang="true" if need_lang else "false",
    )
    status = "reusing" if not need_domain else "needs a pick"
    print(f"prepare: topic={topic!r} hash={h} domain={domain or '?'} lang={lang or '?'} ({status})")
    return 0


def cmd_finalize() -> int:
    topic = effective_topic()
    h = topic_hash(topic)
    state = load_state()

    pick: dict | None = None
    raw = os.environ.get("SECTION_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                pick = parsed
        except json.JSONDecodeError:
            print("finalize: SECTION_JSON was not valid JSON; ignoring the pick.")

    domain, lang, _, _ = resolve(state, h, pick=pick)
    # Whether the domain is backed by a REAL source (pin / remembered / pick) or
    # is about to fall back to the bare default.
    real_choice = bool(domain)
    # Apply the final safety nets so downstream jobs always get a real value.
    domain = domain or DEFAULT_DOMAIN
    lang = lang or norm_lang(os.environ.get("OUTPUT_LANGUAGE")) or DEFAULT_LANG

    # Persist ONLY a real choice. A keyless run with no pin/memory/pick would
    # otherwise freeze the guessed default into sticky state, so `prepare` would
    # never ask the picker again even after a credential is added later.
    if real_choice:
        state[h] = {"domain": domain, "lang": lang, "topic": topic}
        save_state(state)
    write_outputs(domain=domain, lang=lang, topic_hash=h)
    note = "saved" if real_choice else "default (not persisted — awaiting a real pick)"
    print(f"finalize: topic={topic!r} hash={h} -> domain={domain} lang={lang} ({note})")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        return cmd_prepare()
    if cmd == "finalize":
        return cmd_finalize()
    print("Usage: select_domain.py <prepare|finalize>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
