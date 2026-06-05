---
name: Bug report
about: Something in the template isn't working as documented
title: "[bug] "
labels: bug
---

**What happened**
A clear, concise description of the bug.

**What you expected**
What you thought would happen instead.

**Where**
- [ ] Research step (Claude Code Action)
- [ ] Publish step (`scripts/publish_section.py`)
- [ ] Context / de-dup step (`scripts/existing_context.py`)
- [ ] Slack
- [ ] Docs

**Logs**
Paste the relevant GitHub Actions log lines. **Do not paste secrets** — tokens,
API keys, and the Slack webhook URL must never appear here.

**Settings (Variables only — never Secrets)**
e.g. `RESEARCH_TOPIC`, `OUTPUT_LANGUAGE`, `ITEMS_PER_REPORT`, which reports are enabled.
