from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


SEQUENCE_REVIEW_VERSION = "sequence-rhythm-v2"


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


def analyze_director_rhythm(scenes: list[dict]) -> dict:
    if not scenes:
        return {"problems": ["director plan contains no rhythm scenes"], "energy_curve": [], "density_curve": []}
    energies = [float(scene.get("energy", 0.5)) for scene in scenes]
    densities = [str(scene.get("density", "medium")) for scene in scenes]
    resets = [bool(scene.get("visual_reset", False)) for scene in scenes]
    grammars = [str(scene.get("grammar", "")) for scene in scenes]
    problems: list[str] = []

    if len(energies) >= 5 and max(energies) - min(energies) < 0.20:
        problems.append("energy curve is too flat across five or more scenes")

    high_run = 0
    max_high_run = 0
    for density in densities:
        high_run = high_run + 1 if density == "high" else 0
        max_high_run = max(max_high_run, high_run)
    if max_high_run >= 4:
        problems.append("four or more consecutive high-density scenes create sustained overload")

    reset_gap = 0
    max_reset_gap = 0
    for has_reset in resets:
        reset_gap = 0 if has_reset else reset_gap + 1
        max_reset_gap = max(max_reset_gap, reset_gap)
    if len(scenes) >= 7 and max_reset_gap >= 7:
        problems.append("seven or more scenes pass without a planned visual reset")

    grammar_run = 1
    max_grammar_run = 1
    for previous, current in zip(grammars, grammars[1:]):
        grammar_run = grammar_run + 1 if current and current == previous else 1
        max_grammar_run = max(max_grammar_run, grammar_run)
    if max_grammar_run >= 3:
        problems.append("the same visual grammar repeats for three or more consecutive scenes")

    return {
        "problems": problems,
        "energy_curve": [round(value, 3) for value in energies],
        "density_curve": densities,
        "visual_resets": resets,
        "grammar_curve": grammars,
        "energy_range": round(max(energies) - min(energies), 3),
        "max_high_density_run": max_high_run,
        "max_scenes_without_reset": max_reset_gap,
    }


def build_sequence_review(run_dir: Path) -> dict:
    plan = json.loads((run_dir / "scene-plan.json").read_text(encoding="utf-8"))
    director_path = run_dir / "director-plan.json"
    director = json.loads(director_path.read_text(encoding="utf-8")) if director_path.exists() else {"scenes": []}
    scene_count = len(plan["scenes"])
    rows: list[dict] = []
    tiles: list[tuple[str, Image.Image]] = []
    for index in range(1, scene_count + 1):
        scene_id = f"scene-{index:03d}"
        scene_dir = run_dir / "scenes" / scene_id
        video = scene_dir / f"{scene_id}.mov"
        middle = scene_dir / "artifacts" / "visual-gate" / "mid.png"
        state_path = scene_dir / "worker-state.json"
        motion_path = scene_dir / "artifacts" / "motion-gate" / "motion-gate.json"
        motion = json.loads(motion_path.read_text(encoding="utf-8")) if motion_path.exists() else {}
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"status": "not_started"}
        rows.append(
            {
                "scene_id": scene_id,
                "status": state.get("status", "unknown"),
                "video_ready": video.exists() and video.stat().st_size > 0,
                "midpoint_ready": middle.exists(),
                "motion_status": motion.get("status", "missing"),
                "max_idle_seconds": motion.get("max_idle_seconds"),
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
    motion_rejected = [row["scene_id"] for row in rows if row["motion_status"] != "accepted"]
    rhythm = analyze_director_rhythm(director.get("scenes", []))
    blocking_rhythm_problems = rhythm["problems"] if len(director.get("scenes", [])) >= 5 else []
    passed = (
        ready == scene_count
        and not repeated_runs
        and not critic_missing
        and not motion_rejected
        and not blocking_rhythm_problems
    )
    report = {
        "version": SEQUENCE_REVIEW_VERSION,
        "status": "pass" if passed else "rejected",
        "scene_count": scene_count,
        "rendered_count": ready,
        "missing_scenes": [row["scene_id"] for row in rows if not row["video_ready"]],
        "critic_missing": critic_missing,
        "motion_rejected": motion_rejected,
        "adjacent_midpoint_similarity": similarities,
        "repeated_silhouette_runs": repeated_runs,
        "rhythm": rhythm,
        "blocking_rhythm_problems": blocking_rhythm_problems,
        "scenes": rows,
        "contact_sheet": str(artifacts / "scene-midpoint-contact-sheet.jpg"),
        "fresh_eyes_gates": [
            "Every midpoint still makes the spoken idea easier to understand",
            "No primary copy is clipped or hidden by the subtitle reserve",
            "The sequence contains genuine visual resets rather than recolored templates",
            "Energy and density change with the argument instead of staying flat",
        ],
    }
    (artifacts / "sequence-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
