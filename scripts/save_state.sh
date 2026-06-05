#!/usr/bin/env bash
# Save one or more paths to the unified `auto-research-state` orphan branch via a
# throwaway worktree, so main's history is never touched.
#
# All of Auto Research's cross-run state lives on ONE orphan branch (snapshots/
# for Site Watch, selection.json for the domain picker). Different jobs each save
# their OWN disjoint path(s) to this branch, so a push can lose a race against
# any concurrent writer (non-fast-forward). We therefore rebuild from the latest
# tip and retry: because the jobs touch different paths, the retried commit
# cleanly layers on top of whatever else was just pushed. (The watch job
# `needs: select`, so in the normal flow select's write has already landed.)
#
# Usage:  scripts/save_state.sh <branch> <path> [<path> ...]
#
# Authenticates the push with GITHUB_TOKEN (pinned on the origin remote — the
# credential actions/checkout persists is not reliably applied to pushes from a
# separate worktree). Never prints the token. Never fails the job.
set -uo pipefail

BRANCH="${1:?usage: save_state.sh <branch> <path...>}"
shift
PATHS=("$@")

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
  git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
fi

MAX_ATTEMPTS=5
attempt=0
while :; do
  attempt=$((attempt + 1))

  # Rebuild a worktree pointing at the BRANCH's latest tip (or a fresh orphan).
  git fetch origin "$BRANCH" --depth=1 2>/dev/null || true
  work="$(mktemp -d)"; rm -rf "$work"
  # Clear any local branch left by a previous failed attempt, so the orphan-create
  # path below can't fail with "a branch named '$BRANCH' already exists".
  git branch -D "$BRANCH" >/dev/null 2>&1 || true

  # Build the worktree, and VERIFY it — a silent failure here used to leave
  # `$work` a non-git dir, where `diff --cached` returns 128/129 (misread as
  # "has changes") and the commit/push then fail invisibly.
  if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
    git worktree add --force "$work" "origin/$BRANCH" >/dev/null 2>&1 \
      && git -C "$work" checkout -B "$BRANCH" >/dev/null 2>&1
  else
    git worktree add --force --orphan -b "$BRANCH" "$work" >/dev/null 2>&1
  fi
  if ! git -C "$work" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    rm -rf "$work"
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
      echo "::warning title=save_state::could not prepare a worktree for '$BRANCH' after $MAX_ATTEMPTS attempts — state not saved this run."
      break
    fi
    echo "Could not prepare a worktree for '$BRANCH' (attempt $attempt/$MAX_ATTEMPTS) — retrying."
    continue
  fi

  # Copy each path's current content over and stage it.
  for path in "${PATHS[@]}"; do
    [ -e "$path" ] || { echo "  ('$path' missing locally — not saving it.)"; continue; }
    rm -rf "${work:?}/$path"
    mkdir -p "$work/$(dirname "$path")"
    cp -a "$path" "$work/$path"
    git -C "$work" add "$path" >/dev/null 2>&1 || true
  done

  # rc: 0 = nothing staged, 1 = real changes, >1 = git error. Only 1 commits.
  git -C "$work" diff --cached --quiet >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "No changes for [${PATHS[*]}] on '$BRANCH'."
    git worktree remove --force "$work" >/dev/null 2>&1
    break
  elif [ "$rc" -ne 1 ]; then
    echo "::warning title=save_state::could not stage [${PATHS[*]}] on '$BRANCH' (git rc=$rc) — state not saved this run."
    git worktree remove --force "$work" >/dev/null 2>&1 || rm -rf "$work"
    break
  fi

  if git -C "$work" commit -m "Auto Research state: update ${PATHS[*]} [skip ci]" >/dev/null 2>&1 \
     && git -C "$work" push origin "HEAD:$BRANCH" >/dev/null 2>&1; then
    echo "Saved [${PATHS[*]}] to '$BRANCH'."
    git worktree remove --force "$work" >/dev/null 2>&1
    break
  fi

  git worktree remove --force "$work" >/dev/null 2>&1
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "::warning title=save_state::could not push to '$BRANCH' after $MAX_ATTEMPTS attempts — state not saved this run."
    break
  fi
  echo "Push to '$BRANCH' lost a race (attempt $attempt/$MAX_ATTEMPTS) — refetching and retrying."
done
