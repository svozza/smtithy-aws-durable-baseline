#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec timeout --signal=TERM --kill-after=30s 12m \
  "$root/.ai-review-toolkit/scripts/run_claude_isolated.sh" "$@"
