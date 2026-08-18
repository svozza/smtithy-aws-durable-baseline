#!/usr/bin/env bash
set -euo pipefail

workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runner="$workspace/.ai-review-toolkit/scripts/run_claude_isolated.sh"
deadline="${AWS_DURABLE_PROBE_TIMEOUT_SECONDS:-480}"

setsid "$runner" "$@" &
claude_pid=$!

(
  sleep "$deadline"
  if kill -0 "$claude_pid" 2>/dev/null; then
    kill -TERM -- "-$claude_pid" 2>/dev/null || true
    sleep 15
    kill -KILL -- "-$claude_pid" 2>/dev/null || true
  fi
) &
watchdog_pid=$!

set +e
wait "$claude_pid"
status=$?
set -e

kill "$watchdog_pid" 2>/dev/null || true
wait "$watchdog_pid" 2>/dev/null || true
exit "$status"
