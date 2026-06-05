# Domain menu

Auto Research can cover any ONE of the domains below per run. Each is a *lens* —
a way of looking at the run's topic. The picker reads this menu plus the
effective topic and chooses the single domain whose lens fits best, then writes
in the chosen language.

Pick by `key` (the slug used to load `config/domains/<key>.<lang>.md`).

| key        | domain        | use this lens when the topic is about…                                  |
|------------|---------------|--------------------------------------------------------------------------|
| `research` | Research      | science, academia, papers, methods, theory, experiments                  |
| `tech`     | Tech          | software, engineering, products, tools, infrastructure, open source      |
| `business` | Business      | companies, strategy, markets, management, startups, go-to-market         |
| `hobby`    | Hobby         | crafts, games, sports, gear, cooking, music, outdoors, enthusiast culture |
| `finance`  | Finance       | markets, investing, macro, earnings, crypto, personal finance            |

## The three layers every domain produces

Whatever the domain, a run produces the same three-layer briefing. The chosen
domain guide explains what each layer *means* in that domain:

1. **Foundations — the unwavering facts.** Established, slow-moving knowledge:
   definitions, canonical works, settled facts and references. (Published as the
   *related/foundations* section.)
2. **Latest — what's new.** Recent, concrete developments grounded in real,
   freshly-opened sources. (Published as the *news/latest* section.)
3. **Takes — ideas & interpretations.** This is the *thinking* layer: generative,
   domain-appropriate ideas (and the theses behind them) that the foundations +
   latest make possible — a business idea, something to build, an investment or
   research thesis, a project to try — each with a way to test, try, or watch it.
   (Published as the *hypotheses/takes* section.)

## Language

Write the content in the run's chosen language: `en` (English) or `ja` (日本語).
When `OUTPUT_LANGUAGE` is set it decides; otherwise infer the most fitting
language from the topic and its likely audience.

## Editing

This file and the per-domain guides are plain Markdown — edit them freely to
retune sources, tone, or what counts as a good item. Add a new domain by adding
`config/domains/<key>.en.md` + `<key>.ja.md` and a row above (and the key to
`DOMAINS` in `scripts/select_domain.py`).
