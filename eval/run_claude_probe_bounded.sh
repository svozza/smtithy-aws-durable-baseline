#!/usr/bin/env bash
set -euo pipefail

workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runner="$workspace/.ai-review-toolkit/scripts/run_claude_isolated.sh"
deadline="${AWS_DURABLE_PROBE_TIMEOUT:-8m}"

exec timeout --signal=TERM --kill-after=30s "$deadline" \
  "$runner" "$@"
