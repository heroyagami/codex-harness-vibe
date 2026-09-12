import argparse
import fnmatch
import json
import shutil
import sys
from pathlib import Path

from runtime_profile import (
    RuntimeProfileError,
    read_runtime_profile,
    validate_background_coverage,
)
from scene_plan import ScenePlanError, read_scene_plan_document
from shared_dependencies import SharedDependenciesError, link_shared_node_modules


parser = argparse.ArgumentParser()
parser.add_argument("scene_template_dir")
parser.add_argument("transition_template_dir")
parser.add_argument("transitions_dir")
parser.add_argument("scene_plan_path")
parser.add_argument("--shared-node-modules")
args = parser.parse_args()

scene_template_dir = Path(args.scene_template_dir).resolve()
transition_template_dir = Path(args.transition_template_dir).resolve()
transitions_dir = Path(args.transitions_dir).resolve()
shared_node_modules = (
    Path(args.shared_node_modules).resolve()
    if args.shared_node_modules
    else scene_template_dir / "node_modules"
)

for required_dir in (scene_template_dir, transition_template_dir):
    if not required_dir.is_dir():
        sys.exit(f"Template directory not found: {required_dir}")

ignored_names = {
    ".DS_Store",
    ".cache",
    ".claude",
    ".git",
    ".gitignore",
    ".remotion",
    "artifacts",
    "assets",
    "build",
    "claude-scene-prompt.md",
    "design-system",
    "dist",
    "frame.md",
    "logs",
    "node_modules",
    "out",
    "package-lock.json",
    "run-claude-ai.sh",
    "scene-metadata.json",
    "yarn.lock",
}
ignored_patterns = (
    "*.mp4",
    "*.mov",
    "claude-*.stream.jsonl",
    "claude-*.stderr.log",
    "claude-*.user.log",
)


def ignore_template_files(_dir, names):
    return {
        name
        for name in names
        if name in ignored_names
        or any(fnmatch.fnmatch(name, pattern) for pattern in ignored_patterns)
    }


def block_field(key, value):
    lines = str(value).rstrip("\n").splitlines() or [""]
    return "\n".join([f"{key}: |-"] + [f"  {line}" for line in lines])


def write_transition_prompt(transition_dir, transition, visual_theme, runtime_profile):
    prompt_path = transition_dir / "transition-prompt.md"
    text = prompt_path.read_text(encoding="utf-8")
    try:
        _header, body = text.split("\n---\n", 1)
    except ValueError:
        sys.exit(f"{prompt_path}: missing front matter")
    header = [
        "---",
        f"transition_id: {transition['transition_id']}",
        f"transition_type: {transition['type']}",
        f"output_file: {transition['output_file']}",
        f"fps: {runtime_profile.fps}",
        f"frame_range: {json.dumps(transition['frame_range'])}",
        f"time_range_seconds: {json.dumps(transition['time_range_seconds'])}",
        f"duration_in_frames: {transition['duration_in_frames']}",
        f"visual_theme: {visual_theme}",
        f"from_scene_id: {transition['from_scene_id']}",
        f"to_scene_id: {transition['to_scene_id']}",
        f"from_background_anchor: {transition['from_background_anchor']['name']}",
        f"to_background_anchor: {transition['to_background_anchor']['name']}",
        block_field("reason", transition["reason"]),
        block_field("subtitle_context", transition["subtitle_context"]),
    ]
    prompt_path.write_text("\n".join(header) + "\n---\n" + body, encoding="utf-8")


def write_transition_config(
    transition_dir, transition, background, visual_theme, runtime_profile
):
    config_path = transition_dir / "remotion" / "transition-config.ts"
    background_name = f"background{Path(background['target']).suffix.lower()}"
    foreground_travel = round(runtime_profile.height * 5 / 6)
    lines = [
        f"export const TRANSITION_ID = {json.dumps(transition['transition_id'])};",
        f"export const TRANSITION_TYPE: \"parallax\" | \"custom\" = {json.dumps(transition['type'])};",
        f"export const FPS = {runtime_profile.fps};",
        f"export const WIDTH = {runtime_profile.width};",
        f"export const HEIGHT = {runtime_profile.height};",
        f"export const DURATION_IN_FRAMES = {transition['duration_in_frames']};",
        f"export const VISUAL_THEME = {json.dumps(visual_theme)} as const;",
        f"export const BACKGROUND_IMAGE = {json.dumps(f'input/{background_name}')};",
        f"export const BACKGROUND_WIDTH = {background['width']};",
        f"export const BACKGROUND_HEIGHT = {background['height']};",
        f"export const FOREGROUND_TRAVEL = {foreground_travel};",
        f"export const BACKGROUND_COLOR = {json.dumps(background['fallback_color'])};",
        'export const FROM_FOREGROUND_IMAGE = "input/from-foreground.png";',
        'export const TO_FOREGROUND_IMAGE = "input/to-foreground.png";',
        f"export const FROM_BACKGROUND_ANCHOR = {json.dumps(transition['from_background_anchor'])} as const;",
        f"export const TO_BACKGROUND_ANCHOR = {json.dumps(transition['to_background_anchor'])} as const;",
    ]
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


try:
    runtime_profile = read_runtime_profile(args.scene_plan_path)
    document = read_scene_plan_document(args.scene_plan_path)
    if document["fps"] != runtime_profile.fps:
        raise RuntimeProfileError(
            "scene-plan timeline fps does not match runtime_profile.fps"
        )
    validate_background_coverage(runtime_profile, document["background"])
except (ScenePlanError, RuntimeProfileError) as exc:
    sys.exit(str(exc))

rendered_transitions = [
    item for item in document["transitions"] if item["type"] != "hard_cut"
]
if rendered_transitions:
    transitions_dir.mkdir(parents=True, exist_ok=True)

prepared = []
for transition in rendered_transitions:
    transition_id = transition["transition_id"]
    transition_dir = transitions_dir / transition_id
    try:
        transition_dir.relative_to(transitions_dir)
    except ValueError:
        sys.exit(f"Refusing to write outside transitions directory: {transition_dir}")
    spec_path = transition_dir / "transition-spec.json"
    if transition_dir.exists() and spec_path.exists():
        # A previous run may have been interrupted while wiring the shared
        # dependencies. Preserve the generated prompt/spec and finish only
        # the missing dependency link instead of aborting the whole run.
        local_node_modules = transition_dir / "node_modules"
        if local_node_modules.exists() and not local_node_modules.is_symlink():
            marker = local_node_modules / ".shared-dependencies"
            has_packages = any(
                item.name not in {".cache", ".DS_Store"}
                for item in local_node_modules.iterdir()
            )
            if not marker.exists() and not has_packages:
                shutil.rmtree(local_node_modules)
        if not local_node_modules.exists() and not local_node_modules.is_symlink():
            try:
                link_shared_node_modules(transition_dir, shared_node_modules)
            except SharedDependenciesError as exc:
                sys.exit(str(exc))
        prepared.append(transition_id)
        continue
    if transition_dir.exists():
        sys.exit(
            f"Incomplete transition directory without transition-spec.json: {transition_dir}"
        )

    shutil.copytree(scene_template_dir, transition_dir, ignore=ignore_template_files)
    shutil.copytree(
        transition_template_dir,
        transition_dir,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".DS_Store"),
    )
    default_scene = transition_dir / "scenes" / "DefaultScene.tsx"
    scene_config = transition_dir / "remotion" / "scene-config.ts"
    default_scene.unlink(missing_ok=True)
    scene_config.unlink(missing_ok=True)
    (transition_dir / "public" / "input").mkdir(parents=True, exist_ok=True)

    write_transition_prompt(
        transition_dir,
        transition,
        document["visual_theme"],
        runtime_profile,
    )
    write_transition_config(
        transition_dir,
        transition,
        document["background"],
        document["visual_theme"],
        runtime_profile,
    )
    spec = {
        "transition_id": transition_id,
        "output_file": transition["output_file"],
        "type": transition["type"],
        "reason": transition["reason"],
        "subtitle_context": transition["subtitle_context"],
        "fps": runtime_profile.fps,
        "width": runtime_profile.width,
        "height": runtime_profile.height,
        "visual_theme": document["visual_theme"],
        "frame_range": transition["frame_range"],
        "time_range_seconds": transition["time_range_seconds"],
        "duration_in_frames": transition["duration_in_frames"],
        "from_scene_id": transition["from_scene_id"],
        "to_scene_id": transition["to_scene_id"],
        "background": document["background"],
        "from_background_anchor": transition["from_background_anchor"],
        "to_background_anchor": transition["to_background_anchor"],
    }
    spec_path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        link_shared_node_modules(transition_dir, shared_node_modules)
    except SharedDependenciesError as exc:
        sys.exit(str(exc))
    prepared.append(transition_id)

print(
    f"Prepared {len(prepared)} rendered transition(s) in {transitions_dir} "
    f"at {runtime_profile.name}"
)
for transition_id in prepared:
    print(f"- {transition_id}")
