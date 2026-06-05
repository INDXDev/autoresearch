#!/usr/bin/env python3
"""Render the watched pages with Playwright and diff them against their snapshots.

This is the DETERMINISTIC, non-LLM half of the Site Watch section — the fourth
job in the Auto Research workflow. In ONE pass it walks every enabled target in
``config/watch_targets.json`` and, for each page:

1. opens it in headless Chromium (Playwright) and waits for it to settle;
2. extracts the visible text — only the elements matching ``selector`` when one is
   configured, otherwise the whole ``<body>`` — and normalises it to stable lines;
3. compares that against the committed baseline ``snapshots/<slug>.txt``;
4. writes the fresh snapshot back (so the same job can commit it), and — when the
   content changed — appends a unified diff to a single combined report,
   ``.watch_diffs/changes.md``, for the Claude Code step to summarise.

The FIRST time a target is seen there is no baseline, so it just captures one and
reports no change (a baseline run files no Issue — only real changes do).

It reports through ``$GITHUB_OUTPUT`` (``changed`` = did ANY page change) so the
summarise/publish steps can gate on it, and writes ``.watch_diffs/manifest.json``
mapping each changed slug to its +/- line counts (the publisher reads it).

Usage:
    python3 scripts/watch_fetch.py            # fetch + diff every enabled target

Inputs (environment):
    WATCH_TIMEOUT_MS   Playwright navigation timeout in ms (default 30000)
    WATCH_MAX_DIFF     max diff lines kept per page in the report (default 400)
    GITHUB_OUTPUT      Actions step-output file (set automatically in CI)

Security: never prints tokens or any secret.
"""

from __future__ import annotations

import difflib
import json
import os

from watch_targets import DIFF_DIR, SNAPSHOT_DIR, load_targets, snapshot_path

# The single combined report Claude reads, and the machine-readable manifest the
# publisher reads for per-page line counts.
CHANGES_REPORT = os.path.join(DIFF_DIR, "changes.md")
MANIFEST_PATH = os.path.join(DIFF_DIR, "manifest.json")


def _int_env(name: str, default: int) -> int:
    """Read an int env var, falling back to ``default`` on empty/non-numeric.

    A misconfigured repo Variable (e.g. ``WATCH_TIMEOUT_MS=30s``) must degrade to
    the default, not raise.
    """
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def emit_output(**pairs: object) -> None:
    """Append ``key=value`` lines to $GITHUB_OUTPUT (and echo a readable copy)."""
    path = os.environ.get("GITHUB_OUTPUT", "").strip()
    lines: list[str] = []
    for key, value in pairs.items():
        text = "true" if value is True else "false" if value is False else str(value)
        lines.append(f"{key}<<__WATCH_EOF__\n{text}\n__WATCH_EOF__")
        print(f"  {key}={text}")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def normalise_text(raw: str) -> str:
    """Collapse rendered text into stable, diff-friendly lines.

    Trims each line, drops blank lines, and squeezes runs of inner whitespace, so
    cosmetic reflow does not masquerade as a content change. Order is preserved.
    """
    out: list[str] = []
    for line in (raw or "").replace("\r\n", "\n").split("\n"):
        cleaned = " ".join(line.split())
        if cleaned:
            out.append(cleaned)
    return "\n".join(out)


def extract_text(target: dict) -> str:
    """Render the page in headless Chromium and return its normalised text.

    Imported lazily so importing this module never requires Playwright.
    """
    from playwright.sync_api import sync_playwright

    timeout = _int_env("WATCH_TIMEOUT_MS", 30000)
    selector = target.get("selector") or ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(target["url"], wait_until=target["wait_until"], timeout=timeout)
            if selector:
                # Track only the chosen elements (e.g. story titles). Join their
                # individual texts with newlines so each becomes its own diff line.
                page.wait_for_selector(selector, timeout=timeout)
                parts = [el.inner_text() for el in page.query_selector_all(selector)]
                text = "\n".join(parts)
            else:
                text = page.inner_text("body")
        finally:
            browser.close()
    return normalise_text(text)


def diff_target(target: dict) -> dict | None:
    """Render one target, refresh its snapshot, and return its change record.

    Returns ``None`` when there is nothing to report (a fetch error, an empty
    render, a first-run baseline, or no change). Otherwise returns a dict with the
    unified ``diff`` text and the ``added`` / ``removed`` line counts.
    """
    slug = target["slug"]
    print(f"Fetching '{target['name']}' ({target['url']}) …")
    try:
        new_text = extract_text(target)
    except Exception as exc:  # noqa: BLE001 — never fail the run on a flaky fetch.
        print(f"  Could not render the page ({type(exc).__name__}). Skipping this target.")
        return None

    snap = snapshot_path(slug)
    if not new_text.strip():
        # Don't advance the baseline on an empty render (we return before
        # writing it). If a baseline already exists, a configured selector that
        # now matches nothing usually means the page was redesigned — surface
        # that as a warning so it isn't silently swallowed, rather than filing a
        # noisy "everything removed" diff on a possibly-transient outage.
        if target.get("selector") and os.path.exists(snap) and os.path.getsize(snap) > 1:
            print(
                f"::warning title=Site Watch::'{slug}' rendered no text — its selector "
                f"({target.get('selector')!r}) may have changed. Baseline kept; check the page."
            )
        else:
            print("  Rendered text was empty (selector matched nothing?). Skipping.")
        return None

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    first_run = not os.path.exists(snap)
    old_text = ""
    if not first_run:
        with open(snap, encoding="utf-8") as handle:
            old_text = handle.read()

    # Always (re)write the snapshot so the commit step persists the latest state.
    with open(snap, "w", encoding="utf-8") as handle:
        handle.write(new_text + "\n")

    if first_run:
        print(f"  First run for '{slug}': captured a baseline snapshot. No diff to report.")
        return None

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    if old_lines == new_lines:
        print("  No change since the last snapshot.")
        return None

    diff = list(
        difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"{slug} (previous)", tofile=f"{slug} (current)",
            lineterm="", n=2,
        )
    )
    added = sum(1 for ln in diff if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff if ln.startswith("-") and not ln.startswith("---"))
    print(f"  Change detected: +{added} / -{removed} line(s).")
    return {"diff": diff, "added": added, "removed": removed}


def main() -> int:
    targets = load_targets()
    if not targets:
        print("Site Watch: no enabled targets in config/watch_targets.json.")
        emit_output(changed=False, count=0)
        return 0

    max_diff = _int_env("WATCH_MAX_DIFF", 400)

    report_blocks: list[str] = []
    manifest: dict[str, dict[str, int]] = {}

    for target in targets:
        record = diff_target(target)
        if not record:
            continue
        slug = target["slug"]
        manifest[slug] = {"added": record["added"], "removed": record["removed"]}

        diff_lines = record["diff"]
        truncated = ""
        if len(diff_lines) > max_diff:
            diff_lines = diff_lines[:max_diff]
            truncated = f"\n… diff truncated to {max_diff} lines …"
        # One clearly-labelled block per changed page, so Claude reads ONE file
        # and can map each diff back to its slug/name/url.
        report_blocks.append(
            f"## {target['name']}\n"
            f"- slug: `{slug}`\n"
            f"- url: {target['url']}\n"
            f"- lines changed: +{record['added']} / -{record['removed']}\n\n"
            "```diff\n" + "\n".join(diff_lines) + truncated + "\n```"
        )

    if not report_blocks:
        print("Site Watch: nothing changed (or only baselines captured).")
        emit_output(changed=False, count=0)
        return 0

    os.makedirs(DIFF_DIR, exist_ok=True)
    with open(CHANGES_REPORT, "w", encoding="utf-8") as handle:
        handle.write(
            "# Watched pages that changed this run\n\n"
            "Each section below is one changed page: its slug, URL, and a unified "
            "diff of its rendered text (`+` new, `-` removed).\n\n"
            + "\n\n".join(report_blocks) + "\n"
        )
    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False)

    print(f"Site Watch: {len(manifest)} page(s) changed. Wrote {CHANGES_REPORT}.")
    emit_output(changed=True, count=len(manifest), slugs=",".join(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
