#!/usr/bin/env bash
set -euo pipefail

workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runner="$workspace/.ai-review-toolkit/scripts/run_claude_isolated.sh"
deadline="${AWS_DURABLE_PROBE_TIMEOUT_SECONDS:-480}"
grace="${AWS_DURABLE_PROBE_KILL_GRACE_SECONDS:-15}"

setsid --wait "$runner" "$@" <&0 >&1 2>&2 &
claude_pid=$!
sleep "$deadline" &
timer_pid=$!

set +e
wait -n -p completed_pid "$claude_pid" "$timer_pid"
first_status=$?
set -e

if [[ "$completed_pid" == "$claude_pid" ]]; then
  kill "$timer_pid" 2>/dev/null || true
  wait "$timer_pid" 2>/dev/null || true
  exit "$first_status"
fi

sudo kill -TERM -- "-$claude_pid" 2>/dev/null || true
sudo pkill -TERM -u claude-review 2>/dev/null || true
sleep "$grace"
sudo kill -KILL -- "-$claude_pid" 2>/dev/null || true
sudo pkill -KILL -u claude-review 2>/dev/null || true
wait "$claude_pid" 2>/dev/null || true
exit 124
