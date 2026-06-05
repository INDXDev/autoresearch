#!/usr/bin/env python3
"""Pick the SITE's look — title, tagline, brand colours — once, stickily, no LLM here.

The published Astro + Starlight site (``site/``) needs a handful of presentation
choices: the site **title**, the hero **tagline**, and a **brand colour** (the
single voltage the theme paints every link / CTA / active state with). This
script is the DETERMINISTIC half of choosing them; the open-ended "read the
topic and design a fitting look" half is a tiny Claude Code Action step that
runs ONLY the first time a topic is seen (mirrors ``select_domain.py``).

It is sticky per TOPIC — the same key the domain picker uses — so the look is
generated once on the first run for a topic and REUSED thereafter; it only
changes when the topic changes. A user can always override any field with a repo
Variable (``SITE_TITLE``); the authority is **pin > AI design > default**.

Three subcommands:

* ``prepare``  — hash the effective topic, decide whether a fresh design is
  NEEDED (none remembered yet), and write ``.auto_state/site_brief.md`` for the
  picker. Emits ``need_pick`` / ``topic_hash``.
* ``finalize`` — merge the Claude design (or the reused values), validate +
  normalise colours, persist keyed by the topic hash, and emit the result.
* ``emit``     — BUILD TIME (the publish-site workflow): read the remembered
  design for this topic, resolve title/tagline against any Variable pin, write
  the CSS variable overrides to ``site/src/styles/theme.css``, and append
  ``SITE_TITLE`` / ``SITE_TAGLINE`` to ``$GITHUB_ENV`` for the Astro build.

State is one file — a map
``{ "<topic_hash>": {"site_title": ..., "tagline": ..., "brand_color": ...,
"link_color_dark": ..., "link_color_light": ..., "topic": ...} }`` — restored
from / saved to the unified ``auto-research-state`` orphan branch by the
workflow. Its path is ``SITE_STATE_FILE`` (the workflow sets it to
``site_config.json`` at the repo root; default ``.auto_state/site_config.json``).
This script only reads/writes that local file plus ``theme.css``; it never calls
git or an LLM, and ALWAYS exits 0 so any failure degrades to sensible defaults.

Inputs (environment):
    RESEARCH_TOPIC     the lab's topic string (falls back to config/research_topics.md)
    OUTPUT_LANGUAGE    en | ja — picks the default title and is passed to the designer
    RESEARCH_DOMAIN    the run's domain, for the designer's context (optional)
    SITE_TITLE         pin the site title (a repo Variable) — overrides the AI design
    SITE_TAGLINE       pin the hero tagline (optional)
    SECTION_JSON       finalize only: the picker's structured_output JSON
    SITE_STATE_FILE    override the state path (default .auto_state/site_config.json)
    SITE_DIR           emit only: the Astro site dir (default "site")
    GITHUB_OUTPUT      Actions step-output file; key=value lines are appended here
    GITHUB_ENV         emit only: Actions env file; SITE_TITLE/SITE_TAGLINE appended

Security: never prints tokens or secrets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

LANGS = ("en", "ja")
DEFAULT_LANG = "en"
# The theme's shipped defaults (Coinbase Blue) — used when nothing is designed
# or pinned, so emit always produces a valid, on-brand theme.css.
DEFAULT_BRAND = "#0052ff"
DEFAULT_TITLE = {"en": "Auto Research", "ja": "Auto Research"}

_HERE = os.path.dirname(__file__)
_TOPICS_FILE = os.path.join(_HERE, "..", "config", "research_topics.md")
_STATE_FILE = (
    os.environ.get("SITE_STATE_FILE", "").strip() or ".auto_state/site_config.json"
)
_BRIEF_FILE = os.path.join(".auto_state", "site_brief.md")


# --- topic + hashing (mirrors select_domain.py so the keys line up) ---------


def _topic_from_config() -> str:
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
    raw = (value or "").strip().lower()
    if raw.startswith("ja") or raw in {"jp", "japanese", "日本語"}:
        return "ja"
    return "en"


# --- colour helpers ---------------------------------------------------------

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def norm_hex(value: str | None) -> str:
    """Normalise a hex colour to ``#rrggbb`` lower-case, or '' if invalid."""
    raw = (value or "").strip()
    m = _HEX_RE.match(raw)
    if not m:
        return ""
    digits = m.group(1).lower()
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits}"


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in rgb)


def _mix(a: str, b: str, t: float) -> str:
    """Linear blend of two hex colours; t=0 -> a, t=1 -> b."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return _hex(
        (
            round(ra + (rb - ra) * t),
            round(ga + (gb - ga) * t),
            round(ba + (bb - ba) * t),
        )
    )


def derive_palette(brand: str, link_dark: str = "", link_light: str = "") -> dict:
    """Fill in a full theme palette from the single brand colour.

    Only ``brand`` is required from the designer. The hover/active shade and the
    per-theme link tints are derived (darken for active, lighten toward white for
    the dark-mode link) unless the designer supplied explicit link colours.
    """
    brand = norm_hex(brand) or DEFAULT_BRAND
    active = _mix(brand, "#000000", 0.22)        # ~22% darker for hover/active
    link_d = norm_hex(link_dark) or _mix(brand, "#ffffff", 0.42)   # lighter on dark
    link_l = norm_hex(link_light) or brand        # the brand itself on light
    accent_low_dark = _mix(brand, "#000000", 0.7)
    accent_high_dark = _mix(brand, "#ffffff", 0.6)
    accent_low_light = _mix(brand, "#ffffff", 0.82)
    accent_high_light = active
    return {
        "brand": brand,
        "active": active,
        "link_dark": link_d,
        "link_light": link_l,
        "accent_low_dark": accent_low_dark,
        "accent_high_dark": accent_high_dark,
        "accent_low_light": accent_low_light,
        "accent_high_light": accent_high_light,
    }


# --- state file -------------------------------------------------------------


def load_state() -> dict:
    try:
        with open(_STATE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict) -> None:
    parent = os.path.dirname(_STATE_FILE)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_outputs(**kwargs: object) -> None:
    path = os.environ.get("GITHUB_OUTPUT", "").strip()
    lines = [f"{key}={'' if value is None else value}" for key, value in kwargs.items()]
    for line in lines:
        print(line)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def write_env(**kwargs: object) -> None:
    """Append KEY=value lines to $GITHUB_ENV (multi-line safe via heredoc)."""
    path = os.environ.get("GITHUB_ENV", "").strip()
    if not path:
        for key, value in kwargs.items():
            print(f"(env) {key}={value}")
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in kwargs.items():
            handle.write(f"{key}<<__AR_EOF__\n{value}\n__AR_EOF__\n")


def remembered(state: dict, h: str) -> dict:
    value = state.get(h)
    return value if isinstance(value, dict) else {}


# --- prepare ----------------------------------------------------------------


def _write_brief(topic: str, lang: str, domain: str) -> None:
    """Write the designer's brief: the topic, language, domain, and instructions."""
    os.makedirs(os.path.dirname(_BRIEF_FILE), exist_ok=True)
    domain_line = f"**Domain (lens):** {domain}\n\n" if domain else ""
    with open(_BRIEF_FILE, "w", encoding="utf-8") as handle:
        handle.write(
            f"# Design this site's look\n\n"
            f"**Effective research topic:** {topic}\n\n"
            f"**Write the title/tagline in this language:** {lang} (en=English, ja=日本語)\n\n"
            f"{domain_line}"
            f"You are naming and styling a small documentation site that publishes "
            f"this lab's automated findings on the topic above. Choose:\n\n"
            f"- `site_title`: a short, memorable site name (2-4 words) fitting the "
            f"topic and language. Not a sentence.\n"
            f"- `tagline`: one short sentence (<= ~12 words) for the hero, in the "
            f"language above.\n"
            f"- `brand_color`: ONE brand colour as a `#rrggbb` hex — the single "
            f"voltage every link / button / active state is painted with. Pick a "
            f"confident, accessible colour that suits the topic's mood (avoid "
            f"near-white / near-black so it reads on both light and dark themes).\n\n"
            f"The hover shade and per-theme link tints are derived automatically, "
            f"so you only need the one `brand_color`.\n"
        )


def cmd_prepare() -> int:
    topic = effective_topic()
    lang = norm_lang(os.environ.get("OUTPUT_LANGUAGE"))
    domain = (os.environ.get("RESEARCH_DOMAIN", "") or "").strip().lower()
    h = topic_hash(topic)
    state = load_state()
    have = bool(remembered(state, h))
    _write_brief(topic, lang, domain)
    write_outputs(topic_hash=h, need_pick="false" if have else "true")
    status = "reusing remembered look" if have else "needs a fresh design"
    print(f"prepare: topic={topic!r} hash={h} lang={lang} ({status})")
    return 0


# --- finalize ---------------------------------------------------------------


def cmd_finalize() -> int:
    topic = effective_topic()
    lang = norm_lang(os.environ.get("OUTPUT_LANGUAGE"))
    h = topic_hash(topic)
    state = load_state()
    current = remembered(state, h)

    pick: dict = {}
    raw = os.environ.get("SECTION_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                pick = parsed
        except json.JSONDecodeError:
            print("finalize: SECTION_JSON was not valid JSON; ignoring the design.")

    # Authority for each field: existing remembered > fresh pick. (A repo
    # Variable pin is applied later, at emit time, so changing the pin takes
    # effect without re-running the picker.)
    def choose(field: str) -> str:
        return (current.get(field) or pick.get(field) or "").strip()

    title = choose("site_title")
    tagline = choose("tagline")
    brand = norm_hex(choose("brand_color"))
    link_dark = norm_hex(current.get("link_color_dark") or pick.get("link_color_dark"))
    link_light = norm_hex(current.get("link_color_light") or pick.get("link_color_light"))

    # A design is "real" if the picker (or memory) gave us at least a title or a
    # colour. A bare/empty run is NOT persisted, so prepare keeps asking until a
    # credentialed run actually designs the look.
    real = bool(title or brand or tagline)
    if real:
        entry = {
            "site_title": title,
            "tagline": tagline,
            "brand_color": brand or DEFAULT_BRAND,
            "link_color_dark": link_dark,
            "link_color_light": link_light,
            "topic": topic,
        }
        state[h] = entry
        save_state(state)
    write_outputs(topic_hash=h, site_title=title, brand_color=brand or DEFAULT_BRAND)
    note = "saved" if real else "nothing designed (not persisted — awaiting a real pick)"
    print(f"finalize: topic={topic!r} hash={h} title={title or '?'} brand={brand or '?'} ({note})")
    return 0


# --- emit (build time) ------------------------------------------------------


def _theme_css(palette: dict) -> str:
    """The CSS that overrides the theme's tokens with the chosen brand palette.

    Loaded AFTER custom.css, so these win. Only colour tokens are touched; the
    geometry/typography in custom.css is untouched.
    """
    p = palette
    return f"""/* Auto Research — AI-designed site theme (generated by scripts/site_config.py).
   Overrides the brand voltage in custom.css. Do not edit by hand: this file is
   regenerated from site_config.json (the auto-research-state branch) at build. */

:root {{
  --ar-blue: {p['brand']};
  --ar-blue-active: {p['active']};
}}

:root,
:root[data-theme='dark'] {{
  --ar-blue-link: {p['link_dark']};
  --sl-color-accent: {p['brand']};
  --sl-color-accent-low: {p['accent_low_dark']};
  --sl-color-accent-high: {p['accent_high_dark']};
  --sl-color-text-accent: {p['link_dark']};
}}

:root[data-theme='light'] {{
  --ar-blue-link: {p['link_light']};
  --sl-color-accent: {p['brand']};
  --sl-color-accent-low: {p['accent_low_light']};
  --sl-color-accent-high: {p['accent_high_light']};
  --sl-color-text-accent: {p['link_light']};
}}

/* The signature hero gradient, retuned to the brand colour. */
.hero {{
  background:
    radial-gradient(60rem 30rem at 88% -20%,
      color-mix(in srgb, {p['brand']} 30%, transparent), transparent 60%),
    linear-gradient(180deg, #16181c 0%, #0a0b0d 100%);
}}
.hero .actions a[data-variant='primary'] {{
  box-shadow: 0 12px 30px -12px color-mix(in srgb, {p['brand']} 70%, transparent);
}}
"""


def cmd_emit() -> int:
    topic = effective_topic()
    lang = norm_lang(os.environ.get("OUTPUT_LANGUAGE"))
    h = topic_hash(topic)
    state = load_state()
    design = remembered(state, h)

    # Resolve title/tagline: Variable pin > AI design > default.
    pin_title = os.environ.get("SITE_TITLE", "").strip()
    pin_tagline = os.environ.get("SITE_TAGLINE", "").strip()
    title = pin_title or (design.get("site_title") or "").strip() or DEFAULT_TITLE[lang]
    tagline = (
        pin_tagline
        or (design.get("tagline") or "").strip()
        or topic
    )

    palette = derive_palette(
        design.get("brand_color") or DEFAULT_BRAND,
        design.get("link_color_dark") or "",
        design.get("link_color_light") or "",
    )

    site_dir = os.environ.get("SITE_DIR", "").strip() or (
        sys.argv[2] if len(sys.argv) > 2 else "site"
    )
    theme_path = os.path.join(site_dir, "src", "styles", "theme.css")
    os.makedirs(os.path.dirname(theme_path), exist_ok=True)
    with open(theme_path, "w", encoding="utf-8") as handle:
        handle.write(_theme_css(palette))

    write_env(SITE_TITLE=title, SITE_TAGLINE=tagline)
    src = "pinned" if pin_title else ("AI-designed" if design else "default")
    print(
        f"emit: topic={topic!r} hash={h} title={title!r} ({src}) "
        f"brand={palette['brand']} -> {theme_path}"
    )
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        return cmd_prepare()
    if cmd == "finalize":
        return cmd_finalize()
    if cmd == "emit":
        return cmd_emit()
    print("Usage: site_config.py <prepare|finalize|emit>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
