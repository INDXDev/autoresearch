# Contributing to Auto Research

Thanks for your interest! This is a small, deliberately simple template — the
goal is for someone to read the whole thing in one sitting. Contributions that
keep it that way are very welcome.

## Ground rules

- **Keep it dependency-free.** The Python scripts use only the standard library
  (`urllib`, `json`). Please don't add third-party packages.
- **Keep the two halves clean.** Claude does the open-ended research and returns
  schema-validated JSON; Python does everything deterministic (formatting,
  Issues, Slack). No LLM calls in the Python scripts.
- **Never log secrets.** Tokens, API keys, and the Slack webhook must never be
  printed. Existing helpers already enforce this — keep it that way.
- **Update both READMEs.** User-facing changes go in `README.md` *and*
  `README.ja.md`, and any new setting goes in the Settings reference table and
  `.env.example`.

## Run the publisher locally

The deterministic half runs with no setup (creating Issues needs `GITHUB_TOKEN`):

```bash
export SECTION_JSON='{"items":[{"title":"Example","url":"https://arxiv.org/abs/0000.00000","takeaway":"…"}]}'
ENABLE_FILE_OUTPUT=true ENABLE_GITHUB_ISSUE=false python3 scripts/publish_section.py news
# → renders one file per item under outputs/
```

Swap `news` for `hypotheses` or `related` (adjust the JSON shape to match the
`--json-schema` in `.github/workflows/auto-research.yml`).

## Add a new report (section)

1. Copy one of the three jobs in `.github/workflows/auto-research.yml`, give it a
   prompt and a `--json-schema`.
2. Add a matching `items_*` renderer and a `SECTIONS` entry (tag + emoji + name
   key) in `scripts/publish_section.py`.
3. Add the section's display name and any new scaffolding strings to
   `scripts/i18n.py` (both `en` and `ja`).

## Pull requests

Keep PRs focused and small. Describe what changed and why. If you touched the
publisher, paste the output of the local run above so reviewers can see the
rendered Markdown.
