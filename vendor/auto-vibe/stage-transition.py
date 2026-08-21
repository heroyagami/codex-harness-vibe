import argparse
import filecmp
import json
import shutil
import sys
from pathlib import Path

from scene_plan import ScenePlanError, read_scene_plan_document


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Cannot read {path}: {exc}")


def require_file(path):
    if not path.is_file():
        fail(f"Required transition input not found: {path}")
    return path


def resolve_scene_artifact(scene_dir, value, label):
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a relative artifact path")
    candidate = (scene_dir / value).resolve()
    try:
        candidate.relative_to(scene_dir.resolve())
    except ValueError:
        fail(f"{label} must stay inside {scene_dir}")
    return require_file(candidate)


def validate_scene_manifest(scene, manifest, required_handle):
    expected = {
        "scene_id": scene["scene_id"],
        "fps": 30,
        "width": 1080,
        "height": 1440,
        "frame_range": scene["frame_range"],
        "duration_in_frames": scene["duration_in_frames"],
        "visual_theme": scene["visual_theme"],
        "background": scene["background"]["target"],
        "background_width": scene["background"]["width"],
        "background_height": scene["background"]["height"],
        "background_color": scene["background"]["fallback_color"],
        "background_anchor": scene["background_anchor"],
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            fail(
                f"{scene['scene_id']} manifest {field} is {manifest.get(field)!r}, expected {value!r}"
            )
    handle = manifest.get("handles", {}).get(required_handle)
    if not isinstance(handle, dict):
        fail(f"{scene['scene_id']} manifest is missing {required_handle} handle")
    return handle


def copy_input(source, input_dir, name):
    require_file(source)
    target = input_dir / name
    shutil.copy2(source, target)
    return f"public/input/{name}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_plan_path")
    parser.add_argument("transition_id")
    parser.add_argument("--scenes-dir")
    parser.add_argument("--transitions-dir")
    args = parser.parse_args()

    plan_path = Path(args.scene_plan_path).resolve()
    root_dir = plan_path.parent
    scenes_dir = (
        Path(args.scenes_dir).resolve() if args.scenes_dir else root_dir / "scenes"
    )
    transitions_dir = (
        Path(args.transitions_dir).resolve()
        if args.transitions_dir
        else root_dir / "transitions"
    )
    try:
        document = read_scene_plan_document(plan_path)
    except ScenePlanError as exc:
        fail(str(exc))

    transition = next(
        (
            item
            for item in document["transitions"]
            if item["transition_id"] == args.transition_id
        ),
        None,
    )
    if transition is None:
        fail(f"Transition not found: {args.transition_id}")
    if transition["type"] == "hard_cut":
        fail(f"{args.transition_id} is a hard cut and has no staged transition inputs")
    scene_by_id = {scene["scene_id"]: scene for scene in document["scenes"]}
    from_scene = scene_by_id[transition["from_scene_id"]]
    to_scene = scene_by_id[transition["to_scene_id"]]
    from_dir = scenes_dir / from_scene["scene_id"]
    to_dir = scenes_dir / to_scene["scene_id"]
    transition_dir = transitions_dir / transition["transition_id"]
    if not transition_dir.is_dir():
        fail(f"Transition directory not found: {transition_dir}")

    from_manifest_path = require_file(from_dir / "artifacts" / "scene-manifest.json")
    to_manifest_path = require_file(to_dir / "artifacts" / "scene-manifest.json")
    from_manifest = load_json(from_manifest_path)
    to_manifest = load_json(to_manifest_path)
    from_handle = validate_scene_manifest(from_scene, from_manifest, "exit")
    to_handle = validate_scene_manifest(to_scene, to_manifest, "entry")
    require_file(from_dir / from_scene["output_file"])
    require_file(to_dir / to_scene["output_file"])
    from_background = resolve_scene_artifact(
        from_dir,
        from_manifest.get("background"),
        f"{from_scene['scene_id']} background",
    )
    to_background = resolve_scene_artifact(
        to_dir,
        to_manifest.get("background"),
        f"{to_scene['scene_id']} background",
    )
    if not filecmp.cmp(from_background, to_background, shallow=False):
        fail("Adjacent scenes must use the same shared background file")

    input_dir = transition_dir / "public" / "input"
    if input_dir.exists():
        shutil.rmtree(input_dir)
    input_dir.mkdir(parents=True)
    background_name = (
        f"background{Path(document['background']['target']).suffix.lower()}"
    )
    staged = {
        "background": copy_input(from_background, input_dir, background_name),
        "from_foreground": copy_input(
            resolve_scene_artifact(
                from_dir,
                from_handle.get("foreground"),
                f"{from_scene['scene_id']} exit foreground",
            ),
            input_dir,
            "from-foreground.png",
        ),
        "from_composite": copy_input(
            resolve_scene_artifact(
                from_dir,
                from_handle.get("composite"),
                f"{from_scene['scene_id']} exit composite",
            ),
            input_dir,
            "from-composite.png",
        ),
        "to_foreground": copy_input(
            resolve_scene_artifact(
                to_dir,
                to_handle.get("foreground"),
                f"{to_scene['scene_id']} entry foreground",
            ),
            input_dir,
            "to-foreground.png",
        ),
        "to_composite": copy_input(
            resolve_scene_artifact(
                to_dir,
                to_handle.get("composite"),
                f"{to_scene['scene_id']} entry composite",
            ),
            input_dir,
            "to-composite.png",
        ),
    }
    inputs_manifest = {
        "transition_id": transition["transition_id"],
        "from_scene_output": str(
            (from_dir / from_scene["output_file"]).relative_to(root_dir)
        ),
        "to_scene_output": str(
            (to_dir / to_scene["output_file"]).relative_to(root_dir)
        ),
        "from_background_anchor": transition["from_background_anchor"],
        "to_background_anchor": transition["to_background_anchor"],
        "visual_theme": document["visual_theme"],
        "inputs": staged,
    }
    (transition_dir / "transition-inputs.json").write_text(
        json.dumps(inputs_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Staged {transition['transition_id']} inputs in {input_dir}")


if __name__ == "__main__":
    main()
