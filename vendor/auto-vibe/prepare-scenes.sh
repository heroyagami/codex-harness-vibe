#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3}"
PNPM_BIN="${PNPM_BIN:-pnpm}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
TEMPLATE_DIR="${TEMPLATE_DIR:-${ROOT_DIR}/sceneFolder}"
SCENES_DIR="${SCENES_DIR:-${ROOT_DIR}/scenes}"
DESIGN_SYSTEMS_DIR="${DESIGN_SYSTEMS_DIR:-${ROOT_DIR}/design-systems}"
TRANSITION_TEMPLATE_DIR="${TRANSITION_TEMPLATE_DIR:-${ROOT_DIR}/transitionFolder}"
TRANSITIONS_DIR="${TRANSITIONS_DIR:-${ROOT_DIR}/transitions}"

SCENE_PLAN="${1:?Usage: prepare-scenes.sh <scene-plan.json>}"

"$PYTHON_BIN" "$ROOT_DIR/prepare-scenes.py" \
    "$TEMPLATE_DIR" "$SCENES_DIR" "$DESIGN_SYSTEMS_DIR" \
    "$SCENE_PLAN" \
    --install-dependencies \
    --pnpm-bin "$PNPM_BIN" \
    --registry "$NPM_REGISTRY"

"$PYTHON_BIN" "$ROOT_DIR/prepare-transitions.py" \
    "$TEMPLATE_DIR" "$TRANSITION_TEMPLATE_DIR" "$TRANSITIONS_DIR" \
    "$SCENE_PLAN" \
    --shared-node-modules "$TEMPLATE_DIR/node_modules"

"$ROOT_DIR/assign-scene-resources.sh" "$SCENE_PLAN"
