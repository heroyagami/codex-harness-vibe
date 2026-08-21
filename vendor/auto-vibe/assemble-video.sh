#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3}"

SCENE_PLAN="${1:?Usage: assemble-video.sh <scene-plan.json> [output.mov]}"
shift

if [[ $# -gt 0 ]]; then
    exec "$PYTHON_BIN" "$ROOT_DIR/assemble-video.py" "$SCENE_PLAN" --output "$1"
fi
exec "$PYTHON_BIN" "$ROOT_DIR/assemble-video.py" "$SCENE_PLAN"
