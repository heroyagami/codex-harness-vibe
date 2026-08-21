#!/usr/local/bin/python3

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCENE_TEMPLATE = ROOT / "sceneFolder"
TRANSITION_TEMPLATE = ROOT / "transitionFolder"
VISUAL_THEME = os.environ.get("VISUAL_THEME", "dark")
THEMES = {
    "dark": {
        "background": ROOT / "resources" / "backgrounds" / "darkbg.png",
        "color": "#08090b",
    },
    "light": {
        "background": ROOT / "resources" / "backgrounds" / "lightbg.png",
        "color": "#eadeca",
    },
}
WORK_DIR = ROOT / ".parallax-demo-work"
OUTPUT = ROOT / "parallax-demo.mov"
PREVIEW = ROOT / "parallax-demo.mp4"
FRAMES_PER_TRANSITION = 30
BACKGROUND_WIDTH = 1480
BACKGROUND_HEIGHT = 1840
FOREGROUND_TRAVEL = 1200
CAMERA_STOPS = (
    {
        "label": "TOP LEFT",
        "accent": "#5ee7ff",
        "secondary": "#6e7cff",
        "anchor": {"name": "top_left", "x": 0, "y": 0},
    },
    {
        "label": "TOP RIGHT",
        "accent": "#ff6fd8",
        "secondary": "#8d7cff",
        "anchor": {"name": "top_right", "x": 1, "y": 0},
    },
    {
        "label": "BOTTOM RIGHT",
        "accent": "#ffd166",
        "secondary": "#ff7b54",
        "anchor": {"name": "bottom_right", "x": 1, "y": 1},
    },
    {
        "label": "BOTTOM LEFT",
        "accent": "#65f0a5",
        "secondary": "#35b8ff",
        "anchor": {"name": "bottom_left", "x": 0, "y": 1},
    },
    {
        "label": "TOP LEFT",
        "accent": "#5ee7ff",
        "secondary": "#6e7cff",
        "anchor": {"name": "top_left", "x": 0, "y": 0},
    },
)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def run(command, cwd, env=None):
    print(f"[parallax-demo] {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode != 0:
        fail(f"Command failed ({result.returncode}): {' '.join(command)}")


def foreground_svg(label, accent, secondary):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 1080 1440">
  <defs>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="{accent}"/>
      <stop offset="1" stop-color="{secondary}"/>
    </linearGradient>
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="14" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g transform="translate(190 430)">
    <rect width="700" height="430" rx="38" fill="#0c111c" fill-opacity="0.92" stroke="url(#line)" stroke-width="3"/>
    <circle cx="92" cy="92" r="30" fill="{accent}" filter="url(#glow)"/>
    <text x="148" y="108" fill="#f7f8fb" font-family="Arial, sans-serif" font-size="42" font-weight="700">{label}</text>
    <rect x="62" y="166" width="576" height="2" fill="url(#line)" opacity="0.7"/>
    <rect x="62" y="218" width="410" height="22" rx="11" fill="#dce5f4" opacity="0.9"/>
    <rect x="62" y="270" width="520" height="16" rx="8" fill="#8b99ad" opacity="0.62"/>
    <rect x="62" y="310" width="455" height="16" rx="8" fill="#8b99ad" opacity="0.42"/>
    <rect x="62" y="362" width="190" height="4" rx="2" fill="{accent}"/>
  </g>
</svg>
"""


def write_transition_config(segment_index):
    from_stop = CAMERA_STOPS[segment_index]
    to_stop = CAMERA_STOPS[segment_index + 1]
    from_anchor = json.dumps(from_stop["anchor"], separators=(",", ":"))
    to_anchor = json.dumps(to_stop["anchor"], separators=(",", ":"))
    config = f"""export const TRANSITION_ID = "parallax-demo-{segment_index + 1:02d}";
export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1440;
export const DURATION_IN_FRAMES = {FRAMES_PER_TRANSITION};
export const VISUAL_THEME = "{VISUAL_THEME}" as const;
export const BACKGROUND_IMAGE = "input/background.png";
export const BACKGROUND_WIDTH = {BACKGROUND_WIDTH};
export const BACKGROUND_HEIGHT = {BACKGROUND_HEIGHT};
export const FOREGROUND_TRAVEL = {FOREGROUND_TRAVEL};
export const BACKGROUND_COLOR = "{THEMES[VISUAL_THEME]['color']}";
export const FROM_FOREGROUND_IMAGE = "input/scene-{segment_index + 1:02d}.svg";
export const TO_FOREGROUND_IMAGE = "input/scene-{segment_index + 2:02d}.svg";
export const FROM_BACKGROUND_ANCHOR = {from_anchor} as const;
export const TO_BACKGROUND_ANCHOR = {to_anchor} as const;
"""
    (WORK_DIR / "remotion" / "transition-config.ts").write_text(
        config, encoding="utf-8"
    )


def write_demo_root():
    (WORK_DIR / "remotion" / "Root.tsx").write_text(
        """import React from \"react\";
import { Composition } from \"remotion\";
import { ParallaxTransition } from \"../scenes/ParallaxTransition\";
import { DURATION_IN_FRAMES, FPS, HEIGHT, WIDTH } from \"./transition-config\";

export const COMPOSITION_ID = \"default\";

export const Root = () => (
  <Composition
    id={COMPOSITION_ID}
    component={ParallaxTransition}
    durationInFrames={DURATION_IN_FRAMES}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
""",
        encoding="utf-8",
    )


def write_spec(transition_id, output_file, duration_in_frames):
    spec = {
        "transition_id": transition_id,
        "output_file": output_file,
        "fps": 30,
        "width": 1080,
        "height": 1440,
        "visual_theme": VISUAL_THEME,
        "duration_in_frames": duration_in_frames,
    }
    (WORK_DIR / "transition-spec.json").write_text(
        json.dumps(spec, indent=2) + "\n", encoding="utf-8"
    )


def prepare_workspace():
    if VISUAL_THEME not in THEMES:
        fail("VISUAL_THEME must be light or dark")
    background = THEMES[VISUAL_THEME]["background"]
    if not background.is_file():
        fail(f"Shared background not found: {background}")
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    ignored = shutil.ignore_patterns(
        ".DS_Store",
        ".cache",
        ".remotion",
        "artifacts",
        "build",
        "dist",
        "logs",
        "node_modules",
        "out",
        "*.mov",
        "*.mp4",
    )
    shutil.copytree(SCENE_TEMPLATE, WORK_DIR, ignore=ignored)
    shutil.copytree(TRANSITION_TEMPLATE, WORK_DIR, dirs_exist_ok=True, ignore=ignored)
    (WORK_DIR / "scenes" / "DefaultScene.tsx").unlink(missing_ok=True)
    (WORK_DIR / "remotion" / "scene-config.ts").unlink(missing_ok=True)
    write_demo_root()

    node_modules = SCENE_TEMPLATE / "node_modules"
    if not node_modules.is_dir():
        fail(f"Install scene template dependencies first: {node_modules}")
    (WORK_DIR / "node_modules").symlink_to(node_modules, target_is_directory=True)

    input_dir = WORK_DIR / "public" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    background_source = input_dir / "background-source.png"
    shutil.copy2(background, background_source)
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(background_source),
            "-vf",
            (
                f"scale={BACKGROUND_WIDTH}:{BACKGROUND_HEIGHT}:"
                "force_original_aspect_ratio=increase,"
                f"crop={BACKGROUND_WIDTH}:{BACKGROUND_HEIGHT}"
            ),
            str(input_dir / "background.png"),
        ],
        WORK_DIR,
    )
    background_source.unlink()
    for index, stop in enumerate(CAMERA_STOPS, start=1):
        (input_dir / f"scene-{index:02d}.svg").write_text(
            foreground_svg(stop["label"], stop["accent"], stop["secondary"]),
            encoding="utf-8",
        )

    write_transition_config(0)
    write_spec("parallax-demo-01", "segment-01.mov", FRAMES_PER_TRANSITION)


def render_segments():
    run(["pnpm", "run", "verify"], WORK_DIR)
    segment_names = []
    for segment_index in range(len(CAMERA_STOPS) - 1):
        segment_name = f"segment-{segment_index + 1:02d}.mov"
        transition_id = f"parallax-demo-{segment_index + 1:02d}"
        write_transition_config(segment_index)
        write_spec(transition_id, segment_name, FRAMES_PER_TRANSITION)
        env = {**os.environ, "REMOTION_OUTPUT": segment_name}
        run(["pnpm", "run", "remotion:render"], WORK_DIR, env=env)
        run(["pnpm", "run", "render:verify"], WORK_DIR)
        segment_names.append(segment_name)
    return segment_names


def concatenate_segments(segment_names):
    concat_path = WORK_DIR / "parallax-demo.ffconcat"
    concat_path.write_text(
        "ffconcat version 1.0\n"
        + "".join(f"file '{segment_name}'\n" for segment_name in segment_names),
        encoding="utf-8",
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            "parallax-demo.mov",
        ],
        WORK_DIR,
    )
    total_frames = FRAMES_PER_TRANSITION * (len(CAMERA_STOPS) - 1)
    write_spec("parallax-demo-loop", "parallax-demo.mov", total_frames)
    run(["pnpm", "run", "render:verify"], WORK_DIR)


def main():
    prepare_workspace()
    segment_names = render_segments()
    concatenate_segments(segment_names)
    shutil.copy2(WORK_DIR / "parallax-demo.mov", OUTPUT)
    shutil.rmtree(WORK_DIR)
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(OUTPUT),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(PREVIEW),
        ],
        ROOT,
    )
    total_frames = FRAMES_PER_TRANSITION * (len(CAMERA_STOPS) - 1)
    print(
        f"[parallax-demo] Ready: {OUTPUT} and {PREVIEW} "
        f"({total_frames} frames, four-direction closed loop)",
        flush=True,
    )


if __name__ == "__main__":
    main()
