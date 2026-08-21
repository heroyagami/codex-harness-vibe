#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <ratio> <image_prompt> <output_path> [reference_image ...]" >&2
  echo "Example: $0 3:4 'preserve the subject and pose; use soft natural light' public/img/cat-restyled.png public/img/cat-reference.png" >&2
  exit 2
fi

ratio="$1"
image_prompt="$2"
output_path="$3"
shift 3
output_dir="$(dirname -- "$output_path")"

reference_instruction=""
codex_args=(
  -a never exec
  --skip-git-repo-check
  --sandbox workspace-write
  --ephemeral
)

if [ "$#" -gt 5 ]; then
  echo "Error: at most 5 reference images are supported" >&2
  exit 2
fi

if [ "$#" -gt 0 ]; then
  reference_instruction="Use every attached image as a source input for the requested edit, restyle, or composite, in attachment order. Apply the named changes and preserve the named invariants. "
  for reference_image in "$@"; do
    if [ ! -f "$reference_image" ]; then
      echo "Error: reference image does not exist: $reference_image" >&2
      exit 2
    fi
    codex_args+=(--image "$reference_image")
  done
fi

mkdir -p "$output_dir"

codex_args+=(
  --
  "Use \$imagegen to create one image with a ${ratio} aspect ratio. ${reference_instruction}Image requirements: ${image_prompt}. Save it to ${output_path}. If the generated file is first placed in the local generated-image directory, find the newest PNG from this session and copy it to ${output_path}. Do not explain the process; output only the final path."
)

codex "${codex_args[@]}"

if [ ! -f "$output_path" ]; then
  echo "Error: expected output file was not created: $output_path" >&2
  exit 1
fi

echo "$output_path"
