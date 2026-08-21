#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3}"

SCENE_PLAN="${1:?Usage: stage-transition.sh <scene-plan.json> <transition-id>}"
TRANSITION_ID="${2:?Usage: stage-transition.sh <scene-plan.json> <transition-id>}"

exec "$PYTHON_BIN" "$ROOT_DIR/stage-transition.py" "$SCENE_PLAN" "$TRANSITION_ID"
