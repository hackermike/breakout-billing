#!/usr/bin/env bash
# Open a pull request with the body read from a file.
#
#   ./dev-scripts/open-pr.sh "Recurring appointments" scripts/dev/pr-body.md
#   ./dev-scripts/open-pr.sh "Title" body.md main            # explicit base branch
#
# Markdown bodies must never be passed as a shell argument: a newline followed
# by `#` (any heading) trips a path-validation check that cannot be allowlisted.
# Reading from a file sidesteps it entirely.
set -euo pipefail

cd "$(dirname "$0")/.."

TITLE="${1:?usage: open-pr.sh <title> <body-file> [base-branch]}"
BODY_FILE="${2:?usage: open-pr.sh <title> <body-file> [base-branch]}"
BASE="${3:-main}"
REPO="${GH_REPO:-hackermike/breakout-billing}"

if [[ ! -f "${BODY_FILE}" ]]; then
  echo "Body file not found: ${BODY_FILE}" >&2
  exit 1
fi

HEAD="$(git rev-parse --abbrev-ref HEAD)"

if [ "${HEAD}" = "${BASE}" ]; then
  echo "Refusing to open a PR from ${BASE} into itself. Create a branch first." >&2
  exit 1
fi

# Make sure the branch exists on the remote, or gh has nothing to compare.
git push -u origin "${HEAD}"

gh pr create \
  --repo "${REPO}" \
  --base "${BASE}" \
  --head "${HEAD}" \
  --title "${TITLE}" \
  --body-file "${BODY_FILE}"
