import argparse
import fnmatch
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

from scene_plan import ScenePlanError, read_scene_plan_document
from shared_dependencies import SharedDependenciesError, link_shared_node_modules

parser = argparse.ArgumentParser()
parser.add_argument("template_dir")
parser.add_argument("scenes_dir")
parser.add_argument("design_systems_dir")
parser.add_argument("scene_plan_path")
parser.add_argument("--install-dependencies", action="store_true")
parser.add_argument("--pnpm-bin", default="pnpm")
parser.add_argument(
    "--registry", default="https://registry.npmmirror.com"
)
args = parser.parse_args()

template_dir = Path(args.template_dir).resolve()
scenes_dir = Path(args.scenes_dir).resolve()
design_systems_dir = Path(args.design_systems_dir).resolve()
NO_DESIGN_SYSTEM = "__none__"

if not template_dir.is_dir():
    sys.exit(f"Template directory not found: {template_dir}")

ignored_names = {
    ".DS_Store",
    ".cache",
    ".git",
    ".gitignore",
    ".remotion",
    "assets",
    "build",
    "dist",
    "logs",
    "node_modules",
    "out",
    "package-lock.json",
    "yarn.lock",
    "design-system",
}
ignored_patterns = (
    "*.mp4",
    "*.mov",
    "claude-*.stream.jsonl",
    "claude-*.stderr.log",
    "claude-*.user.log",
)


def ignore_template_files(_dir, names):
    ignored = set()
    for name in names:
        if name in ignored_names or any(
            fnmatch.fnmatch(name, pattern) for pattern in ignored_patterns
        ):
            ignored.add(name)
    return ignored


def read_design_settings(candidates):
    weights_path = design_systems_dir / "weights.json"
    defaults = {
        path.name: {"theme": None, "weight": 1.0} for path in candidates
    }
    if not weights_path.exists():
        return defaults
    try:
        with weights_path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        sys.exit(f"{weights_path}: invalid JSON: {exc}")
    if not isinstance(raw, dict):
        sys.exit(f"{weights_path}: expected object mapping design names to settings")
    settings = defaults.copy()
    candidate_names = set(settings)
    candidate_names.add(NO_DESIGN_SYSTEM)
    unknown = sorted(set(raw) - candidate_names)
    if unknown:
        sys.exit(f"{weights_path}: unknown design system(s): {', '.join(unknown)}")
    for name, value in raw.items():
        allowed_fields = {"weight"} if name == NO_DESIGN_SYSTEM else {"theme", "weight"}
        if isinstance(value, dict):
            unknown_fields = sorted(set(value) - allowed_fields)
            if unknown_fields:
                sys.exit(
                    f"{weights_path}: unknown field(s) for {name}: {', '.join(unknown_fields)}"
                )
            weight = value.get("weight")
            theme = None if name == NO_DESIGN_SYSTEM else value.get("theme")
            if name != NO_DESIGN_SYSTEM and theme not in {"light", "dark"}:
                sys.exit(f"{weights_path}: theme for {name} must be light or dark")
        else:
            weight = value
            theme = (
                None
                if name == NO_DESIGN_SYSTEM
                else (
                    "dark"
                    if isinstance(weight, (int, float)) and weight >= 50
                    else "light"
                )
            )
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight <= 0
        ):
            sys.exit(f"{weights_path}: weight for {name} must be a positive number")
        settings[name] = {"theme": theme, "weight": float(weight)}
    return settings


def select_design_system(visual_theme):
    if not design_systems_dir.is_dir():
        sys.exit(f"Design systems directory not found: {design_systems_dir}")
    all_candidates = sorted(
        path
        for path in design_systems_dir.iterdir()
        if path.is_dir()
        and path.name not in {"_schema", NO_DESIGN_SYSTEM}
        and not path.name.startswith(".")
    )
    settings = read_design_settings(all_candidates)
    candidates = [
        path
        for path in all_candidates
        if settings[path.name]["theme"] in (None, visual_theme)
    ]
    options = list(candidates)
    if NO_DESIGN_SYSTEM in settings:
        options.append(None)
    if not options:
        if not all_candidates:
            sys.exit(f"No design system directories found in {design_systems_dir}")
        sys.exit(f"No {visual_theme} design systems found in {design_systems_dir}")
    return random.SystemRandom().choices(
        options,
        weights=[
            settings[NO_DESIGN_SYSTEM if option is None else option.name]["weight"]
            for option in options
        ],
        k=1,
    )[0]


def copy_design_system(scene_dir, visual_theme):
    src = select_design_system(visual_theme)
    if src is None:
        return None
    dest = scene_dir / "design-system" / src.name
    dest.parent.mkdir(exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("fonts", ".DS_Store"))
    if not (dest / "DESIGN.md").is_file():
        sys.exit(f"DESIGN.md not found in copied design system: {dest}")
    font_src = src / "fonts"
    if font_src.is_dir():
        font_dest = scene_dir / "public" / "fonts"
        font_dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(font_src, font_dest, dirs_exist_ok=True)
    return src.name


def annotate_frame_design_system(scene_dir, name, visual_theme):
    frame_path = scene_dir / "frame.md"
    if not frame_path.exists():
        sys.exit(f"frame.md not found in template copy: {frame_path}")
    text = frame_path.read_text(encoding="utf-8").rstrip()
    lines = [f"{text}\n- Visual theme: `{visual_theme}`.\n"]
    if name is not None:
        lines.append(f"- Selected design system: `design-system/{name}/`.\n")
    frame_path.write_text("".join(lines), encoding="utf-8")


def block_field(key, value):
    lines = str(value).rstrip("\n").splitlines() or [""]
    return "\n".join([f"{key}: |-"] + [f"  {line}" for line in lines])


def substitute_scene_prompt(
    scene_dir, scene_id, scene_plan, timeline_origin_seconds, fps
):
    prompt_path = scene_dir / "claude-scene-prompt.md"
    if not prompt_path.exists():
        return
    text = prompt_path.read_text(encoding="utf-8")
    try:
        _header, body = text.split("\n---\n", 1)
    except ValueError:
        sys.exit(f"{prompt_path}: missing front matter")
    header = [
        "---",
        f"scene_id: {scene_id}",
        f"output_file: {scene_plan['output_file']}",
        f"fps: {fps}",
        f"timeline_origin_seconds: {timeline_origin_seconds}",
        f"frame_range: {json.dumps(scene_plan['frame_range'])}",
        f"render_range_seconds: {json.dumps(scene_plan['render_range_seconds'], ensure_ascii=False)}",
        f"duration_in_frames: {scene_plan['duration_in_frames']}",
        f"visual_theme: {scene_plan['visual_theme']}",
        f"background_image: {scene_plan['background']['target']}",
        f"background_anchor: {scene_plan['background_anchor']['name']}",
        f"transition_handles: {json.dumps({key: key in scene_plan['boundary_contract'] for key in ('entry', 'exit')})}",
        block_field(
            "boundary_contract",
            "\n".join(scene_plan["boundary_contract"].values())
            if scene_plan["boundary_contract"]
            else "无额外交接要求",
        ),
        block_field("subtitle_text", scene_plan["subtitle_text"]),
        block_field("research_brief", scene_plan["research_brief"]),
    ]
    text = "\n".join(header) + "\n---\n" + body
    prompt_path.write_text(text, encoding="utf-8")


def write_scene_config(scene_dir, scene_plan, timeline_origin_seconds, fps):
    config_path = scene_dir / "remotion" / "scene-config.ts"
    background_image = scene_plan["background"]["target"]
    if not background_image.startswith("public/"):
        sys.exit(f"{background_image}: background target must start with public/")
    background_static_path = background_image.removeprefix("public/")
    handles = {
        "entry": "entry" in scene_plan["boundary_contract"],
        "exit": "exit" in scene_plan["boundary_contract"],
    }
    lines = [
        f"export const SCENE_ID = {json.dumps(scene_plan['scene_id'])};",
        f"export const FPS = {fps};",
        "export const WIDTH = 1080;",
        "export const HEIGHT = 1440;",
        f"export const DURATION_IN_FRAMES = {scene_plan['duration_in_frames']};",
        f"export const VISUAL_THEME = {json.dumps(scene_plan['visual_theme'])} as const;",
        f"export const TIMELINE_ORIGIN_SECONDS = {json.dumps(timeline_origin_seconds)};",
        f"export const FRAME_RANGE = {json.dumps(scene_plan['frame_range'])} as const;",
        f"export const RENDER_RANGE_SECONDS = {json.dumps(scene_plan['render_range_seconds'])} as const;",
        f"export const BACKGROUND_IMAGE = {json.dumps(background_static_path)};",
        f"export const BACKGROUND_WIDTH = {scene_plan['background']['width']};",
        f"export const BACKGROUND_HEIGHT = {scene_plan['background']['height']};",
        f"export const BACKGROUND_COLOR = {json.dumps(scene_plan['background']['fallback_color'])};",
        f"export const BACKGROUND_ANCHOR = {json.dumps(scene_plan['background_anchor'])} as const;",
        f"export const TRANSITION_HANDLES = {json.dumps(handles)} as const;",
    ]
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    metadata = {
        "scene_id": scene_plan["scene_id"],
        "output_file": scene_plan["output_file"],
        "fps": fps,
        "width": 1080,
        "height": 1440,
        "timeline_origin_seconds": timeline_origin_seconds,
        "frame_range": scene_plan["frame_range"],
        "render_range_seconds": scene_plan["render_range_seconds"],
        "duration_in_frames": scene_plan["duration_in_frames"],
        "visual_theme": scene_plan["visual_theme"],
        "background_image": background_static_path,
        "background_width": scene_plan["background"]["width"],
        "background_height": scene_plan["background"]["height"],
        "background_color": scene_plan["background"]["fallback_color"],
        "background_anchor": scene_plan["background_anchor"],
        "transition_handles": handles,
    }
    (scene_dir / "scene-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


try:
    scene_plan_document = read_scene_plan_document(args.scene_plan_path)
except ScenePlanError as exc:
    sys.exit(str(exc))
scene_plan = scene_plan_document["scenes"]
scenes_dir.mkdir(parents=True, exist_ok=True)
prepared = []
for i, plan_item in enumerate(scene_plan, start=1):
    scene_id = f"scene-{i:03d}"
    scene_dir = scenes_dir / scene_id
    try:
        scene_dir.relative_to(scenes_dir)
    except ValueError:
        sys.exit(f"Refusing to write outside SCENES_DIR: {scene_dir}")
    if scene_dir.exists():
        sys.exit(f"Scene directory exists: {scene_dir}")
    shutil.copytree(template_dir, scene_dir, ignore=ignore_template_files)
    scenes_source_dir = scene_dir / "scenes"
    scenes_source_dir.mkdir(parents=True, exist_ok=True)
    default_scene = scenes_source_dir / "DefaultScene.tsx"
    if not default_scene.exists():
        default_scene.write_text(
            'import React from "react";\n'
            'import {AbsoluteFill} from "remotion";\n\n'
            'export const DefaultScene: React.FC = () => (\n'
            '  <AbsoluteFill style={{backgroundColor: "transparent"}} />\n'
            ');\n',
            encoding="utf-8",
        )
    substitute_scene_prompt(
        scene_dir,
        scene_id,
        plan_item,
        scene_plan_document["timeline_start_seconds"],
        scene_plan_document["fps"],
    )
    write_scene_config(
        scene_dir,
        plan_item,
        scene_plan_document["timeline_start_seconds"],
        scene_plan_document["fps"],
    )
    design_system_name = copy_design_system(
        scene_dir, scene_plan_document["visual_theme"]
    )
    annotate_frame_design_system(
        scene_dir, design_system_name, scene_plan_document["visual_theme"]
    )
    (scene_dir / "public" / "img").mkdir(parents=True, exist_ok=True)
    (scene_dir / "public" / "audio").mkdir(parents=True, exist_ok=True)
    prepared.append(
        (scene_id, design_system_name, max(0, len(plan_item["image_resources"]) - 1))
    )

if args.install_dependencies:
    print(f"Installing shared dependencies in {template_dir}", flush=True)
    try:
        subprocess.run(
            [
                args.pnpm_bin,
                "install",
                "--frozen-lockfile",
                f"--registry={args.registry}",
            ],
            cwd=template_dir,
            check=True,
        )
    except FileNotFoundError:
        sys.exit(f"pnpm executable not found: {args.pnpm_bin}")
    except subprocess.CalledProcessError as exc:
        sys.exit(
            f"Shared dependency installation failed in {template_dir} "
            f"with exit code {exc.returncode}"
        )

    shared_node_modules = template_dir / "node_modules"
    try:
        for scene_id, _design_system_name, _image_resource_count in prepared:
            link_shared_node_modules(
                scenes_dir / scene_id,
                shared_node_modules,
            )
    except SharedDependenciesError as exc:
        sys.exit(str(exc))

print(
    f"Prepared {len(prepared)} {scene_plan_document['visual_theme']} scene(s) in {scenes_dir}"
)
for scene_id, design_system_name, image_resource_count in prepared:
    print(
        f"- {scene_id} ({design_system_name or 'no design system'}, "
        f"{image_resource_count} planned image resource(s))"
    )
