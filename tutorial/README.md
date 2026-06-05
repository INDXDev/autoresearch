# 📘 Auto Research — Step-by-Step Tutorial

🌐 **English (this page)** ・ [日本語](README.ja.md)

This tutorial walks you through Auto Research **one step at a time**, from a
blank GitHub account to a repository that files a fresh, web-sourced research
briefing every morning. No server, no code required — just a browser and about
five minutes.

If you only want the condensed version, the main [README](../README.md) has a
Quickstart. This page is the slow, careful walkthrough that explains *why* each
step exists.

> 🧭 Built for **researchers** first — but the same engine doubles as a daily
> **tech / business / hobby / finance** tracker; it picks the right lens per topic
> (see [Step 5](#step-5--optional-choose-your-research-topic)). Every run files
> four parallel jobs into **GitHub Issues**, and can also publish a **GitHub Pages
> docs site** and ping **Slack**.

---

## Before you begin

You will need:

- A **GitHub account** (free is fine).
- **One** Claude credential — either:
  - a **Claude Pro/Max plan** (we'll generate a token from it), **or**
  - **API billing** at [console.anthropic.com](https://console.anthropic.com).
- *(Optional)* A **Slack workspace** where you can create an Incoming Webhook,
  if you want a chat ping for each result.

You do **not** need: a server, a credit card for GitHub, Python installed
locally, or any coding.

> 💡 **Good to know:** every step below is reversible, and the workflow is
> designed to *never break while you set up*. If a credential is missing, the
> scheduled run still succeeds and leaves a note telling you exactly what to add.

---

## Step 1 — Create your own copy from the template

Auto Research is a **GitHub repository template**. You don't fork it or clone it;
you stamp out your own independent copy.

1. Open the template repository on GitHub.
2. Click the green **"Use this template"** button near the top right.
3. Choose **"Create a new repository"**.
4. Give it a name (e.g. `my-auto-research`) and pick **Public** or **Private**.
   - Public repos get **free unlimited GitHub Actions minutes**, so they're the
     cheapest option. Private repos work too but consume your Actions quota.
5. Click **"Create repository"**.

You now have your own copy with all the workflow, scripts, and config files.

> **Why a template and not a fork?** A template gives you a clean repo with no
> upstream link and no shared history — it's *yours* to edit freely.

---

## Step 2 — Enable GitHub Actions

GitHub disables Actions on brand-new repositories created from templates, as a
safety default. You need to turn them on once.

1. In your new repository, click the **Actions** tab at the top.
2. You'll see a prompt explaining workflows are disabled. Click the button to
   **enable workflows** (often labelled *"I understand my workflows, go ahead
   and enable them"*).

That's it — the scheduled job is now allowed to run.

---

## Step 3 — Get one Claude credential

Auto Research needs to talk to Claude. Pick **one** of these two paths — you do
**not** need both.

### Option A — Claude Pro/Max plan (OAuth token)

If you subscribe to a Claude **Pro** or **Max** plan, you can mint a token from
it without separate API billing:

1. Install Claude Code locally if you haven't:
   `npm install -g @anthropic-ai/claude-code` (or follow the official install
   docs).
2. In a terminal, run:

   ```bash
   claude setup-token
   ```

3. Log in through the browser window it opens.
4. Copy the token it prints to your terminal. This is your
   `CLAUDE_CODE_OAUTH_TOKEN`.

### Option B — API billing (API key)

If you'd rather pay per use:

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Create an **API key**.
3. Copy it. This is your `ANTHROPIC_API_KEY`.

> **Which should I pick?** If you already pay for a Pro/Max plan, Option A reuses
> that subscription. If not, Option B (pay-as-you-go) is simplest. Either one
> works identically for Auto Research.

---

## Step 4 — Add your credential as a repository Secret

A **Secret** is an encrypted value GitHub never prints to logs — the right place
for a token or key.

1. In your repo, go to **Settings → Secrets and variables → Actions**.
2. Click the **Secrets** tab.
3. Click **"New repository secret"**.
4. Fill it in based on which credential you got in Step 3:

   | If you have… | Name the secret | Paste as the value |
   | --- | --- | --- |
   | A plan token (Option A) | `CLAUDE_CODE_OAUTH_TOKEN` | the token from `claude setup-token` |
   | An API key (Option B) | `ANTHROPIC_API_KEY` | the key from the console |

5. Click **"Add secret"**.

> ⚠️ Add **only one** of these two. Don't paste a token into the API-key slot or
> vice versa — the names matter.

---

## Step 5 — (Optional) Choose your research topic

By default Auto Research searches the broad topic `AI`. To focus it:

1. Go to **Settings → Secrets and variables → Actions** and open the
   **Variables** tab (not Secrets — the topic isn't sensitive).
2. Click **"New repository variable"**.
3. Name it `RESEARCH_TOPIC` and set the value to your topic, e.g.
   `Retrieval-augmented generation`, `protein folding`, or `RISC-V compilers`.
4. Click **"Add variable"**.

**For richer, lab-specific results**, also edit the file
**`config/research_topics.md`** in your repo (click the pencil ✏️ icon on GitHub
to edit in the browser) and list your topics, datasets, constraints, and open
questions. Claude reads this file on every run for extra context.

**To prioritise the sources you trust**, edit **`config/priority_sources.md`**
and list the feeds, blogs, or listing pages you follow — one URL per bullet.
Before its open-ended web search, Claude fetches those URLs **first** and
follows the specific item links it finds on them, so your favourite sources get
crawled preferentially every run. They're priorities, not a whitelist — after
using them Claude still searches freely for anything else new.

**The lens is automatic.** A run isn't limited to academic research — it can read
your topic through one of five domains (**research / tech / business / hobby /
finance**, each a guide under `config/domains/`). By default the domain is `auto`:
a tiny picker reads the topic at the start of each run, chooses the best-fitting
lens, and remembers it for that topic. You normally set **nothing** here. To pin
it, add a `RESEARCH_DOMAIN` Variable set to one of those five.

---

## Step 6 — Run it now (don't wait for the schedule)

You don't have to wait until tomorrow morning — trigger a run by hand to see it
work.

1. Go to the **Actions** tab.
2. In the left sidebar, click the **"Auto Research"** workflow.
3. Click the **"Run workflow"** button on the right, then confirm.
4. Watch the run appear. It takes a few minutes — Claude is web-searching real
   sources and the publisher is creating Issues.

When it finishes, open the **Issues** tab. You'll see new Issues — **one per
item** — each titled, labelled, and carrying a real, clickable source link.

> 💡 If you didn't add a credential yet, the run **still succeeds** but creates no
> research Issues; the log prints a `::notice` telling you exactly what to add.
> Go back to Step 4, then re-run.

---

## Step 7 — Read, triage, and steer the results

Each result is a normal GitHub Issue, so it slots into how you already work:

- **Read** the one-line takeaway and click through to the source.
- **Comment**, **assign**, or **close** Issues like any other.
- **Filter by tag.** A follow-up *Auto Label* workflow adds **topical tags** to each
  day's Issues automatically (on top of the pipeline labels), so you can slice the
  backlog by subject.
- **Steer the next run** with a single click:
  - React **👍** on an Issue you liked → Claude produces *more* like it.
  - React **👎** on one you didn't → Claude *avoids* that kind next time.
  - (Adding a `good` / `bad` label does the same thing.)

Every run also first summarises the Issues it already opened and is told **not**
to repeat them — so you get genuinely new material each day, not the same papers
again.

---

## Step 8 — Let it run daily

You're done. From here on, the workflow runs **automatically once a day** (the
default is 04:17 JST / 19:17 UTC) and files fresh Issues while you sleep.

To change *when* it runs, edit the single `cron` line in
**`.github/workflows/auto-research.yml`** (cron times are always in **UTC**):

```yaml
schedule:
  - cron: "0 22 * * *"   # 07:00 JST daily
  - cron: "17 19 * * 1"  # 04:17 JST on Mondays only
  - cron: "0 */12 * * *" # every 12 hours
```

Build your own schedule at [crontab.guru](https://crontab.guru). You can always
trigger a manual run from the Actions tab too (Step 6).

---

## Optional add-ons

These are all one-line settings under **Settings → Secrets and variables →
Actions**. None require code edits.

### Get a Slack ping for each item

1. Create a Slack [Incoming Webhook](https://api.slack.com/messaging/webhooks)
   and copy its URL.
2. Add it as a **Secret** named `SLACK_WEBHOOK_URL`.

Each item then posts a one-line message — led by its section emoji
(📰 / 💡 / 📚 / 👀) — with its title and a link to its Issue. By default each
section is bundled into a single digest post; set `SLACK_DIGEST=false` for one
message per item. There's no separate on/off flag: the webhook's presence **is**
the switch. No webhook, no post.

### Write in Japanese instead of English

Set the **Variable** `OUTPUT_LANGUAGE` to `ja` (default is `en`). This switches
both the language Claude writes in **and** the headings/labels in each Issue.

### Pick which of the four jobs you want

Each is an independent, parallel job you can switch off by setting its
**Variable** to `false`:

| Variable | Controls | Default |
| --- | --- | --- |
| `ENABLE_RESEARCH_NEWS` | 📰 News report | on |
| `ENABLE_HYPOTHESIS_GENERATION` | 💡 Hypotheses report | on |
| `ENABLE_RELATED_WORK` | 📚 Related Work report | on |
| `ENABLE_SITE_WATCH` | 👀 Site Watch page-diff watcher | on |

**Site Watch** watches web pages you list in **`config/watch_targets.json`** (it
ships watching the Hacker News front page) with a real headless browser and, when
one changes, files an Issue summarising what's new. The first run on a new page
just captures a baseline and files nothing.

### Publish a docs site of everything

A second workflow, **`publish-site.yml`**, runs right after each Auto Research /
Auto Label run and turns every Issue into a rich **Astro + Starlight** docs site —
sidebar, full-text search, dark mode, with each item's tags, reactions, and
comments. It deploys to dedicated **`gh-pages*`** branches. **One-time setup:**
since the serving location decides the `base` path baked into the CSS/JS, the
first run (no `SITE_BASE` Variable) publishes both **`gh-pages`** (base
`/<repo>/`, public project Pages) and **`gh-pages-root`** (base `/`, private root
Pages). Open *Settings → Pages → Build and deployment*, set **Source = "Deploy
from a branch"** and pick whichever branch **renders with its CSS**. Your site
goes live at `https://<you>.github.io/<repo>/` for the public case. (Lock it in
by setting `SITE_BASE` to `/` or `/<repo>/` — then only the matching branch is
rebuilt.)

### Also save each item as a Markdown file

Set `ENABLE_FILE_OUTPUT=true` to *additionally* write one file per item
(`outputs/YYYY-MM-DD-<section>-<n>.md`) and upload them as a downloadable GitHub
Actions artifact. Off by default — Issues are the primary output.

### Tune the count and the model

- `ITEMS_PER_REPORT` (default `5`) — roughly how many items per report.
- `ANTHROPIC_MODEL` (default `claude-sonnet-4-6`) — which Claude model to use.

See the [Settings reference](../README.md#settings-reference) in the main README
for the full list.

---

## Try the publisher locally (no GitHub needed)

The research half needs the Claude Code Action, but the deterministic
**publisher** runs anywhere with Python — handy for previewing the Markdown. It
uses only the standard library, so there's nothing to install:

```bash
export SECTION_JSON='{"items":[{"title":"Example","url":"https://arxiv.org/abs/0000.00000","takeaway":"…"}]}'
export OUTPUT_LANGUAGE=en
ENABLE_FILE_OUTPUT=true python3 scripts/publish_section.py news
# → renders outputs/<date>-news-01.md, one file per item
#   (creating Issues would need GITHUB_TOKEN)
```

---

## Troubleshooting

| Symptom | Likely cause & fix |
| --- | --- |
| Run succeeds but no research Issues appear | No Claude credential. Check the run log for a `::notice`, then add `CLAUDE_CODE_OAUTH_TOKEN` **or** `ANTHROPIC_API_KEY` (Step 4). |
| "Run workflow" button is missing | Actions not enabled yet (Step 2), or you're not on the **Auto Research** workflow in the sidebar. |
| No Slack messages | `SLACK_WEBHOOK_URL` not set, or set to a dummy value. The log prints `Slack webhook is not configured. Skipping Slack post.` |
| Output is in the wrong language | Set the `OUTPUT_LANGUAGE` Variable to `en` or `ja`. Anything unrecognised falls back to English. |
| Same papers showing up again | Raise `EXISTING_CONTEXT_MAX` so more prior Issues are summarised for de-duplication (default `40`). |
| Topic is too broad/generic | Set `RESEARCH_TOPIC` and flesh out `config/research_topics.md` (Step 5). |

> **Security note:** secrets — the API key, OAuth token, and Slack webhook — are
> **never printed** to the logs. `.env` is gitignored; only `.env.example` (dummy
> values) is committed.

---

## What's next

- **[Main README](../README.md)** — the full capability list and settings reference.
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — how to extend the template.
- **Going further:** add a new report, enrich a schema, build a daily digest, or
  run a matrix across many topics — see the [Going further](../README.md#going-further)
  section.

Happy researching! 🔬
