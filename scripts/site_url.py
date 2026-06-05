"""Resolve links into the published GitHub Pages documentation site.

The Slack / email publishers use this to embed a link to each item's own page on
the site that ``publish-site.yml`` builds from the Issues — right beside the
Issue link itself.

The site's public URL is read **once** from the GitHub Pages REST API
(``GET /repos/{owner}/{repo}/pages`` → ``html_url``). That URL already carries
the correct base path for however Pages is served — ``/<repo>/`` for public
project Pages, ``/`` for user/root Pages or a custom domain — so we never have to
guess it from ``SITE_BASE`` / ``SITE_URL``. The call needs the workflow token to
carry ``pages: read`` (granted in ``auto-research.yml``).

Everything degrades to ``None`` when Pages is not enabled, the token lacks the
scope, or the API is unreachable — so the publishers simply omit the site link
and keep working. Dependency-free (urllib) to match the rest of the pipeline.

An explicit ``SITE_PAGES_URL`` env var short-circuits the API (handy for local
runs and tests, e.g. ``SITE_PAGES_URL=https://acme.github.io/lab/``).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_API = "https://api.github.com"

# Memoise the (possibly slow or failing) Pages lookup for the process lifetime.
# Sentinel distinguishes "not looked up yet" from "looked up, came back None".
_UNSET = object()
_cache: object = _UNSET


def _repo() -> str | None:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    return repo if "/" in repo else None


def _token() -> str | None:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _fetch_base() -> tuple[str | None, bool]:
    """Query the Pages API. Returns ``(base_url_or_None, cacheable)``.

    ``cacheable`` is True for a DEFINITIVE answer — a real URL, or a 403/404
    meaning Pages is genuinely not enabled / the token lacks ``pages: read``. It
    is False for a TRANSIENT failure (network error, timeout, 429/5xx), so the
    caller retries on the next item instead of poisoning the whole run's links
    off one flaky request.
    """
    repo = _repo()
    if not repo:
        return None, True  # no repo → definitively no site link
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "auto-research",
    }
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(f"{_API}/repos/{repo}/pages", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 404 = Pages not enabled yet; 403 = token missing `pages: read`. Both
        # are permanent for this run. Other codes (429 rate limit, 5xx) are
        # transient — don't cache, so a later item can succeed.
        permanent = exc.code in (403, 404)
        print(f"GitHub Pages URL unavailable (HTTP {exc.code}). Omitting site link.")
        return None, permanent
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        print(f"GitHub Pages URL lookup failed ({type(exc).__name__}). Omitting site link.")
        return None, False

    html_url = str(data.get("html_url", "")).strip()
    if not html_url.startswith(("http://", "https://")):
        return None, True
    return html_url.rstrip("/") + "/", True


def site_base_url() -> str | None:
    """Return the site origin+base (with trailing slash), or None if unavailable."""
    override = os.environ.get("SITE_PAGES_URL", "").strip()
    if override:
        return override.rstrip("/") + "/"

    global _cache
    if _cache is _UNSET:
        value, cacheable = _fetch_base()
        if cacheable:
            _cache = value
        return value  # transient failure: leave cache unset so we retry later
    return _cache  # type: ignore[return-value]


def item_url(issue: dict | None) -> str | None:
    """Return the on-site detail-page URL for ``issue``, or None.

    Mirrors ``build_site.py``'s per-item path: ``<base>items/<issue-number>/``.
    """
    if not issue:
        return None
    base = site_base_url()
    if not base:
        return None
    number = str(issue.get("number", "")).strip()
    if not number:
        return None
    return f"{base}items/{number}/"
