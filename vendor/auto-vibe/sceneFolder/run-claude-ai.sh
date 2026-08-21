#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

scene_id="$(basename "$SCRIPT_DIR")"

RAW_LOG="${RAW_LOG:-${SCRIPT_DIR}/claude-${scene_id}.stream.jsonl}"
STDERR_LOG="${STDERR_LOG:-${SCRIPT_DIR}/claude-${scene_id}.stderr.log}"
USER_LOG="${USER_LOG:-${SCRIPT_DIR}/claude-${scene_id}.user.log}"

if [[ "${1:-}" == "--wait-message" ]]; then
  message_number="${2:-}"
  if [[ ! "$message_number" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Usage: %s --wait-message <positive-line-number>\n' "$0" >&2
    exit 2
  fi

  while true; do
    if [[ -f "$USER_LOG" ]]; then
      current_message=0
      while IFS= read -r message; do
        current_message=$((current_message + 1))
        if (( current_message == message_number )); then
          printf '%s\n' "$message"
          exit 0
        fi
      done <"$USER_LOG"
    fi
    sleep 1
  done
fi

: >"$RAW_LOG"
: >"$STDERR_LOG"
: >"$USER_LOG"

status=0
CLAUDE_CODE_BRIEF=1 claude -p \
  --brief \
  --dangerously-skip-permissions \
  --verbose \
  --output-format stream-json \
  --prompt-suggestions false \
  --append-system-prompt '每完成一个阶段，立即通过 SendUserMessage 发送一行 [[USER_MESSAGE]]...，status 使用 normal，然后继续任务。' \
  '当前目录是本场景唯一的文件上下文；在当前目录内独立完成 `claude-scene-prompt.md`。' \
  2>"$STDERR_LOG" \
| tee "$RAW_LOG" \
| jq -Rr --unbuffered '
  fromjson?
  | select(.type=="assistant")
  | .message.content[]?
  | select(.type=="tool_use" and .name=="SendUserMessage")
  | (.input.message // empty)
  | split("\n")[]
  | select(startswith("[[USER_MESSAGE]]"))
' \
| tee "$USER_LOG" || status=$?

printf '[[USER_MESSAGE]]claude 进程已结束，exit_code=%d\n' "$status" | tee -a "$USER_LOG"
exit "$status"
