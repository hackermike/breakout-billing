#!/usr/bin/env bash
# Poll a pull request until a given reviewer has posted a review.
#
#   ./dev-scripts/wait-for-review.sh 10                    # wait for coderabbitai
#   ./dev-scripts/wait-for-review.sh 10 someuser           # wait for another reviewer
#   ./dev-scripts/wait-for-review.sh 10 coderabbitai 30 5  # 30 attempts, 5s apart
#
# Exits 0 once the review appears, 1 on timeout.
set -euo pipefail

cd "$(dirname "$0")/.."

PR="${1:?usage: wait-for-review.sh <pr-number> [reviewer] [attempts] [interval]}"
REVIEWER="${2:-coderabbitai}"
ATTEMPTS="${3:-18}"
INTERVAL="${4:-10}"
REPO="${GH_REPO:-hackermike/breakout-billing}"

for i in $(seq 1 "${ATTEMPTS}"); do
  n=$(gh pr view "${PR}" --repo "${REPO}" --json reviews \
        --jq "[.reviews[].author.login] | map(select(. == \"${REVIEWER}\")) | length" \
        2>/dev/null || echo 0)

  if [ "${n}" -ge 1 ]; then
    echo "${REVIEWER} reviewed PR #${PR} (reviews: ${n})"
    exit 0
  fi

  echo "attempt ${i}/${ATTEMPTS}: no ${REVIEWER} review yet"
  sleep "${INTERVAL}"
done

echo "Timed out after $((ATTEMPTS * INTERVAL))s waiting on ${REVIEWER} for PR #${PR}" >&2
exit 1
