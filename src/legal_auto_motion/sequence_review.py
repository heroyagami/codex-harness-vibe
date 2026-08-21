from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


def _similarity(left: Image.Image, right: Image.Image) -> float:
    a = left.convert("L").resize((64, 64))
    b = right.convert("L").resize((64, 64))
    mean_difference = ImageStat.Stat(ImageChops.difference(a, b)).mean[0]
    return max(0.0, 1.0 - mean_difference / 255.0)


def _foreground_mask(frame: Image.Image, background: Image.Image) -> Image.Image:
    sized = background.convert("RGB").resize(frame.size)
    difference = ImageChops.difference(frame.convert("RGB"), sized).convert("L").resize((64, 64))
    return difference.point(lambda value: 255 if value > 24 else 0)


def _silhouette_similarity(left: Image.Image, right: Image.Image, background: Image.Image) -> float:
    return _similarity(_foreground_mask(left, background), _foreground_mask(right, background))


def build_sequence_review(run_dir: Path) -> dict:
    plan = json.loads((run_dir / "scene-plan.json").read_text(encoding="utf-8"))
    scene_count = len(plan["scenes"])
    rows: list[dict] = []
    tiles: list[tuple[str, Image.Image]] = []
    for index in range(1, scene_count + 1):
        scene_id = f"scene-{index:03d}"
        scene_dir = run_dir / "scenes" / scene_id
        video = scene_dir / f"{scene_id}.mov"
        middle = scene_dir / "artifacts" / "visual-gate" / "mid.png"
        state_path = scene_dir / "worker-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"status": "not_started"}
        rows.append(
            {
                "scene_id": scene_id,
                "status": state.get("status", "unknown"),
                "video_ready": video.exists() and video.stat().st_size > 0,
                "midpoint_ready": middle.exists(),
            }
        )
        if middle.exists():
            tiles.append((scene_id, Image.open(middle).convert("RGB")))

    artifacts = run_dir / "reports"
    artifacts.mkdir(parents=True, exist_ok=True)
    if tiles:
        tile_width, tile_height, columns = 270, 380, 4
        rows_count = (len(tiles) + columns - 1) // columns
        sheet = Image.new("RGB", (tile_width * columns, tile_height * rows_count), "#101114")
        draw = ImageDraw.Draw(sheet)
        for position, (scene_id, frame) in enumerate(tiles):
            x = (position % columns) * tile_width
            y = (position // columns) * tile_height
            frame.thumbnail((tile_width, 360), Image.Resampling.LANCZOS)
            sheet.paste(frame, (x + (tile_width - frame.width) // 2, y))
            draw.text((x + 8, y + 360), scene_id, fill="white")
        sheet.save(artifacts / "scene-midpoint-contact-sheet.jpg", quality=92)

    ready = sum(1 for row in rows if row["video_ready"])
    similarities = []
    background_path = run_dir / "resources" / "backgrounds" / "darkbg.png"
    background = Image.open(background_path).convert("RGB") if background_path.exists() else None
    for (left_id, left), (right_id, right) in zip(tiles, tiles[1:]):
        similarity = _silhouette_similarity(left, right, background) if background is not None else _similarity(left, right)
        similarities.append({"left": left_id, "right": right_id, "similarity": round(similarity, 4)})
    repeated_runs = []
    for first, second in zip(similarities, similarities[1:]):
        if first["similarity"] >= 0.94 and second["similarity"] >= 0.94:
            repeated_runs.append([first["left"], first["right"], second["right"]])
    critic_missing = []
    for row in rows:
        critique = run_dir / "scenes" / row["scene_id"] / "artifacts" / "creative-critique.json"
        if not critique.exists() or json.loads(critique.read_text(encoding="utf-8")).get("verdict") != "pass":
            critic_missing.append(row["scene_id"])
    passed = ready == scene_count and not repeated_runs and not critic_missing
    report = {
        "status": "pass" if passed else "rejected",
        "scene_count": scene_count,
        "rendered_count": ready,
        "missing_scenes": [row["scene_id"] for row in rows if not row["video_ready"]],
        "critic_missing": critic_missing,
        "adjacent_midpoint_similarity": similarities,
        "repeated_silhouette_runs": repeated_runs,
        "scenes": rows,
        "contact_sheet": str(artifacts / "scene-midpoint-contact-sheet.jpg"),
        "fresh_eyes_gates": [
            "Every midpoint still makes the spoken idea easier to understand",
            "No primary copy is clipped or hidden by the subtitle reserve",
            "The sequence contains genuine visual resets rather than recolored templates",
        ],
    }
    (artifacts / "sequence-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
