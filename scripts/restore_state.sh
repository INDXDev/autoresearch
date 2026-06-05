#!/usr/bin/env bash
# Restore one or more paths from the unified `auto-research-state` orphan branch
# into the current working tree, so a job can diff/extend the latest state.
#
# All of Auto Research's cross-run state lives on ONE orphan branch (snapshots/
# for Site Watch, selection.json for the domain picker), keeping main's history
# clean. This is the read half; scripts/save_state.sh is the write half.
#
# Usage:  scripts/restore_state.sh <branch> <path> [<path> ...]
#
# First run ever: the branch does not exist yet, so nothing is restored and the
# caller simply proceeds from empty (fresh snapshots / no remembered choice).
# Never fails the job: a missing branch or path is reported, not fatal.
set -uo pipefail

BRANCH="${1:?usage: restore_state.sh <branch> <path...>}"
shift

git fetch origin "$BRANCH" --depth=1 2>/dev/null || true

if ! git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  echo "No '$BRANCH' branch yet — nothing to restore (first run)."
  exit 0
fi

for path in "$@"; do
  # Distinguish "path genuinely absent on the branch" (fine — first run for it)
  # from "path exists but checkout failed" (a real problem: diffing would start
  # from an empty/stale baseline). `cat-file -e` works for both a blob and a
  # directory tree (e.g. snapshots/).
  if git cat-file -e "origin/$BRANCH:$path" 2>/dev/null; then
    if git checkout "origin/$BRANCH" -- "$path" 2>/dev/null; then
      echo "Restored '$path' from '$BRANCH'."
    else
      echo "::warning title=restore_state::'$path' exists on '$BRANCH' but could not be checked out — proceeding from an empty/stale state."
    fi
  else
    echo "  ('$path' not present on '$BRANCH' yet — skipping.)"
  fi
done
