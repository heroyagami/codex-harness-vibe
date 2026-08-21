---
name: kimi-img-viewer
description: 当需要识别图像时使用此 skill。Use the bundled API-style script for local image recognition, OCR, visual question answering, and image description.
---

# Kimi Img Viewer

## Overview

Use this skill when an agent needs to inspect a local image. Do not call `kimi -p` for image recognition, and do not depend on any external helper script. The full API-style implementation is embedded in this skill's bundled script:

```bash
/usr/local/bin/python3 scripts/recognize_image_with_kimi.py '/absolute/path/to/image.png' --model k3 -p '请用中文描述这张图上有什么。'
```

The script reads and refreshes local Kimi Code credentials from `kimi login` by default when no explicit API key is provided, then calls K3 through the Kimi/OpenAI-compatible `/chat/completions` API directly.

## Quick Start

Run from this skill directory, or use the absolute path to this skill's bundled `scripts/recognize_image_with_kimi.py`.

General image description:

```bash
/usr/local/bin/python3 scripts/recognize_image_with_kimi.py '/absolute/path/to/image.jpg' --model k3 -p '请用中文描述这张图上有什么。'
```

Ask a specific visual question:

```bash
/usr/local/bin/python3 scripts/recognize_image_with_kimi.py '/absolute/path/to/image.jpg' --model k3 -q '请识别图片中的文字，并保持原有换行。'
```

Crop to a region when only part of the image matters:

```bash
/usr/local/bin/python3 scripts/recognize_image_with_kimi.py '/absolute/path/to/image.jpg' --model k3 --region '120,80,640,360' -p '请只识别这个区域里的内容。'
```

## Workflow

1. Resolve the image path first. Prefer absolute paths so the script can read the file from any working directory.
2. Always use `/usr/local/bin/python3`.
3. Use this skill's bundled `scripts/recognize_image_with_kimi.py`.
4. Pass `--model k3` explicitly.
5. Put the task in `-p/--prompt` or `-q/--question`: description, OCR, object counting, UI analysis, logo identification, comparison, or any other visual question.
6. Keep the script's default HTTP timeout at 300 seconds. When invoking it through Claude Code's Bash tool, set the Bash tool `timeout` to at least `360000` milliseconds so the outer tool does not move the command to the background after 120 seconds.
7. Keep stderr visible. Never append `2>/dev/null` or otherwise discard stderr; preserve the exception text for timeout and API diagnostics.
8. For large images, let the script downscale by default. Use `--full-resolution` only when fine detail is required and the file is small enough.
9. For targeted details, use `--region x,y,width,height` in original image pixels.
10. For debugging without an API call, use `--metadata-only` or `--dry-run`.

## Fine Detail and Region Limits

Validated locally on 2026-07-23 with k3 (clean shapes, noisy 1080x1440 with distractors, blind random markers):

- Pixel coordinates and bounding boxes: k3 returns JSON `center`/`bbox` reliably, error ≤2px for distinct elements when the image edge is ≤2000px. State the image size and top-left origin in the prompt. Ask for `bbox` when an element's "center" is ambiguous (e.g. triangles).
- Images with any edge >2000px are downscaled to max-edge 2000 before sending, so coordinates come back in the downscaled space: scale them by `original_edge/2000`, or use `--region`/`--full-resolution`.
- Region content with `--region`: reliable. The script crops locally before sending, so the model only sees the target region. Prefer `--region` over describing region coordinates in the prompt.

Practical guidance:

- Use `--region` for small text, UI elements, or local detail.
- Keep `--full-resolution --detail high` for small synthetic/debug images where fine detail matters.

## Output

The script writes the final model answer to stdout and errors to stderr. Use the stdout answer directly in the agent response.
