#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROGRESS_FILE="$SCRIPT_DIR/progress.md"
MAX_ROUNDS="${MAX_ROUNDS:-100}"
CODEX_BIN="${CODEX_BIN:-codex}"

todo_count() {
  grep -c '^- \[ \]' "$PROGRESS_FILE" || true
}

if [[ ! -f "$PROGRESS_FILE" ]]; then
  echo "Missing progress file: $PROGRESS_FILE" >&2
  exit 1
fi

round=1
while (( round <= MAX_ROUNDS )); do
  before="$(todo_count)"

  if (( before == 0 )); then
    echo "All design systems are done."
    exit 0
  fi

  echo "Round $round: $before design system(s) remaining."

  "$CODEX_BIN" --search --ask-for-approval never exec \
    --cd "$SCRIPT_DIR" \
    --sandbox danger-full-access \
    - <<'PROMPT'
Follow progress.md.

Process exactly one remaining design system according to progress.md:
- choose the highest-weight unchecked item from weights.json
- complete the DESIGN.md motion-reference rewrite, local font setup, and validation required by progress.md
- mark that one todo item complete in progress.md
- stop after finishing that one item
PROMPT

  after="$(todo_count)"
  if (( after >= before )); then
    echo "Stopped: progress.md todo count did not decrease after round $round." >&2
    exit 1
  fi

  ((round++))
done

echo "Stopped: reached MAX_ROUNDS=$MAX_ROUNDS with $(todo_count) item(s) remaining." >&2
exit 1
