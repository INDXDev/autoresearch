# Project guide for Claude (Auto Research)

This repository is an **Auto Research** template. Inside GitHub Actions, you
(Claude Code) run the **research half** of each section: you web-search the
topic and return a **schema-validated JSON object** as structured output. A
small Python script then deterministically turns that JSON into GitHub Issues —
**one Issue per item** (each news item, paper, or hypothesis is its own Issue).

So the split is:

- **You (Claude Code Action):** the open-ended, trial-and-error part — search,
  read, reason, and emit structured JSON. **You do not create Issues or files.**
  Claude is the **main** engine. If a run has no Claude credential but an OpenAI
  one (`OPENAI_API_KEY` / `CODEX_ACCESS_TOKEN`), the local composite action
  `.github/actions/agent` falls back to **OpenAI Codex** (`openai/codex-action`)
  as the **sub**, normalising its reply with `scripts/extract_json.py` into the
  same schema-shaped JSON. Claude always wins when both are present.
- **Python (`scripts/publish_section.py`):** the deterministic part — iterates
  the array, formats each item into Markdown, opens one Issue per item, writes
  optional files, and emits one Slack line (and, when configured, one email) per
  item. Each line's **primary** link is a public URL — the item's page on the
  published Pages site (resolved live via `scripts/site_url.py`), else the
  GitHub Issue. The Issue is shown as a secondary `↳` link when the site page
  leads, and becomes the primary only as a fallback. The curated source URL (the
  paper/article) stays inside the Issue body, not the notification.
- **One combined send per run.** The four section jobs run in parallel and would
  each fire their own Slack post + email. By default (`COMBINE_NOTIFICATIONS` ≠
  `false`) every publisher routes its lines through `scripts/notify.py`, which —
  seeing `NOTIFY_SPOOL_DIR` set — **spools** each block to `.notify/` instead of
  sending. Each section uploads that as a `notify-<section>` artifact; a final
  `notify` job downloads them all and runs `scripts/notify_combined.py` to fold
  every section into **one Slack post and one email** for the whole run (ordered
  Latest → Takes → Foundations → Site Watch). Pin `COMBINE_NOTIFICATIONS=false`
  to go back to per-section sends.

## What matters

- **Use real web search.** Ground every item in sources you actually opened via
  the WebSearch / WebFetch tools. Prefer arXiv, Semantic Scholar, top venues,
  and reputable blogs. **Never fabricate** papers, authors, dates, or URLs. If
  unsure, leave a field blank or describe the type of work — do not invent a
  citation.
- **Return ONLY the JSON required by the `--json-schema`.** Do not wrap it in
  prose or Markdown. The schema is the contract; the Python publisher renders it.
- **Respect the configuration** in the prompt: output language (write the text
  fields in that language), research topic, and the per-section instructions.
- Read `config/research_topics.md` for the lab's topics/notes, and
  `config/prompts/` for per-section guidance.
- **Security:** never print or echo secrets, tokens, or the Slack webhook URL.

## Domains: one lens per run (research / tech / business / hobby / finance)

A run is not limited to academic research. The **`select` job** runs first and
picks ONE **domain** — `research`, `tech`, `business`, `hobby`, or `finance` —
each described by a plain Markdown guide under `config/domains/<domain>.<lang>.md`
(English + 日本語). The three section jobs then `needs: select` and share that
choice. Whatever the domain, every run produces the SAME three generic layers,
and the chosen domain guide says what each layer means in that domain:

- **Foundations** (the `related` section) — the unwavering, slow-moving facts.
- **Latest** (the `news` section) — recent, concrete developments.
- **Takes** (the `hypotheses` section) — interpretations / theses, each testable.

How the domain + language are decided (you usually set NO Variables):

- **Domain:** default `auto` — a tiny Claude picker reads `config/domains/index.md`
  and the topic and chooses. Pin it with the `RESEARCH_DOMAIN` Variable if you want.
- **Language:** `OUTPUT_LANGUAGE` when set; otherwise the picker infers it from the
  topic.
- **Sticky:** `scripts/select_domain.py` hashes the effective topic and REMEMBERS
  `{domain, lang}` for that hash on the `auto-research-state` orphan branch, so the
  choice only changes when the topic changes. The picker step runs only when a fresh
  choice is actually needed (or never, with no Claude key → sensible defaults).

When you are the picker, return ONLY `{"domain": ..., "lang": ...}`. When you are a
section, `Read` the named `config/domains/<domain>.<lang>.md` FIRST and follow it.

## How a run is wired (per section, in parallel)

1. `select` job: `scripts/select_domain.py prepare` decides if a fresh pick is
   needed; if so a small Claude step picks the domain + language; `finalize`
   remembers it on `auto-research-state`. Exposes `domain` / `lang` outputs.
2. `news` / `hypotheses` / `related` are independent jobs (`needs: select`), each
   gated by its flag, all sharing the run's domain + language.
3. Context step: `scripts/existing_context.py` summarises Issues from prior runs
   (plus any 👍/👎 reaction or good/bad label feedback) into
   `.research_context/<section>.md`. Your prompt tells you to `Read` it so you
   avoid duplicates and lean toward what was marked good.
4. Research step: `anthropics/claude-code-action@v1` runs you with a prompt +
   `--json-schema` → `structured_output`. Each Issue also gets a `domain:<domain>`
   label.
5. Publish step: `python3 scripts/publish_section.py <section>` reads that JSON
   and creates one labelled Issue per item.

## The 4th section: Site Watch (Playwright page diffs)

Alongside news / hypotheses / related work, the Auto Research workflow has a
fourth job — **Site Watch** — that watches web pages for changes (e.g. the Hacker
News front page). Same two-halves philosophy, applied to diffing:

- **Python (`scripts/watch_fetch.py`):** renders every page in
  `config/watch_targets.json` with **Playwright**, normalises its text, and diffs
  it against the baseline in `snapshots/<slug>.txt`. It writes the diffs of all
  changed pages into one report, `.watch_diffs/changes.md`. Deterministic. The
  baselines are **not** kept on the default branch — the workflow restores them
  from the unified `auto-research-state` orphan branch before this step and saves
  the refreshed ones back there afterward (sharing it with the domain selection
  state via the `scripts/restore_state.sh` / `scripts/save_state.sh` helpers), so
  main's history stays clean.
- **You (Claude Code Action):** run **only when something changed** — you `Read`
  `.watch_diffs/changes.md` (plus `config/prompts/watch_summary.md`) and return a
  schema-validated JSON object with one entry per changed page (copy each `slug`).
  **You do not create Issues, commit snapshots, or invent links.**
- **Python (`scripts/publish_watch.py`):** turns that JSON into one GitHub Issue
  per changed page (labelled `site-watch` + `watch:<slug>`) and an optional Slack
  line; the job then saves the refreshed snapshots back to the unified
  `auto-research-state` orphan branch so the next run diffs against the latest state.

The first time a target is seen there is no baseline, so that run just captures
one and files nothing. If a page's diff is pure noise (vote counts, timestamps,
reordering), set its `no_meaningful_change: true` and leave `changes` empty so the
publisher files nothing for it.

## Auto-labelling: topical tags on today's Issues

A separate workflow (`.github/workflows/auto-label.yml`) runs **after** the Auto
Research workflow finishes (and on manual dispatch). It adds **topical labels**
to the Issues that run just created — on top of the pipeline labels they already
carry (`auto-research`, `research-news`, …). Same two-halves split:

- **Python (`scripts/label_context.py`):** lists today's Issues (across every
  section) plus the repo's existing label taxonomy into
  `.label_context/issues.md`, and reports `has_issues` so the LLM step is skipped
  when nothing was generated. Deterministic.
- **You (Claude Code Action):** `Read` that file (plus `config/prompts/labeling.md`)
  and return a schema-validated JSON object — one entry per Issue with its `issue`
  number and an `add` list of labels. Reuse existing labels where they fit; invent
  short, reusable new ones only when needed. **You do not call the GitHub API.**
- **Python (`scripts/apply_labels.py`):** adds those labels to each Issue
  (ADDITIVE — existing labels are kept; GitHub auto-creates new ones).

## The wrap-up: a rich Astro + Starlight site on the `gh-pages` branch

A separate workflow (`.github/workflows/publish-site.yml`) runs **after** the
**Auto Label** or **Auto Research** workflow finishes (and on manual dispatch).
It reads **all** the Issues back — the single source of truth, including the
`site-watch` ones — together with each Issue's **labels (tags)**, **reactions**,
and **comments**, and turns them into a rich documentation website. Same
two-halves split, no LLM:

- **Python (`scripts/build_site.py`):** reads the Issues (+ comments via
  `scripts/github_issue.py:list_comments`) and deterministically emits Markdown
  into `site/src/content/docs/` — `index.md` (splash landing page: hero + stat
  cards + browse-by-section cards + run list + browse-by-reaction strip), one
  `runs/<date>.md` per execution (compact cards grouped by section 📰 / 💡 / 📚 /
  👀), one **`items/<number>.md`** per item (the FULL body + **tags** + **reaction**
  chips + **comments**), one **`sections/<key>.md`** per layer (Latest / Takes /
  Foundations / Site Watch), one **`reactions/<slug>.md`** per reaction (👍 ❤️ …),
  and one `tags/<slug>.md` per topical tag. Every card title links to that item's
  own on-site page (navigation stays on the site); the source GitHub Issue is only
  a small secondary button. Cards are plain Markdown with embedded, escaped HTML —
  source/comment text is inert.
- **Astro + Starlight (`site/`):** builds those Markdown files into a static
  site with a sidebar, full-text search (Pagefind), dark mode, and responsive
  layout. The optional **giscus** widget (live comments/reactions backed by
  GitHub Discussions) is injected by `site/src/components/Footer.astro` only when
  the `GISCUS_*` repo Variables are set.
- **Deploy:** `peaceiris/actions-gh-pages` pushes the built `site/dist` to the
  dedicated **`gh-pages` branch** (Pages Source = "Deploy from a branch"), so
  `main`'s history stays clean — same pattern as the `auto-research-state` branch.

**You do not build or deploy the site** — that's Python + Astro + Actions; your
half is still only research / diff-summary → structured JSON.

### The site's look is AI-designed once, then sticky (per topic)

The site's **presentation** — its **title**, hero **tagline**, and the single
**brand colour** the theme paints every link / button / active state with — is
itself chosen by a tiny agent step, exactly like the domain picker. In the
`select` job, after the domain is fixed, `scripts/site_config.py prepare` checks
whether a look is already remembered for this topic hash; only on the FIRST run
for a topic does a small Claude step (`Read` `.auto_state/site_brief.md`) return
`{site_title, tagline, brand_color}`, which `finalize` validates and remembers in
`site_config.json` on the unified `auto-research-state` branch (skipped on every
later run). At build time the publish-site workflow restores that file and
`scripts/site_config.py emit` turns it into `site/src/styles/theme.css` (CSS
variable overrides, loaded after `custom.css`) plus the `SITE_TITLE` /
`SITE_TAGLINE` the Astro build reads. A repo Variable still wins — authority is
**`SITE_TITLE` pin > AI design > shipped default** — so each user can override
any field, while the agent designs a fitting look on its own the very first run.
This is still your research half only: you return the design JSON; Python writes
the CSS and the site.

## Useful files

- `config/research_topics.md` — the lab's topics and notes.
- `config/domains/` — the per-domain Markdown guides (`index.md` menu +
  `<domain>.{en,ja}.md`) that say what each layer means in that domain.
- `config/priority_sources.md` — URLs to WebFetch first, before open-ended search.
- `config/watch_targets.json` — the pages Site Watch renders + diffs (Hacker News by default).
- `config/prompts/` — editable prompt guidance per section (incl. `watch_summary.md`, `labeling.md`).
- `.github/actions/agent/action.yml` — the local composite action every LLM step
  uses: run Claude (main) if a Claude credential exists, else fall back to OpenAI
  Codex (sub); returns the same `structured_output` either way.
- `scripts/extract_json.py` — normalises the Codex sub's free-form `final-message`
  into one clean JSON object for the publishers (no-op for Claude; deterministic, no LLM).
- `scripts/select_domain.py` — deterministic domain/language picker: topic hash,
  sticky `{domain,lang}` memory, menu generation (no LLM).
- `scripts/site_config.py` — deterministic site-look half: `prepare`/`finalize`
  remember the AI-designed `{site_title, tagline, brand_color}` per topic hash on
  `auto-research-state`; `emit` renders `site/src/styles/theme.css` + the
  `SITE_TITLE`/`SITE_TAGLINE` env at build time (sticky, no LLM here).
- `scripts/restore_state.sh` / `scripts/save_state.sh` — shared helpers that
  restore/save paths on the unified `auto-research-state` orphan branch (race-safe).
- `scripts/existing_context.py` — builds the prior-Issue de-dup digest + 👍/👎 feedback (no LLM).
- `scripts/publish_section.py` — deterministic JSON → Issue publisher for the research sections (no LLM).
- `scripts/label_context.py` — gathers today's Issues + existing labels for the auto-labeler (no LLM).
- `scripts/apply_labels.py` — deterministic auto-label JSON → additive Issue labels (no LLM).
- `scripts/watch_fetch.py` — Playwright render + diff vs `snapshots/<slug>.txt` baseline (kept on the unified `auto-research-state` branch; no LLM).
- `scripts/publish_watch.py` — deterministic Site Watch JSON → Issue publisher (no LLM).
- `scripts/watch_targets.py` — shared loader for `config/watch_targets.json` (no LLM).
- `scripts/build_site.py` — deterministic Issues (+ labels/reactions/comments) → Starlight Markdown under `site/` (no LLM).
- `site/` — the Astro + Starlight documentation site (scaffold committed; generated content + build output are gitignored).
- `scripts/slack_post.py` — safe Slack poster (skips when unset, never logs URL).
- `scripts/email_post.py` — safe Resend email sender; mirrors every Slack line when `RESEND_API_KEY` + `EMAIL_TO` are set (skips otherwise, never logs the key).
- `scripts/notify.py` — the single send entry point every publisher uses: sends to Slack + email now, OR (when `NOTIFY_SPOOL_DIR` is set) spools each block for one combined run send; also owns the `primary_link` rule (Pages page → Issue).
- `scripts/notify_combined.py` — the `notify` job's step: folds every section's spooled blocks into ONE Slack post + ONE email per run (no LLM, no GitHub writes).
- `scripts/site_url.py` — resolves the live GitHub Pages site URL (via the `pages: read` API) so each Slack/email line links to the item's on-site page; returns `None` when Pages isn't enabled, so the publisher falls back to the GitHub Issue link.
