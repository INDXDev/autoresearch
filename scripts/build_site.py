#!/usr/bin/env python3
"""Export the Auto Research Issues into content for the Astro + Starlight site.

This is the AGGREGATION half of the project. The per-section workflow files one
GitHub Issue per item (news / hypothesis / paper / site-watch). This script reads
ALL of those Issues back from the GitHub API — the single source of truth —
together with each Issue's **labels (tags)**, **reactions**, and **comments**,
and renders them into Markdown pages that the Starlight site (under ``site/``)
turns into a rich documentation website:

    GitHub Issues + labels + reactions + comments
        -> Markdown content files -> (Astro/Starlight build) -> static site

Layout written under ``site/src/content/docs/``:

* ``index.md``            — splash landing page: hero + stat cards + browse-by-
                            section cards + run list + browse-by-reaction strip.
* ``runs/<date>.md``      — one page per run (one daily/manual execution), items
                            grouped by section (📰 / 💡 / 📚 / 👀) as compact cards.
* ``items/<number>.md``   — one page per item: the FULL body, topical **tags**,
                            **reaction** chips, and **comments**. Every card on the
                            site links here (navigation stays on-site); the source
                            GitHub Issue is only a small secondary button.
* ``sections/<key>.md``   — one page per layer (Latest / Takes / Foundations /
                            Site Watch), every item in it across all runs.
* ``reactions/<slug>.md`` — one page per reaction the lab used (👍 ❤️ 🎉 …),
                            listing every item that received it.
* ``tags/<slug>.md``      — one page per topical tag, listing every item carrying
                            it (the tags come from the auto-label workflow).

A small ``site/src/data/meta.json`` carries build metadata.

A "run" is keyed by the publication date stamped in each Issue body (the ``Date``
header the publisher writes), falling back to the Issue's creation date.

This script never calls an LLM and has NO third-party dependencies — it uses only
the Python standard library and the read helpers in ``github_issue``. It always
exits 0: if the token/repo are missing or the API returns nothing, it still emits
a valid (empty-state) site so the deploy succeeds.

Usage:
    python3 scripts/build_site.py [site_dir]        # default site dir: site

Inputs (environment):
    GITHUB_TOKEN          provided automatically by Actions (read access)
    GITHUB_REPOSITORY     'owner/name' (auto-set inside Actions); used for links
    OUTPUT_LANGUAGE       en | ja  (site scaffolding language; default en)
    RESEARCH_TOPIC        topic string shown in the hero (falls back to config)
    SITE_MAX_ISSUES       max Issues to pull per section label (default 300)
    SITE_FETCH_COMMENTS   pull each Issue's comments too? default true
    SITE_BUILT_AT         optional timestamp for the footer/meta (else blank)

Security: never prints tokens or any secret.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys

import i18n
from github_issue import list_comments, list_issues

# section key -> (label tag publish_section.py stamps, i18n name key, emoji,
# accent, sidebar order). The accent is used only as a small category indicator
# (left rail / dot / kicker) — the dominant brand color stays Coinbase Blue.
SECTIONS: list[dict[str, object]] = [
    {"key": "news", "tag": "research-news", "name_key": "section_news", "emoji": "📰", "accent": "#2563eb", "order": 1},
    {"key": "hypotheses", "tag": "hypothesis", "name_key": "section_hypotheses", "emoji": "💡", "accent": "#d97706", "order": 2},
    {"key": "related", "tag": "related-work", "name_key": "section_related", "emoji": "📚", "accent": "#7c3aed", "order": 3},
    {"key": "watch", "tag": "site-watch", "name_key": "section_watch", "emoji": "👀", "accent": "#059669", "order": 4},
]

# Pipeline/feedback labels that are NOT shown as topical tags on the site.
# (The topical tags themselves are added by the auto-label workflow.) The
# per-run `domain:<domain>` label is also a pipeline label — excluded by the
# `domain:` prefix check in the tag filter below, like the `watch:` slugs.
_PIPELINE_LABELS = {
    "auto-research", "research-news", "hypothesis", "related-work",
    "site-watch", "good", "bad",
}

# The reaction summary keys GitHub returns, mapped to (display emoji, URL slug,
# i18n display-name key). Drives both the inline chips and the per-reaction pages.
_REACTION_META: list[tuple[str, str, str, str]] = [
    ("+1", "👍", "liked", "react_plus1"),
    ("heart", "❤️", "loved", "react_heart"),
    ("hooray", "🎉", "celebrated", "react_hooray"),
    ("rocket", "🚀", "rocket", "react_rocket"),
    ("laugh", "😄", "funny", "react_laugh"),
    ("eyes", "👀", "watching", "react_eyes"),
    ("confused", "😕", "confused", "react_confused"),
    ("-1", "👎", "disliked", "react_minus1"),
]
# Back-compat view used by the chip renderer: (key, emoji) in display order.
_REACTION_EMOJI: list[tuple[str, str]] = [(k, e) for k, e, _, _ in _REACTION_META]

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_URL = re.compile(r"https?://[^\s<>()\]]+")

# The publisher's metadata header labels (Topic / Date / Source / Link / Theme),
# in EVERY supported language — not just the one build_site happens to run with.
# Issues are written with the labels of the run's OUTPUT_LANGUAGE; if the site is
# built under a different language those lines would otherwise be unrecognised and
# leak into the card excerpt (e.g. the research topic showing on every card).
_META_LABEL_KEYS = ("topic_label", "pub_date", "pub_source", "pub_link", "pub_theme")
_META_LABELS: set[str] = {
    variant
    for key in _META_LABEL_KEYS
    for variant in i18n._STRINGS.get(key, {}).values()
}


# --- small helpers ----------------------------------------------------------


def topic_from_config() -> str:
    """Fallback topic from config/research_topics.md (first few bullets)."""
    path = os.path.join(os.path.dirname(__file__), "..", "config", "research_topics.md")
    try:
        with open(path, encoding="utf-8") as handle:
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


def _section_names() -> set[str]:
    """Localised + English section display names, for stripping issue prefixes."""
    names: set[str] = set()
    for section in SECTIONS:
        names.add(i18n.t(section["name_key"]))
    return names


def _clean_title(raw: str, section_name: str) -> str:
    """Drop the leading ``<Section>: `` prefix the publisher adds to a title."""
    title = (raw or "").strip()
    for name in {section_name, *_section_names()}:
        prefix = f"{name}: "
        if title.startswith(prefix):
            return title[len(prefix):].strip()
    return title


def _run_date(issue: dict) -> str:
    """The run date for an Issue: the ISO date in its body, else its created day."""
    match = _ISO_DATE.search(str(issue.get("body", "")))
    if match:
        return match.group(0)
    created = str(issue.get("created_at", ""))
    found = _ISO_DATE.search(created)
    return found.group(0) if found else "undated"


def _topical_tags(issue: dict) -> list[str]:
    """The Issue's topical labels (everything bar the pipeline/feedback labels)."""
    out: list[str] = []
    for label in issue.get("labels") or []:
        name = (label.get("name") if isinstance(label, dict) else str(label)) or ""
        name = name.strip()
        if (
            not name
            or name in _PIPELINE_LABELS
            or name.startswith("watch:")
            or name.startswith("domain:")
        ):
            continue
        if name not in out:
            out.append(name)
    return out


def _reaction_count(reactions: object, key: str) -> int:
    """Safely read one reaction's count off a GitHub reactions summary object."""
    if not isinstance(reactions, dict):
        return 0
    try:
        return int(reactions.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _reaction_chip_html(reactions: object) -> str:
    """The reaction ``<span>`` chips only, no wrapper (empty string when none)."""
    chips: list[str] = []
    for key, emoji in _REACTION_EMOJI:
        count = _reaction_count(reactions, key)
        if count > 0:
            chips.append(f'<span class="ar-chip">{emoji} {count}</span>')
    return "".join(chips)


def _reaction_chips(reactions: object) -> str:
    """Render a reactions summary into a wrapped chip row (empty when none)."""
    chips = _reaction_chip_html(reactions)
    return f'<div class="ar-reactions">{chips}</div>' if chips else ""


def _excerpt(body: str, limit: int = 200) -> str:
    """A short plain-text preview from a (self-authored) Issue body.

    Skips the publisher's metadata header lines (Topic / Date / Source / Link /
    Theme), headings, rules, and the italic footer, then gathers the first run of
    prose — for a bullet like ``- **Rationale:** …`` it keeps the value after the
    label. Returns plain text (no Markdown markup), truncated on a word boundary.
    """
    meta_labels = _META_LABELS
    collected: list[str] = []
    total = 0
    for raw in (body or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            if collected:
                break  # stop at the first blank line after some prose
            continue
        if line.startswith("#") or (set(line) <= {"-"} and len(line) >= 3):
            continue
        if re.match(r"^_.*_$", line):  # the italic footer line
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        label = re.match(r"^\*\*([^*]+?):\*\*\s*(.*)$", line)
        if label:
            if label.group(1).strip() in meta_labels:
                continue  # pure metadata — skip the whole line
            line = label.group(2).strip()
            if not line:
                continue
        # Flatten any remaining inline Markdown to plain text.
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", line)
        collected.append(line)
        total += len(line)
        if total >= limit:
            break
    text = " ".join(collected).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip() + "…"
    return text


def tag_slug(tag: str) -> str:
    """A stable, URL-safe slug for a tag. Falls back to a hash for non-ASCII."""
    slug = re.sub(r"[^0-9a-z]+", "-", tag.lower()).strip("-")
    if not slug:
        slug = "tag-" + hashlib.md5(tag.encode("utf-8")).hexdigest()[:8]
    return slug


# --- minimal, safe Markdown -> HTML (for our own generated Issue bodies) -----


def _inline(text: str, links: bool = True) -> str:
    """Render inline Markdown to safe HTML: escape first, then bold/italic/links.

    Operates on already-escaped text so any user/source content is inert; only
    the tags this function emits are real HTML. With ``links=False`` no anchors
    are produced — used where the result is itself placed inside an ``<a>`` (a
    card title), so an injected ``[x](url)`` can't open a nested off-site anchor.
    """
    out = html.escape(text, quote=False)
    if links:
        # [label](url) -> anchor (url is escaped; only http(s) is linkified).
        def _md_link(match: re.Match) -> str:
            label, url = match.group(1), match.group(2)
            if not url.startswith(("http://", "https://")):
                return match.group(0)
            return f'<a href="{html.escape(url, quote=True)}" rel="noopener nofollow">{label}</a>'

        out = re.sub(r"\[([^\]]+)\]\((https?://[^)]+|[^)]+)\)", _md_link, out)
        # Autolink bare URLs that are not already inside an anchor's href/text.
        def _auto(match: re.Match) -> str:
            url = match.group(0)
            return f'<a href="{html.escape(url, quote=True)}" rel="noopener nofollow">{url}</a>'

        out = re.sub(r"(?<![\"=>])" + _URL.pattern, _auto, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", out)
    return out


def _markdown(body: str) -> str:
    """Render a (small, self-authored) Markdown body to an HTML fragment.

    The output is a single contiguous HTML block (no blank lines), so it can be
    embedded inside a Markdown page without the Markdown parser re-opening.
    """
    lines = (body or "").replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    buf: list[str] = []  # pending paragraph lines
    items: list[str] = []  # pending <li> contents

    def flush_para() -> None:
        if buf:
            blocks.append("<p>" + "<br>".join(_inline(b) for b in buf) + "</p>")
            buf.clear()

    def flush_list() -> None:
        if items:
            blocks.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_para()
            flush_list()
            continue
        if set(stripped) <= {"-"} and len(stripped) >= 3:  # horizontal rule
            flush_para()
            flush_list()
            blocks.append("<hr>")
            continue
        if stripped.startswith("#"):
            flush_para()
            flush_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            text = stripped.lstrip("#").strip()
            blocks.append(f"<h{level}>{_inline(text)}</h{level}>")
            continue
        if stripped.startswith("- "):
            flush_para()
            items.append(stripped[2:].strip())
            continue
        flush_list()
        buf.append(stripped)

    flush_para()
    flush_list()
    # No blank lines between blocks: keep the whole fragment one HTML block.
    return "".join(blocks)


# --- model ------------------------------------------------------------------


def collect_issues(limit: int, fetch_comments: bool) -> list[dict]:
    """Fetch every section's Issues and merge them, de-duplicated by number.

    Stamps each issue with ``_section`` and, when ``fetch_comments`` is on, its
    ``_comments`` list (one extra API call per Issue).
    """
    by_number: dict[int, dict] = {}
    order: list[int] = []
    for section in SECTIONS:
        for issue in list_issues(section["tag"], state="all", limit=limit):
            number = issue.get("number")
            if number is None or number in by_number:
                continue
            issue["_section"] = section
            by_number[number] = issue
            order.append(number)
    issues = [by_number[n] for n in order]
    if fetch_comments:
        for issue in issues:
            count = issue.get("comments")
            # Skip the API call when GitHub already tells us there are 0 comments.
            if isinstance(count, int) and count == 0:
                issue["_comments"] = []
            else:
                issue["_comments"] = list_comments(int(issue["number"]))
    return issues


def group_by_run(issues: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group issues by run date, newest run first, items newest-Issue first."""
    runs: dict[str, list[dict]] = {}
    for issue in issues:
        runs.setdefault(_run_date(issue), []).append(issue)
    for items in runs.values():
        items.sort(key=lambda i: i.get("number", 0), reverse=True)
    return sorted(runs.items(), key=lambda kv: kv[0], reverse=True)


# --- Markdown content rendering ---------------------------------------------


def _yaml_str(value: str) -> str:
    """Quote a string for a YAML frontmatter scalar."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _run_basename(date: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]", "-", date)


def _item_basename(issue: dict) -> str:
    """URL-safe basename for an item's own detail page (its Issue number)."""
    return re.sub(r"[^0-9A-Za-z_-]", "-", str(issue.get("number", "")))


def _clean_issue_title(issue: dict) -> str:
    """The Issue title with the publisher's ``<Section>: `` prefix removed."""
    section = issue["_section"]
    return _clean_title(str(issue.get("title", "")), i18n.t(section["name_key"]))


def _github_button(url: str, label: str, *, large: bool = False) -> str:
    """A small secondary pill linking out to the source Issue on GitHub."""
    if not url:
        return ""
    cls = "ar-ghbtn ar-ghbtn-lg" if large else "ar-ghbtn"
    return (
        f'<a class="{cls}" href="{html.escape(url, quote=True)}" rel="noopener">'
        f'{html.escape(label)}</a>'
    )


def _sidebar_order(date: str) -> int:
    """Newest run first in the autogenerated sidebar (smaller order = higher)."""
    digits = re.sub(r"\D", "", date)
    return -int(digits) if digits else 0


def _comment_block(comment: dict) -> str:
    """One rendered comment card (author · date · body · its reactions)."""
    user = comment.get("user")
    login = (user.get("login") if isinstance(user, dict) else "") or "someone"
    when = str(comment.get("created_at", ""))[:10]
    url = str(comment.get("html_url", "")).strip()
    who = html.escape(login)
    if url:
        who = f'<a href="{html.escape(url, quote=True)}" rel="noopener">@{who}</a>'
    else:
        who = f"@{who}"
    head = f'<div class="ar-comment-head">{who}<span class="ar-comment-date">{html.escape(when)}</span></div>'
    body = f'<div class="ar-comment-body">{_markdown(str(comment.get("body", "")))}</div>'
    reactions = _reaction_chips(comment.get("reactions"))
    return f'<div class="ar-comment">{head}{body}{reactions}</div>'


def _card(issue: dict, date: str | None = None, prefix: str = "../../") -> str:
    """A compact listing card: kicker, title (→ the item's OWN page), excerpt,
    tags, then a foot row of reaction chips + a small GitHub button.

    Used on every listing page (runs / sections / tags / reactions), each of
    which lives two levels deep, so internal links default to ``../../<area>/…``.
    The root ``index.md`` passes ``prefix=""`` for root-relative links. When
    ``date`` is given (cross-run listings) it shows as a kicker link to the run.
    """
    section = issue["_section"]
    # No links inside the title — it's wrapped in the card's own <a>.
    title_html = _inline(_clean_issue_title(issue), links=False)
    href = f"{prefix}items/{_item_basename(issue)}/"

    parts = [f'<article class="ar-card" style="--ar-accent:{section["accent"]}">']
    kicker = f'{section["emoji"]} {html.escape(i18n.t(section["name_key"]))}'
    if date:
        kicker += (
            f' <span class="ar-kdot">·</span> '
            f'<a class="ar-kicker-date" href="{prefix}runs/{_run_basename(date)}/">'
            f'{html.escape(date)}</a>'
        )
    parts.append(f'<span class="ar-kicker">{kicker}</span>')
    parts.append(f'<h3 class="ar-card-title"><a href="{href}">{title_html}</a></h3>')

    excerpt = _excerpt(str(issue.get("body", "")))
    if excerpt:
        parts.append(f'<p class="ar-excerpt">{_inline(excerpt)}</p>')

    tags = _topical_tags(issue)
    if tags:
        chips = "".join(
            f'<a class="ar-tag" href="{prefix}tags/{tag_slug(tag)}/">#{html.escape(tag)}</a>'
            for tag in tags
        )
        parts.append(f'<div class="ar-tags">{chips}</div>')

    foot: list[str] = []
    chips = _reaction_chip_html(issue.get("reactions"))
    if chips:
        foot.append(f'<span class="ar-card-reacts">{chips}</span>')
    comments = issue.get("_comments") or []
    if comments:
        foot.append(f'<span class="ar-card-comments">💬 {len(comments)}</span>')
    button = _github_button(str(issue.get("html_url", "")).strip(), "GitHub")
    if button:
        foot.append(button)
    if foot:
        parts.append(f'<div class="ar-card-foot">{"".join(foot)}</div>')

    parts.append("</article>")
    return "".join(parts)


def render_item_page(issue: dict, date: str) -> str:
    """One item's own page: the full body, tags, reactions, comments, and a small
    GitHub button + back-to-run link in the footer. This is what the cards link to
    (so navigation stays on-site; GitHub is only the small secondary button)."""
    section = issue["_section"]
    title = _clean_issue_title(issue)
    excerpt = _excerpt(str(issue.get("body", "")), limit=150)
    front = [
        "---",
        f"title: {_yaml_str(title)}",
        f"description: {_yaml_str(excerpt or i18n.t(section['name_key']))}",
        "tableOfContents: false",
        "---",
        "",
    ]

    kicker = (
        f'<span class="ar-kicker">{section["emoji"]} '
        f'<a class="ar-kicker-link" href="../../sections/{section["key"]}/">'
        f'{html.escape(i18n.t(section["name_key"]))}</a>'
    )
    if date:
        kicker += (
            f' <span class="ar-kdot">·</span> '
            f'<a class="ar-kicker-date" href="../../runs/{_run_basename(date)}/">'
            f'{html.escape(date)}</a>'
        )
    kicker += "</span>"

    body: list[str] = [f'<div class="ar-detail" style="--ar-accent:{section["accent"]}">', kicker]
    body.append(f'<div class="ar-body ar-body-lg">{_markdown(str(issue.get("body", "")))}</div>')

    tags = _topical_tags(issue)
    if tags:
        chips = "".join(
            f'<a class="ar-tag" href="../../tags/{tag_slug(tag)}/">#{html.escape(tag)}</a>'
            for tag in tags
        )
        body.append(f'<div class="ar-tags">{chips}</div>')

    reactions = _reaction_chips(issue.get("reactions"))
    if reactions:
        body.append(reactions)

    comments = issue.get("_comments") or []
    if comments:
        heading = i18n.t("site_comments_heading")
        count = i18n.t("site_comments", count=len(comments))
        blocks = "".join(_comment_block(c) for c in comments)
        body.append(
            f'<div class="ar-comments-open">'
            f'<h2 class="ar-comments-head">💬 {html.escape(heading)} '
            f'<span class="ar-count">· {len(comments)}</span></h2>'
            f'<span class="sr-only">{html.escape(count)}</span>{blocks}</div>'
        )

    foot: list[str] = []
    button = _github_button(str(issue.get("html_url", "")).strip(),
                            i18n.t("site_view_on_github"), large=True)
    if button:
        foot.append(button)
    if date:
        foot.append(
            f'<a class="ar-backlink" href="../../runs/{_run_basename(date)}/">'
            f'{html.escape(i18n.t("site_back_run", date=date))}</a>'
        )
    if foot:
        body.append(f'<div class="ar-detail-foot">{"".join(foot)}</div>')

    body.append("</div>")
    return "\n".join(front) + "\n".join(body) + "\n"


def render_run_page(date: str, items: list[dict]) -> str:
    """A run page: frontmatter + items grouped by section, as compact cards."""
    heading = f"{i18n.t('site_run_heading')} · {date}"
    counts = sum(1 for _ in items)
    front = [
        "---",
        f"title: {_yaml_str(heading)}",
        f"description: {_yaml_str(i18n.t('site_run_desc', count=counts, date=date))}",
        f"sidebar:\n  order: {_sidebar_order(date)}",
        "---",
        "",
    ]
    body: list[str] = []
    for section in SECTIONS:
        group = [i for i in items if i["_section"]["key"] == section["key"]]
        if not group:
            continue
        name = i18n.t(section["name_key"])
        body.append(f'<h2 class="ar-sec-head" style="--ar-accent:{section["accent"]}">'
                    f'{section["emoji"]} {html.escape(name)} '
                    f'<span class="ar-count">· {len(group)}</span></h2>')
        body.append('<div class="ar-grid">')
        for issue in group:
            body.append(_card(issue))
        body.append("</div>")
    return "\n".join(front) + "\n".join(body) + "\n"


def render_section_page(section: dict, entries: list[tuple[str, dict]]) -> str:
    """A section page: every item in one layer (Latest / Takes / …), newest first."""
    name = i18n.t(section["name_key"])
    label = f'{section["emoji"]} {name}'
    front = [
        "---",
        f"title: {_yaml_str(label)}",
        f"description: {_yaml_str(i18n.t('site_section_desc', name=name, count=len(entries)))}",
        f"sidebar:\n  order: {section['order']}",
        "---",
        "",
    ]
    body = ['<div class="ar-grid">']
    for date, issue in entries:
        body.append(_card(issue, date=date))
    body.append("</div>")
    return "\n".join(front) + "\n".join(body) + "\n"


def render_reaction_page(meta: tuple[str, str, str, str],
                         entries: list[tuple[str, dict]]) -> str:
    """A reaction page: every item the lab reacted to with one emoji, newest first."""
    _key, emoji, _slug, name_key = meta
    name = i18n.t(name_key)
    front = [
        "---",
        f"title: {_yaml_str(f'{emoji} {name}')}",
        f"description: {_yaml_str(i18n.t('site_reaction_desc', emoji=emoji, name=name, count=len(entries)))}",
        "---",
        "",
    ]
    body = ['<div class="ar-grid">']
    for date, issue in entries:
        body.append(_card(issue, date=date))
    body.append("</div>")
    return "\n".join(front) + "\n".join(body) + "\n"


def render_tag_page(tag: str, entries: list[tuple[str, dict]]) -> str:
    """A tag page: every item carrying this tag, newest run first."""
    front = [
        "---",
        f"title: {_yaml_str('#' + tag)}",
        f"description: {_yaml_str(i18n.t('site_tag_desc', tag=tag, count=len(entries)))}",
        "---",
        "",
    ]
    body = ['<div class="ar-grid">']
    for date, issue in entries:
        body.append(_card(issue, date=date))
    body.append("</div>")
    return "\n".join(front) + "\n".join(body) + "\n"


def render_index(runs: list[tuple[str, list[dict]]], topic: str, repo: str) -> str:
    """The landing page: hero + a small stat strip, then EVERY item rendered as a
    card grouped by section (newest first) — the whole feed, right on the front
    page. No "browse by section" cards or per-run drill-in: the articles are here.
    """
    total_items = sum(len(items) for _, items in runs)
    # The AI-designed look (scripts/site_config.py emit) exports SITE_TITLE /
    # SITE_TAGLINE; fall back to the i18n default / the topic when unset.
    title = os.environ.get("SITE_TITLE", "").strip() or i18n.t("site_title")
    tagline = (
        os.environ.get("SITE_TAGLINE", "").strip()
        or topic
        or i18n.t("site_tagline")
    )
    front = [
        "---",
        f"title: {_yaml_str(title)}",
        f"description: {_yaml_str(tagline)}",
        "template: splash",
        "hero:",
        f"  tagline: {_yaml_str(tagline)}",
    ]
    if runs and repo:
        front += [
            "  actions:",
            f"    - text: {_yaml_str(i18n.t('site_view_on_github'))}",
            f"      link: https://github.com/{repo}/issues",
            "      icon: external",
            "      variant: minimal",
        ]
    front += ["---", ""]

    body: list[str] = []

    # Overview stat strip: two top-line numbers.
    body.append('<div class="ar-stats">')
    for num, label in [(len(runs), i18n.t("site_runs")), (total_items, i18n.t("site_items"))]:
        body.append(
            f'<div class="ar-stat"><span class="ar-stat-num">{num}</span>'
            f'<span class="ar-stat-label">{html.escape(label)}</span></div>'
        )
    body.append("</div>")

    if not runs:
        body.append(f'<p class="ar-empty">{html.escape(i18n.t("site_no_runs"))}</p>')
        return "\n".join(front) + "\n".join(body) + "\n"

    # Every item, grouped by section (newest run first), rendered as cards right
    # here — the front page IS the feed. Cards use root-relative links (prefix="").
    section_entries: dict[str, list[tuple[str, dict]]] = {s["key"]: [] for s in SECTIONS}
    for date, items in runs:
        for issue in items:
            section_entries[issue["_section"]["key"]].append((date, issue))

    for section in SECTIONS:
        entries = section_entries[section["key"]]
        if not entries:
            continue
        name = i18n.t(section["name_key"])
        body.append(
            f'<h2 class="ar-sec-head" style="--ar-accent:{section["accent"]}">'
            f'{section["emoji"]} {html.escape(name)} '
            f'<span class="ar-count">· {len(entries)}</span></h2>'
        )
        body.append('<div class="ar-grid">')
        for date, issue in entries:
            body.append(_card(issue, date=date, prefix=""))
        body.append("</div>")

    return "\n".join(front) + "\n".join(body) + "\n"


# --- entrypoint -------------------------------------------------------------


def _truthy(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "on"}


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main() -> int:
    site_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SITE_DIR", "site")
    docs_dir = os.path.join(site_dir, "src", "content", "docs")
    data_dir = os.path.join(site_dir, "src", "data")

    topic = os.environ.get("RESEARCH_TOPIC", "").strip() or topic_from_config() or "AI"
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    try:
        limit = int(os.environ.get("SITE_MAX_ISSUES", "300"))
    except ValueError:
        limit = 300
    fetch_comments = _truthy("SITE_FETCH_COMMENTS", True)

    issues = collect_issues(limit, fetch_comments)
    runs = group_by_run(issues)

    # index
    _write(os.path.join(docs_dir, "index.md"), render_index(runs, topic, repo))

    # one page per run; one detail page per item; collect section + reaction groups
    section_entries: dict[str, list[tuple[str, dict]]] = {s["key"]: [] for s in SECTIONS}
    reaction_entries: dict[str, list[tuple[str, dict]]] = {k: [] for k, _, _, _ in _REACTION_META}
    for date, items in runs:
        _write(os.path.join(docs_dir, "runs", f"{_run_basename(date)}.md"),
               render_run_page(date, items))
        for issue in items:
            _write(os.path.join(docs_dir, "items", f"{_item_basename(issue)}.md"),
                   render_item_page(issue, date))
            section_entries[issue["_section"]["key"]].append((date, issue))
            reactions = issue.get("reactions")
            for key, _, _, _ in _REACTION_META:
                if _reaction_count(reactions, key) > 0:
                    reaction_entries[key].append((date, issue))

    # one page per section (Latest / Takes / Foundations / Site Watch)
    section_pages = 0
    for section in SECTIONS:
        entries = section_entries[section["key"]]
        if not entries:
            continue
        _write(os.path.join(docs_dir, "sections", f"{section['key']}.md"),
               render_section_page(section, entries))
        section_pages += 1

    # one page per reaction the lab actually used
    reaction_pages = 0
    for meta_tuple in _REACTION_META:
        entries = reaction_entries[meta_tuple[0]]
        if not entries:
            continue
        _write(os.path.join(docs_dir, "reactions", f"{meta_tuple[2]}.md"),
               render_reaction_page(meta_tuple, entries))
        reaction_pages += 1

    # one page per topical tag (collect across runs, newest run first)
    tag_entries: dict[str, list[tuple[str, dict]]] = {}
    for date, items in runs:
        for issue in items:
            for tag in _topical_tags(issue):
                tag_entries.setdefault(tag, []).append((date, issue))
    for tag, entries in sorted(tag_entries.items(), key=lambda kv: kv[0].lower()):
        _write(os.path.join(docs_dir, "tags", f"{tag_slug(tag)}.md"),
               render_tag_page(tag, entries))

    # build metadata (optional consumer: the site footer / debugging)
    meta = {
        "topic": topic,
        "repo": repo,
        "runs": len(runs),
        "items": sum(len(items) for _, items in runs),
        "tags": len(tag_entries),
        "built_at": os.environ.get("SITE_BUILT_AT", "").strip(),
    }
    _write(os.path.join(data_dir, "meta.json"), json.dumps(meta, ensure_ascii=False, indent=2) + "\n")

    print(
        f"Exported Starlight content to '{docs_dir}/': index + {len(runs)} run page(s) "
        f"+ {sum(len(v) for v in section_entries.values())} item page(s) "
        f"+ {section_pages} section page(s) + {reaction_pages} reaction page(s) "
        f"+ {len(tag_entries)} tag page(s) from {len(issues)} Issue(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
