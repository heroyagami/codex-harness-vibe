import json
import re
import sys
from pathlib import Path, PurePosixPath


FPS = 30
WIDTH = 1080
HEIGHT = 1440
TRANSITION_TYPES = {"parallax", "custom", "hard_cut"}
VISUAL_THEMES = {
    "dark": {
        "source": "resources/backgrounds/darkbg.png",
        "target": "public/img/darkbg.png",
        "width": 1480,
        "height": 1840,
        "fallback_color": "#08090b",
    },
    "light": {
        "source": "resources/backgrounds/lightbg.png",
        "target": "public/img/lightbg.png",
        "width": 1480,
        "height": 1840,
        "fallback_color": "#eadeca",
    },
}
BACKGROUND_ANCHORS = (
    {"name": "top_left", "x": 0, "y": 0},
    {"name": "top_right", "x": 1, "y": 0},
    {"name": "bottom_right", "x": 1, "y": 1},
    {"name": "bottom_left", "x": 0, "y": 1},
)
ENTRY_HANDOFF = (
    "首帧完整呈现至少一个内容相关的清晰前景主体；该主体与共享纹理远景形成明确的前后层级，"
    "其他元素围绕它展开入场动画。"
)
EXIT_HANDOFF = (
    "末帧完整保留至少一个内容相关的清晰前景主体；主体与共享纹理远景形成明确层级，"
    "为相邻场景的独立转场提供清晰的出发状态。"
)


class ScenePlanError(ValueError):
    pass


def fail(message):
    raise ScenePlanError(message)


def pick(item, *keys):
    for key in keys:
        if key in item:
            return item[key]
    return None


def normalize_duration(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.fullmatch(r"\d+(?:\.\d{1,3})?", value):
        return None
    return value


def seconds_text_to_ms(value):
    normalized = normalize_duration(value)
    if normalized is None:
        return None
    whole, dot, fraction = normalized.partition(".")
    milliseconds = int(fraction.ljust(3, "0")) if dot else 0
    return int(whole) * 1000 + milliseconds


def format_ms_as_seconds(ms):
    return f"{ms / 1000:.3f}"


def timeline_ms_to_frame(ms, timeline_start_ms, fps=FPS):
    delta_ms = ms - timeline_start_ms
    if delta_ms < 0:
        fail("timeline frame conversion received a time before the timeline start")
    return (delta_ms * fps + 500) // 1000


def normalize_time_range(value):
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    start_ms = seconds_text_to_ms(value[0])
    end_ms = seconds_text_to_ms(value[1])
    if start_ms is None or end_ms is None or end_ms <= start_ms:
        return None
    return [format_ms_as_seconds(start_ms), format_ms_as_seconds(end_ms)]


def normalize_relative_posix_path(value):
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or any(char in text for char in ("\r", "\n", "\t")):
        return None
    path = PurePosixPath(text)
    if path.is_absolute():
        return None
    if not path.parts or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path.as_posix()


SRT_TIMESTAMP_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
SRT_TIME_LINE_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+" r"(\d{2}:\d{2}:\d{2},\d{3})(?:\s+.*)?"
)


def srt_timestamp_to_ms(value):
    match = SRT_TIMESTAMP_RE.fullmatch(value.strip())
    if not match:
        return None
    hours, minutes, seconds, milliseconds = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        return None
    return (((hours * 60) + minutes) * 60 + seconds) * 1000 + milliseconds


def parse_subtitle_cues(text, label, allow_index_lines=True):
    lines = str(text).replace("\ufeff", "", 1).splitlines()
    cues = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if allow_index_lines and line.isdigit() and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if SRT_TIME_LINE_RE.fullmatch(next_line):
                index += 1
                line = next_line
        match = SRT_TIME_LINE_RE.fullmatch(line)
        if not match:
            fail(f"{label}: unexpected text outside an SRT cue: {line}")

        start_ms = srt_timestamp_to_ms(match.group(1))
        end_ms = srt_timestamp_to_ms(match.group(2))
        if start_ms is None or end_ms is None or end_ms <= start_ms:
            fail(f"{label}: invalid SRT time line: {line}")
        index += 1
        content_lines = []
        while index < len(lines):
            candidate = lines[index].strip()
            if SRT_TIME_LINE_RE.fullmatch(candidate):
                break
            if (
                allow_index_lines
                and candidate.isdigit()
                and index + 1 < len(lines)
                and SRT_TIME_LINE_RE.fullmatch(lines[index + 1].strip())
            ):
                index += 1
                break
            content_lines.append(lines[index].strip())
            index += 1
        while content_lines and not content_lines[0]:
            content_lines.pop(0)
        while content_lines and not content_lines[-1]:
            content_lines.pop()
        content = "\n".join(content_lines)
        if not content:
            fail(f"{label}: SRT cue at {match.group(1)} has no text")
        cues.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "time_line": f"{match.group(1)} --> {match.group(2)}",
                "text": content,
            }
        )
    return cues


def validate_srt_timeline(plan_path, scenes, timeline_start_ms, timeline_end_ms):
    srt_path = plan_path.parent / "transcription.srt"
    if not srt_path.is_file():
        fail(f"{plan_path}: transcription.srt not found next to scene plan")
    original_cues = parse_subtitle_cues(
        srt_path.read_text(encoding="utf-8-sig"), str(srt_path)
    )
    if not original_cues:
        fail(f"{srt_path}: expected at least one subtitle cue")
    if original_cues[0]["start_ms"] != timeline_start_ms:
        fail(
            f"{plan_path}: first scene must start at first SRT cue "
            f"{format_ms_as_seconds(original_cues[0]['start_ms'])}"
        )
    if original_cues[-1]["end_ms"] != timeline_end_ms:
        fail(
            f"{plan_path}: last scene must end at last SRT cue "
            f"{format_ms_as_seconds(original_cues[-1]['end_ms'])}"
        )

    planned_cues = []
    for index, scene in enumerate(scenes, start=1):
        planned_cues.extend(
            parse_subtitle_cues(
                scene["subtitle_text"],
                f"{plan_path}: scenes[{index}].subtitle_text",
                allow_index_lines=False,
            )
        )

    def canonical(cue):
        return (cue["start_ms"], cue["end_ms"], cue["text"])

    if [canonical(cue) for cue in planned_cues] != [
        canonical(cue) for cue in original_cues
    ]:
        fail(
            f"{plan_path}: scene subtitle_text cues must reproduce transcription.srt exactly once "
            "in original order"
        )
    return original_cues


def cue_context_for_range(cues, start_ms, end_ms):
    lines = []
    for cue in cues:
        if cue["end_ms"] <= start_ms or cue["start_ms"] >= end_ms:
            continue
        lines.extend((cue["time_line"], cue["text"]))
    return "\n".join(lines) if lines else "该区间无字幕"


def normalize_image_resource(plan_path, scene_index, resource_index, item):
    if not isinstance(item, dict):
        fail(
            f"{plan_path}: scenes[{scene_index}].image_resources[{resource_index}] must be an object"
        )
    source = normalize_relative_posix_path(
        pick(item, "source", "from", "RESOURCE_SOURCE")
    )
    target = normalize_relative_posix_path(
        pick(item, "target", "to", "RESOURCE_TARGET")
    )
    missing = []
    if not source:
        missing.append("source")
    if not target:
        missing.append("target")
    if missing:
        fail(
            f"{plan_path}: scenes[{scene_index}].image_resources[{resource_index}] missing/invalid: "
            f"{', '.join(missing)}"
        )

    source_parts = PurePosixPath(source).parts
    if len(source_parts) < 2 or source_parts[0] != "resources":
        fail(
            f"{plan_path}: scenes[{scene_index}].image_resources[{resource_index}].source must stay under "
            "resources/"
        )

    target_parts = PurePosixPath(target).parts
    if len(target_parts) < 3 or target_parts[:2] != ("public", "img"):
        fail(
            f"{plan_path}: scenes[{scene_index}].image_resources[{resource_index}].target must stay under "
            "public/img/"
        )

    return {"source": source, "target": target}


def normalize_background_path(plan_path, field, value, root, min_parts):
    normalized = normalize_relative_posix_path(value)
    parts = PurePosixPath(normalized).parts if normalized else ()
    if len(parts) < min_parts or parts[0] != root:
        fail(f"{plan_path}: background.{field} must stay under {root}/")
    return normalized


def normalize_visual_theme(plan_path, value):
    if value not in VISUAL_THEMES:
        fail(f"{plan_path}: visual_theme must be light or dark")
    return value


def read_prompt_visual_theme(plan_path):
    prompt_path = plan_path.parent / "codex-prompt.md"
    if not prompt_path.is_file():
        return None
    lines = prompt_path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        fail(f"{prompt_path}: unclosed front matter")

    values = []
    for line in lines[1:closing_index]:
        key, separator, value = line.partition(":")
        if separator and key.strip() == "visual_theme":
            values.append(value.strip())
    if len(values) > 1:
        fail(f"{prompt_path}: visual_theme appears more than once in front matter")
    return values[0] if values else None


def resolve_visual_theme(plan_path, plan_value):
    prompt_value = read_prompt_visual_theme(plan_path)
    if plan_value is None:
        return normalize_visual_theme(plan_path, prompt_value)
    visual_theme = normalize_visual_theme(plan_path, plan_value)
    if prompt_value is not None:
        prompt_theme = normalize_visual_theme(plan_path, prompt_value)
        if visual_theme != prompt_theme:
            fail(
                f"{plan_path}: visual_theme {visual_theme!r} does not match "
                f"{plan_path.parent / 'codex-prompt.md'} front matter {prompt_theme!r}"
            )
    return visual_theme


def normalize_background(plan_path, item, visual_theme):
    expected = VISUAL_THEMES[visual_theme]
    if item is None:
        item = expected
    elif not isinstance(item, dict):
        fail(f"{plan_path}: background must be an object")

    source = normalize_background_path(
        plan_path, "source", item.get("source"), "resources", 2
    )
    target = normalize_relative_posix_path(item.get("target"))
    target_parts = PurePosixPath(target).parts if target else ()
    if len(target_parts) < 3 or target_parts[:2] != ("public", "img"):
        fail(f"{plan_path}: background.target must stay under public/img/")

    source_suffix = PurePosixPath(source).suffix.lower()
    target_suffix = PurePosixPath(target).suffix.lower()
    if source_suffix != ".png" or target_suffix != ".png":
        fail(f"{plan_path}: background.source and background.target must be PNG paths")

    width = item.get("width")
    height = item.get("height")
    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or width <= WIDTH
        or width > 16384
    ):
        fail(
            f"{plan_path}: background.width must be an integer from {WIDTH + 1} to 16384"
        )
    if (
        isinstance(height, bool)
        or not isinstance(height, int)
        or height <= HEIGHT
        or height > 16384
    ):
        fail(
            f"{plan_path}: background.height must be an integer from {HEIGHT + 1} to 16384"
        )

    source_path = plan_path.parent / source
    if not source_path.is_file():
        fail(f"{plan_path}: shared background not found: {source_path}")
    with source_path.open("rb") as file:
        header = file.read(24)
    if (
        len(header) < 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[12:16] != b"IHDR"
    ):
        fail(f"{plan_path}: background.source must be a readable PNG")
    actual_width = int.from_bytes(header[16:20], "big")
    actual_height = int.from_bytes(header[20:24], "big")
    if (actual_width, actual_height) != (width, height):
        fail(
            f"{plan_path}: background dimensions are {actual_width}x{actual_height}, "
            f"expected {width}x{height}"
        )

    background = {
        "source": source,
        "target": target,
        "width": width,
        "height": height,
    }
    for field in ("source", "target", "width", "height"):
        if background[field] != expected[field]:
            fail(
                f"{plan_path}: {visual_theme} visual_theme requires "
                f"background.{field}={expected[field]!r}"
            )
    background["fallback_color"] = expected["fallback_color"]
    return background


def normalize_scene_plan_item(plan_path, index, item, background):
    if not isinstance(item, dict):
        fail(f"{plan_path}: scenes[{index}] must be an object")
    if "background" in item:
        fail(f"{plan_path}: define the shared background once at top-level background")

    time_range_seconds = normalize_time_range(item.get("time_range_seconds"))
    subtitle_text = item.get("subtitle_text")
    research_brief = item.get("research_brief")

    missing = []
    if not time_range_seconds:
        missing.append("time_range_seconds")
    if subtitle_text is None:
        missing.append("subtitle_text")
    if research_brief is None or not str(research_brief).strip():
        missing.append("research_brief")
    if missing:
        fail(f"{plan_path}: scenes[{index}] missing/invalid: {', '.join(missing)}")
    scene_id = item.get("scene_id")
    expected_scene_id = f"scene-{index:03d}"
    if scene_id and scene_id != expected_scene_id:
        fail(
            f"{plan_path}: scenes[{index}] scene_id must be {expected_scene_id}, got {scene_id}"
        )
    output_file = item.get("output_file")
    expected_output_file = f"{expected_scene_id}.mov"
    if output_file and output_file != expected_output_file:
        fail(
            f"{plan_path}: scenes[{index}] output_file must be {expected_output_file}, got {output_file}"
        )

    raw_image_resources = item.get("image_resources", [])
    if not isinstance(raw_image_resources, list):
        fail(f"{plan_path}: scenes[{index}].image_resources must be a list")

    image_resources = [{"source": background["source"], "target": background["target"]}]
    seen_targets = {background["target"]}
    for resource_index, resource in enumerate(raw_image_resources, start=1):
        normalized = normalize_image_resource(
            plan_path, index, resource_index, resource
        )
        if normalized["target"] in seen_targets:
            fail(
                f"{plan_path}: scenes[{index}].image_resources has duplicate target {normalized['target']}"
            )
        seen_targets.add(normalized["target"])
        image_resources.append(normalized)

    return {
        "scene_id": expected_scene_id,
        "output_file": expected_output_file,
        "time_range_seconds": time_range_seconds,
        "subtitle_text": str(subtitle_text).strip(),
        "research_brief": str(research_brief).strip(),
        "background": background,
        "background_anchor": dict(
            BACKGROUND_ANCHORS[(index - 1) % len(BACKGROUND_ANCHORS)]
        ),
        "image_resources": image_resources,
    }


def normalize_transition(plan_path, index, item, scenes, timeline_start_ms):
    if not isinstance(item, dict):
        fail(f"{plan_path}: transitions[{index}] must be an object")

    transition_type = item.get("type")
    if transition_type not in TRANSITION_TYPES:
        fail(
            f"{plan_path}: transitions[{index}].type must be parallax, custom, or hard_cut"
        )
    reason = item.get("reason")
    if reason is None or not str(reason).strip() or len(str(reason).strip()) > 300:
        fail(
            f"{plan_path}: transitions[{index}].reason must contain 1 to 300 characters"
        )
    reason = str(reason).strip()

    transition_id = f"transition-{index:03d}"
    supplied_id = item.get("transition_id")
    if supplied_id and supplied_id != transition_id:
        fail(
            f"{plan_path}: transitions[{index}] transition_id must be {transition_id}, got {supplied_id}"
        )
    from_scene = scenes[index - 1]
    to_scene = scenes[index]
    boundary_ms = seconds_text_to_ms(from_scene["time_range_seconds"][1])

    base = {
        "transition_id": transition_id,
        "type": transition_type,
        "reason": reason,
        "from_scene_id": from_scene["scene_id"],
        "to_scene_id": to_scene["scene_id"],
        "from_background_anchor": from_scene["background_anchor"],
        "to_background_anchor": to_scene["background_anchor"],
        "cut_time_seconds": format_ms_as_seconds(boundary_ms),
    }

    if transition_type == "hard_cut":
        return base

    time_range_seconds = normalize_time_range(item.get("time_range_seconds"))
    if not time_range_seconds:
        fail(
            f"{plan_path}: transitions[{index}].time_range_seconds is required for rendered transitions"
        )
    start_ms, end_ms = (seconds_text_to_ms(value) for value in time_range_seconds)
    if not start_ms < boundary_ms < end_ms:
        fail(
            f"{plan_path}: transitions[{index}].time_range_seconds must straddle scene boundary "
            f"{format_ms_as_seconds(boundary_ms)}"
        )

    start_frame = timeline_ms_to_frame(start_ms, timeline_start_ms)
    boundary_frame = timeline_ms_to_frame(boundary_ms, timeline_start_ms)
    end_frame = timeline_ms_to_frame(end_ms, timeline_start_ms)
    if not start_frame < boundary_frame < end_frame:
        fail(
            f"{plan_path}: transitions[{index}] must include at least one 30fps frame on each side "
            "of its scene boundary"
        )

    expected_output_file = f"{transition_id}.mov"
    supplied_output = item.get("output_file")
    if supplied_output and supplied_output != expected_output_file:
        fail(
            f"{plan_path}: transitions[{index}] output_file must be {expected_output_file}, got {supplied_output}"
        )
    return {
        **base,
        "output_file": expected_output_file,
        "time_range_seconds": time_range_seconds,
        "frame_range": [start_frame, end_frame],
        "duration_seconds": format_ms_as_seconds(end_ms - start_ms),
        "duration_in_frames": end_frame - start_frame,
    }


def apply_render_ranges(plan_path, scenes, transitions, timeline_start_ms):
    for index, scene in enumerate(scenes):
        semantic_start_ms, semantic_end_ms = (
            seconds_text_to_ms(value) for value in scene["time_range_seconds"]
        )
        render_start_ms = semantic_start_ms
        render_end_ms = semantic_end_ms
        boundary_contract = {}

        if index > 0 and transitions[index - 1]["type"] != "hard_cut":
            render_start_ms = seconds_text_to_ms(
                transitions[index - 1]["time_range_seconds"][1]
            )
            boundary_contract["entry"] = ENTRY_HANDOFF
        if index < len(transitions) and transitions[index]["type"] != "hard_cut":
            render_end_ms = seconds_text_to_ms(
                transitions[index]["time_range_seconds"][0]
            )
            boundary_contract["exit"] = EXIT_HANDOFF

        render_start_frame = timeline_ms_to_frame(render_start_ms, timeline_start_ms)
        render_end_frame = timeline_ms_to_frame(render_end_ms, timeline_start_ms)
        if render_end_ms <= render_start_ms or render_end_frame <= render_start_frame:
            fail(
                f"{plan_path}: transitions leave {scene['scene_id']} without a positive 30fps render range"
            )

        scene["render_range_seconds"] = [
            format_ms_as_seconds(render_start_ms),
            format_ms_as_seconds(render_end_ms),
        ]
        scene["frame_range"] = [render_start_frame, render_end_frame]
        scene["duration"] = format_ms_as_seconds(render_end_ms - render_start_ms)
        scene["duration_in_frames"] = render_end_frame - render_start_frame
        scene["boundary_contract"] = boundary_contract


def build_timeline_segments(plan_path, scenes, transitions, total_duration_frames):
    segments = []
    for index, scene in enumerate(scenes):
        segments.append(
            {
                "kind": "scene",
                "id": scene["scene_id"],
                "output_file": scene["output_file"],
                "time_range_seconds": scene["render_range_seconds"],
                "frame_range": scene["frame_range"],
                "duration_in_frames": scene["duration_in_frames"],
            }
        )
        if index < len(transitions) and transitions[index]["type"] != "hard_cut":
            transition = transitions[index]
            segments.append(
                {
                    "kind": "transition",
                    "id": transition["transition_id"],
                    "output_file": transition["output_file"],
                    "time_range_seconds": transition["time_range_seconds"],
                    "frame_range": transition["frame_range"],
                    "duration_in_frames": transition["duration_in_frames"],
                }
            )

    expected_start = 0
    for segment in segments:
        start_frame, end_frame = segment["frame_range"]
        if start_frame != expected_start:
            fail(
                f"{plan_path}: timeline has a frame gap or overlap before {segment['id']}"
            )
        expected_start = end_frame
    if expected_start != total_duration_frames:
        fail(
            f"{plan_path}: timeline covers {expected_start} frames, expected {total_duration_frames}"
        )
    return segments


def read_scene_plan_document(path):
    plan_path = Path(path).resolve()
    if not plan_path.is_file():
        fail(f"Scene plan not found: {plan_path}")

    try:
        with plan_path.open(encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        fail(f"{plan_path}: invalid JSON: {exc}")

    if not isinstance(data, dict):
        fail(f"{plan_path}: expected an object with scenes and transitions")
    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        fail(f"{plan_path}: expected non-empty scenes list")

    raw_fps = data.get("fps", FPS)
    if isinstance(raw_fps, bool) or not isinstance(raw_fps, int) or raw_fps != FPS:
        fail(f"{plan_path}: fps must be {FPS}")

    visual_theme = resolve_visual_theme(plan_path, data.get("visual_theme"))
    background = normalize_background(plan_path, data.get("background"), visual_theme)
    scenes = [
        normalize_scene_plan_item(plan_path, index, item, background)
        for index, item in enumerate(raw_scenes, start=1)
    ]
    for scene in scenes:
        scene["visual_theme"] = visual_theme
    previous_end_ms = None
    for index, item in enumerate(scenes, start=1):
        start_ms, end_ms = (
            seconds_text_to_ms(value) for value in item["time_range_seconds"]
        )
        if previous_end_ms is not None and start_ms != previous_end_ms:
            fail(
                f"{plan_path}: scenes[{index}] time_range_seconds must start at "
                f"{format_ms_as_seconds(previous_end_ms)}"
            )
        previous_end_ms = end_ms

    timeline_start_ms = seconds_text_to_ms(scenes[0]["time_range_seconds"][0])
    timeline_end_ms = seconds_text_to_ms(scenes[-1]["time_range_seconds"][1])
    actual_total_ms = timeline_end_ms - timeline_start_ms
    srt_cues = validate_srt_timeline(
        plan_path, scenes, timeline_start_ms, timeline_end_ms
    )
    expected_total = normalize_duration(data.get("total_duration_seconds"))
    if not expected_total:
        fail(f"{plan_path}: total_duration_seconds is required")
    expected_total_ms = seconds_text_to_ms(expected_total)
    if actual_total_ms != expected_total_ms:
        fail(
            f"{plan_path}: scene coverage {format_ms_as_seconds(actual_total_ms)}s does not match "
            f"total_duration_seconds {format_ms_as_seconds(expected_total_ms)}s"
        )

    raw_transitions = data.get("transitions")
    if not isinstance(raw_transitions, list):
        fail(
            f"{plan_path}: transitions must be a list with one item per scene boundary"
        )
    expected_transition_count = len(scenes) - 1
    if len(raw_transitions) != expected_transition_count:
        fail(
            f"{plan_path}: transitions must contain {expected_transition_count} item(s), got "
            f"{len(raw_transitions)}"
        )
    transitions = [
        normalize_transition(plan_path, index, item, scenes, timeline_start_ms)
        for index, item in enumerate(raw_transitions, start=1)
    ]
    for transition in transitions:
        if transition["type"] == "hard_cut":
            continue
        transition_start_ms, transition_end_ms = (
            seconds_text_to_ms(value) for value in transition["time_range_seconds"]
        )
        transition["subtitle_context"] = cue_context_for_range(
            srt_cues, transition_start_ms, transition_end_ms
        )

    apply_render_ranges(plan_path, scenes, transitions, timeline_start_ms)
    total_duration_frames = timeline_ms_to_frame(timeline_end_ms, timeline_start_ms)
    timeline_segments = build_timeline_segments(
        plan_path, scenes, transitions, total_duration_frames
    )

    return {
        "fps": FPS,
        "visual_theme": visual_theme,
        "timeline_start_seconds": format_ms_as_seconds(timeline_start_ms),
        "timeline_end_seconds": format_ms_as_seconds(timeline_end_ms),
        "total_duration_seconds": format_ms_as_seconds(actual_total_ms),
        "total_duration_frames": total_duration_frames,
        "background": background,
        "scenes": scenes,
        "transitions": transitions,
        "timeline_segments": timeline_segments,
    }


def read_scene_plan(path):
    return read_scene_plan_document(path)["scenes"]


def print_timeline(document):
    print(
        f"Timeline: {document['total_duration_seconds']}s, "
        f"{document['total_duration_frames']} frames at {document['fps']}fps"
    )
    for segment in document["timeline_segments"]:
        start, end = segment["time_range_seconds"]
        print(
            f"- {segment['id']}: {segment['kind']} {start} -> {end}, "
            f"{segment['duration_in_frames']} frames"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: scene_plan.py <scene-plan.json>")
    try:
        print_timeline(read_scene_plan_document(sys.argv[1]))
    except ScenePlanError as exc:
        sys.exit(str(exc))
