#!/usr/bin/env bash
# Squash-merge a PR, delete its branch, and return to an up-to-date main.
#
#   ./dev-scripts/merge-pr.sh 12
#
# Guards: the PR's CI must be green (gh refuses to merge otherwise unless you
# pass --admin, which this script intentionally does not).
set -euo pipefail

cd "$(dirname "$0")/.."

PR="${1:?usage: merge-pr.sh <pr-number>}"
REPO="${GH_REPO:-hackermike/breakout-billing}"

gh pr merge "${PR}" --repo "${REPO}" --squash --delete-branch

git checkout main
git pull --ff-only origin main

echo "Merged PR #${PR}; main is up to date."
git log --oneline -1
