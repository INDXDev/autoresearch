"""Output mode: publish research reports as GitHub Issues.

The publisher creates one Issue per item (each news item / paper / hypothesis),
all carrying their section's labels. This module is the thin API layer.

It uses the token GitHub Actions provides automatically as ``GITHUB_TOKEN``
(you do not need to create a personal token). The target repo is read from
``GITHUB_REPOSITORY`` (also auto-set inside Actions, e.g. ``owner/name``).

Requirements:
* The workflow must grant ``issues: write`` permission.
* ``GITHUB_TOKEN`` must be passed into the step's env.

Security: the token is never printed. Only safe status messages are logged.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.github.com"


def _is_set(value: str | None) -> bool:
    return bool(value and value.strip())


def base_labels() -> list[str]:
    """Shared labels applied to every Issue, from GITHUB_ISSUE_LABELS.

    Comma-separated. Empty by default. GitHub auto-creates labels that do not
    yet exist; if a label is rejected, :func:`create_issue` retries without
    labels so the Issue is still created.
    """
    raw = os.environ.get("GITHUB_ISSUE_LABELS", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _post_issue(repo: str, token: str, payload: dict[str, object]) -> tuple[bool, int, dict]:
    """POST a single issue. Returns ``(ok, status_code, data)``."""
    request = urllib.request.Request(
        f"{API_ROOT}/repos/{repo}/issues",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "auto-research-template",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        return True, response.status, data
    except urllib.error.HTTPError as exc:
        # Do not echo the response body; status only, to avoid leaking data.
        return False, exc.code, {}
    except urllib.error.URLError as exc:
        print(f"GitHub Issue creation failed ({type(exc).__name__}). Skipping.")
        return False, 0, {}


def _api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "auto-research-template",
    }


def _paginated_get(endpoint: str, params: dict, limit: int, what: str) -> list[dict]:
    """GET a list endpoint, following pagination until ``limit`` items or the
    last page. Returns a list of dicts; never raises.

    GitHub caps ``per_page`` at 100 and exposes further results only via the
    ``page`` parameter, so a single request silently drops everything past the
    first 100. This walks pages (page=1,2,…) until a short page is returned or
    ``limit`` items have been collected, then slices to ``limit``. Returns an
    empty list when the token/repo are missing or a request fails.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not _is_set(token) or not _is_set(repo) or "/" not in repo:
        return []

    results: list[dict] = []
    page = 1
    while len(results) < limit:
        query = urllib.parse.urlencode({**params, "per_page": 100, "page": page})
        request = urllib.request.Request(
            f"{API_ROOT}/repos/{repo}/{endpoint}?{query}",
            method="GET",
            headers=_api_headers(token),
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Status only (e.g. 403/429 rate limit) — never echo the body.
            print(f"Could not {what} (HTTP {exc.code}). Continuing with what we have.")
            break
        except urllib.error.URLError as exc:
            print(f"Could not {what} ({type(exc).__name__}). Continuing with what we have.")
            break
        if not isinstance(data, list) or not data:
            break
        results.extend(item for item in data if isinstance(item, dict))
        if len(data) < 100:
            break  # last page
        page += 1
    return results[:limit]


def list_issues(label: str, state: str = "all", limit: int = 50) -> list[dict]:
    """List recent Issues carrying ``label``. Returns a list of issue dicts.

    Used to give the research step awareness of what was already published, so it
    can avoid proposing duplicates. Pull requests are filtered out. Pagination is
    followed so callers asking for more than 100 (e.g. the site builder) get the
    full set. Returns an empty list (never raises) when the token/repo are missing
    or the call fails, so a context-gathering step degrades gracefully.
    """
    params = {"labels": label, "state": state, "sort": "created", "direction": "desc"}
    data = _paginated_get("issues", params, limit, "list existing Issues")
    # The /issues endpoint also returns PRs; drop them.
    return [item for item in data if "pull_request" not in item][:limit]


def list_comments(issue_number: int, limit: int = 100) -> list[dict]:
    """List the comments on an Issue, oldest first. Returns comment dicts.

    Used by the static-site exporter to render an Issue's discussion (the lab's
    notes/feedback) onto its page. Each comment dict carries ``user`` (with
    ``login``), ``body``, ``created_at``, ``html_url``, ``author_association``
    and a ``reactions`` summary object — the default media type already includes
    reactions, so no extra Accept header is needed. Pagination is followed so
    busy threads aren't truncated at 100.

    Returns an empty list (never raises) when the token/repo are missing or the
    call fails, so the site still builds (just without comments).
    """
    return _paginated_get(
        f"issues/{issue_number}/comments", {}, limit,
        f"list comments for Issue #{issue_number}",
    )


def list_labels(limit: int = 100) -> list[str]:
    """List the label names that already exist in the repo.

    Used to show the auto-labeler the repo's current label taxonomy so it can
    REUSE an existing label rather than minting a near-duplicate. Pagination is
    followed so a taxonomy larger than 100 labels is seen in full. Returns an
    empty list (never raises) when the token/repo are missing or the call fails.
    """
    data = _paginated_get("labels", {}, limit, "list repo labels")
    return [item["name"] for item in data if item.get("name")]


def add_labels(issue_number: int, labels: list[str]) -> bool:
    """Add labels to an existing Issue (ADDITIVE — existing labels are kept).

    Uses POST /issues/{n}/labels, which appends without removing what's already
    there and auto-creates any label that does not yet exist. Returns ``True``
    on success. Never raises and never logs the token.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    labels = [str(name).strip() for name in labels if str(name).strip()]
    if not labels:
        return False
    if not _is_set(token) or not _is_set(repo) or "/" not in repo:
        print("GITHUB_TOKEN/REPOSITORY not configured. Skipping label add.")
        return False

    request = urllib.request.Request(
        f"{API_ROOT}/repos/{repo}/issues/{issue_number}/labels",
        data=json.dumps({"labels": labels}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "auto-research-template",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            ok = 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        print(f"Adding labels to Issue #{issue_number} returned HTTP {exc.code}. Skipping.")
        return False
    except urllib.error.URLError as exc:
        print(f"Adding labels to Issue #{issue_number} failed ({type(exc).__name__}). Skipping.")
        return False
    if ok:
        print(f"Labelled Issue #{issue_number}: +[{', '.join(labels)}]")
    return ok


def _safe_labels(labels: list[str]) -> list[str]:
    """Keep only labels GitHub will accept (non-empty, ≤50 chars after trim).

    Used to recover from an HTTP 422 caused by a single malformed label (e.g. an
    over-long or empty one) WITHOUT discarding the valid pipeline/section tags an
    Issue needs to be found by the site builder and de-dup.
    """
    out: list[str] = []
    for raw in labels:
        name = str(raw).strip()
        if 0 < len(name) <= 50 and name not in out:
            out.append(name)
    return out


def create_issue(title: str, body: str, labels: list[str] | None = None) -> dict | None:
    """Create a GitHub Issue. Returns the issue data dict on success, else None.

    ``labels`` defaults to :func:`base_labels`. If GitHub rejects the request
    with HTTP 422 while labels were supplied, the call first retries with the
    valid labels kept (dropping only malformed ones, so section/pipeline tags
    survive), and only as a last resort retries with no labels at all. Never
    raises and never logs the token. The returned dict includes ``number`` and
    ``html_url`` from the GitHub API.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not _is_set(token):
        print("GITHUB_TOKEN is not configured. Skipping GitHub Issue creation.")
        return None
    if not _is_set(repo) or "/" not in repo:
        print("GITHUB_REPOSITORY is not set (expected 'owner/name'). Skipping GitHub Issue.")
        return None

    if labels is None:
        labels = base_labels()

    payload: dict[str, object] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    ok, status, data = _post_issue(repo, token, payload)

    # If labels caused a validation error, first retry keeping only the valid
    # ones (so section/pipeline tags survive a single malformed label), then
    # fall back to no labels at all only if that still fails.
    if not ok and status == 422 and labels:
        safe = _safe_labels(labels)
        if safe and safe != labels:
            print("GitHub rejected the labels (HTTP 422). Retrying with the valid labels only.")
            ok, status, data = _post_issue(repo, token, {"title": title, "body": body, "labels": safe})
            if ok:
                labels = safe
        if not ok and status == 422:
            print("GitHub still rejected the labels (HTTP 422). Retrying without labels.")
            ok, status, data = _post_issue(repo, token, {"title": title, "body": body})
            if ok:
                labels = []

    if ok:
        number = data.get("number")
        shown = f" [{', '.join(labels)}]" if labels else ""
        print(f"Created GitHub Issue #{number}: {title}{shown}")
        return data

    print(f"GitHub Issue creation returned HTTP {status}. Skipping.")
    return None


if __name__ == "__main__":
    create_issue("Auto Research test issue", "This is a test body.", labels=["auto-research"])
