# Site Watch — change-summary guidance

The Site Watch workflow renders a page you watch (see `config/watch_targets.json`),
diffs it against the last snapshot, and — only when it changed — asks Claude Code
to summarise the **unified diff** into a structured JSON object. A Python script
turns that JSON into one GitHub Issue (and an optional Slack line).

This file is the editable guidance the summarise step reads each run. Tune it to
your taste.

## How to read the diff

- It is a standard unified diff of the page's normalised text.
- Lines starting with `+` are **new** content; `-` lines were **removed**.
- Unchanged context lines (no prefix) are only there to anchor the change.

## What to surface

- **New items** are the signal: a new story, post, release, headline, price,
  status, or section. Lead with those.
- Group related lines into a single change when they describe one thing.
- Give each change a short, human title. Add a one-line `detail` only when it
  genuinely helps (what it is / why it matters).
- Keep the top-level `summary` to 1–3 sentences: the gist a busy reader needs.

## What to ignore

- Pure churn with no new content: vote/point counts, comment tallies, "N minutes
  ago" timestamps, ad rotations, reordering of the same items.
- If the **entire** diff is that kind of noise, set `no_meaningful_change` to
  `true` and leave `changes` empty — the publisher will then file nothing.

## Honesty

- Only include a URL you actually saw in the diff or opened with WebFetch. Never
  invent links, titles, or details. When unsure, describe the change in words and
  leave the URL blank.
