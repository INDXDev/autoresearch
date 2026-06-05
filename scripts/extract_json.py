#!/usr/bin/env python3
"""Normalise an LLM's free-form reply into one clean JSON object.

Claude Code Action returns `structured_output` that is already a clean,
schema-validated JSON string. The Codex fallback (`openai/codex-action`) only
exposes a `final-message`, and although we ask Codex to "output ONLY JSON", it
may still wrap the object in prose or a ```json fence — and a known Codex bug
makes `--output-schema` unreliable when web search / tools are active. So when
the run used the Codex sub, we pass its final message through this script to
recover the single JSON object the downstream publishers expect.

Deterministic, no LLM, no third-party deps — same spirit as the other
`scripts/*.py` helpers. Reads the raw text from the RAW env var (or stdin),
writes the compact JSON to stdout, and — when running in GitHub Actions — also
appends `json=<compact>` to $GITHUB_OUTPUT.
"""

from __future__ import annotations

import json
import os
import sys


def _strip_fences(text: str) -> str:
    """Drop a leading ```json / ``` fence and its closing ```, if present."""
    t = text.strip()
    if t.startswith("```"):
        # remove the opening fence line (``` or ```json …)
        nl = t.find("\n")
        if nl != -1:
            t = t[nl + 1 :]
        # remove a trailing closing fence
        if t.rstrip().endswith("```"):
            t = t.rstrip()[: -3]
    return t.strip()


def _balanced_objects(text: str):
    """Yield each complete, brace-balanced ``{ … }`` span in ``text`` in order.

    Braces inside strings (respecting backslash escapes) are ignored, so prose
    before/after an object — or stray braces in string values — don't throw the
    match off. Yielding ALL spans (not just the first) lets the caller skip a
    leading ``{…}`` that is prose-with-braces and reach the real JSON object.
    """
    i = 0
    n = len(text)
    while True:
        start = text.find("{", i)
        if start == -1:
            return
        depth = 0
        in_str = False
        escaped = False
        end = -1
        for j in range(start, n):
            ch = text[j]
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end == -1:
            return  # unbalanced from here on — no further complete objects
        yield text[start : end + 1]
        i = end + 1


def _as_object(value: object) -> dict | None:
    """Coerce a parsed JSON value to the single object the publishers expect.

    Returns the dict itself, unwraps a single-element ``[ {…} ]`` array (a common
    Codex malformation), or None when there's no usable object.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return None


def extract(raw: str) -> dict:
    """Recover the JSON object from a raw LLM reply, or raise ValueError."""
    if not raw or not raw.strip():
        raise ValueError("empty input — no JSON to extract")

    candidate = _strip_fences(raw)

    # Fast path: the whole (de-fenced) message is already valid JSON (and a
    # usable object, possibly wrapped in a single-element array).
    try:
        obj = _as_object(json.loads(candidate))
        if obj is not None:
            return obj
    except json.JSONDecodeError:
        pass

    # Otherwise scan for balanced { … } spans and return the FIRST that parses
    # to a usable object — skipping any earlier prose-with-braces span.
    for text in (candidate, raw):
        for span in _balanced_objects(text):
            try:
                obj = _as_object(json.loads(span))
            except json.JSONDecodeError:
                continue
            if obj is not None:
                return obj
    raise ValueError("no JSON object found in input")


def main() -> int:
    raw = os.environ.get("RAW")
    if raw is None:
        raw = sys.stdin.read()

    try:
        data = extract(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        # Don't fail the job — emit a warning and leave the `json` output empty so
        # the publish step's `!= ''` guard skips cleanly, matching the template's
        # "every job succeeds with a note" behaviour. (Stay quiet about the raw
        # content; it may be large.)
        print(f"::warning title=Codex output::could not parse JSON from the Codex sub ({exc}); skipping publish.", file=sys.stderr)
        return 0

    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    print(compact)

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # compact is single-line (json.dumps emits no newlines), so a heredoc
        # delimiter keeps it robust even if a string value contained one.
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("json<<__AGENT_JSON_EOF__\n")
            fh.write(compact + "\n")
            fh.write("__AGENT_JSON_EOF__\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
