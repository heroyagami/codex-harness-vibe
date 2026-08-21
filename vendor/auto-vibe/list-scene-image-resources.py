import sys

from scene_plan import ScenePlanError, read_scene_plan


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: list-scene-image-resources.py <scene-plan.json>")

    try:
        scene_plan = read_scene_plan(sys.argv[1])
    except ScenePlanError as exc:
        sys.exit(str(exc))

    for scene in scene_plan:
        for resource in scene["image_resources"]:
            print(f"{scene['scene_id']}\t{resource['source']}\t{resource['target']}")


if __name__ == "__main__":
    main()
