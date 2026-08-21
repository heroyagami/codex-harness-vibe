#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3}"
SCENES_DIR="${SCENES_DIR:-${ROOT_DIR}/scenes}"

SCENE_PLAN="${1:?Usage: assign-scene-resources.sh <scene-plan.json>}"
PLAN_PATH="$("$PYTHON_BIN" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$SCENE_PLAN")"
PLAN_DIR="$(cd "$(dirname "$PLAN_PATH")" && pwd)"
RESOURCE_POOL_DIR="${RESOURCE_POOL_DIR:-${PLAN_DIR}/resources}"

assigned_count=0
while IFS=$'\t' read -r scene_id source target; do
    [[ -n "$scene_id" ]] || continue

    if [[ ! -d "$SCENES_DIR/$scene_id" ]]; then
        echo "Scene directory not found for resource assignment: $SCENES_DIR/$scene_id" >&2
        exit 1
    fi
    if [[ ! -d "$RESOURCE_POOL_DIR" ]]; then
        echo "Resource pool directory not found: $RESOURCE_POOL_DIR" >&2
        exit 1
    fi

    source_rel="${source#resources/}"
    source_path="${RESOURCE_POOL_DIR}/${source_rel}"
    target_path="${SCENES_DIR}/${scene_id}/${target}"

    if [[ ! -f "$source_path" ]]; then
        echo "Planned image resource not found: $source_path" >&2
        exit 1
    fi

    mkdir -p "$(dirname "$target_path")"
    cp -f "$source_path" "$target_path"
    assigned_count=$((assigned_count + 1))
done < <("$PYTHON_BIN" "$ROOT_DIR/list-scene-image-resources.py" "$PLAN_PATH")

echo "Assigned ${assigned_count} planned image resource(s)"
