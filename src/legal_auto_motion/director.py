from __future__ import annotations

import json
import re
from pathlib import Path

from .pipeline import _run_role, write_json
from .config import HarnessConfig, config_for_run
from .state import StateGraph, input_hash
from .srt import Cue, parse_srt


DIRECTOR_PROMPT_VERSION = "semantic-director-v3-rhythm"
DIRECTOR_SCHEMA_VERSION = "director-schema-v3"
GRAMMARS = (
    "object_demo, relationship_diagram, timeline, process_flow, comparison, "
    "document_evidence, number_event, interface_simulation, kinetic_phrase, visual_rest"
)
DENSITIES = ("low", "medium", "high")
CONTRAST_LEVELS = ("soft", "medium", "strong")
TRANSITION_INTENTS = ("hard_cut", "carry", "flow", "temporal", "contrast", "settle")

DIRECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "cue_start": {"type": "integer"},
                    "cue_end": {"type": "integer"},
                    "meaning": {"type": "string"},
                    "visual_goal": {"type": "string"},
                    "grammar": {"type": "string"},
                    "section": {"type": "string"},
                    "on_screen_copy": {"type": "array", "items": {"type": "string"}},
                    "subject": {"type": "string"},
                    "energy": {"type": "number", "minimum": 0, "maximum": 1},
                    "density": {"type": "string", "enum": list(DENSITIES)},
                    "visual_reset": {"type": "boolean"},
                    "contrast_with_previous": {"type": "string", "enum": list(CONTRAST_LEVELS)},
                    "transition_intent": {"type": "string", "enum": list(TRANSITION_INTENTS)},
                },
                "required": [
                    "cue_start", "cue_end", "meaning", "visual_goal", "grammar", "section",
                    "on_screen_copy", "subject", "energy", "density", "visual_reset",
                    "contrast_with_previous", "transition_intent",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["scenes"],
    "additionalProperties": False,
}


def _director_prompt(cues: list[Cue]) -> str:
    transcript = "\n".join(f"[{cue.index}] {cue.timing} {cue.text}" for cue in cues)
    return f"""你是法律科普短视频的语义导演与视觉节奏导演，只负责理解、拆镜和确定视觉节奏，不写Remotion代码。

读取下面完整SRT，按含义变化拆成语义镜头。观众容易看懂是第一优先级，同时要让整片存在明显的视觉强弱、留白和重置，而不是机械轮换模板。

要求：
- 每条字幕必须且只能归入一个镜头，cue范围连续，不遗漏、不重叠。
- 一镜头一个视觉命题；通常2.5到6秒，必要时可更长但必须有内部节拍。
- 不编造人物、日期、金额、责任比例、案号或裁判结论。
- on_screen_copy只放字幕中逐字存在的必要短语，尽量短。
- visual_goal说明观众应该看到什么，不得写“展示文字/套模板”。
- subject写本镜头唯一的视觉主体，例如“付款关系”“合同证据”“争议金额”，不要写空泛的“画面”。
- grammar从以下选择，连续镜头尽量不重复：{GRAMMARS}。
- section用于论证章节分组，例如hook/facts/conflict/rule/evidence/conclusion。
- energy为0到1，表示镜头视觉能量；高潮、反转、关键结论更高，解释与留白更低。不要让所有镜头都处于同一能量带。
- density从low/medium/high选择，表示画面信息密度。连续高密度镜头后应主动安排低密度或visual_rest。
- visual_reset表示该镜头是否应明显改变主体位置、构图、尺度或视觉语法，让观众重新获得注意力。
- contrast_with_previous从soft/medium/strong选择。第一镜头用strong。
- transition_intent从{', '.join(TRANSITION_INTENTS)}选择。默认优先hard_cut；只有语义连续且确有叙事理由时才选carry/flow/temporal/settle。观点反转或强对比选contrast。
- 不要为了“多样性”机械轮换语法；语法必须服务本段含义。

只返回下面结构的JSON，不要写文件，不要解释，不要提问。遇到取舍自行做最有利于观众理解和整片节奏的决定：
{{
  "scenes": [
    {{
      "cue_start": 1,
      "cue_end": 2,
      "meaning": "本段真正表达的意思",
      "visual_goal": "观众一眼能理解的具体画面变化",
      "grammar": "object_demo",
      "section": "hook",
      "on_screen_copy": ["字幕原文短语"],
      "subject": "本镜头视觉主体",
      "energy": 0.85,
      "density": "medium",
      "visual_reset": true,
      "contrast_with_previous": "strong",
      "transition_intent": "hard_cut"
    }}
  ]
}}

完整SRT：
{transcript}
"""


def director_fingerprint(run_dir: Path, config: HarnessConfig | None = None) -> str:
    config = config or config_for_run(run_dir)
    route = config.route("director")
    return input_hash(
        [run_dir / "transcription.srt"],
        [
            route.provider,
            route.model,
            route.fallback_model,
            DIRECTOR_PROMPT_VERSION,
            DIRECTOR_SCHEMA_VERSION,
            GRAMMARS,
            ",".join(TRANSITION_INTENTS),
        ],
    )


def extract_json_object(output: str) -> dict:
    """Extract the first complete JSON object from plain or decorated model output."""
    stripped = output.strip()
    candidates = [stripped]
    candidates.extend(match.group(1).strip() for match in re.finditer(r"```(?:json)?\s*(.*?)```", output, re.DOTALL | re.IGNORECASE))
    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                structured = value.get("structured_output")
                if isinstance(structured, dict):
                    return structured
                result = value.get("result")
                if isinstance(result, str) and result.strip() != candidate:
                    try:
                        return extract_json_object(result)
                    except ValueError:
                        pass
                if "scenes" in value:
                    return value
        except json.JSONDecodeError:
            pass
        for index, character in enumerate(candidate):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                structured = value.get("structured_output")
                if isinstance(structured, dict):
                    return structured
                if "scenes" in value:
                    return value
    raise ValueError("Director returned no valid JSON object")


def validate_and_normalize_director(raw: dict, cues: list[Cue]) -> dict:
    source = raw.get("scenes")
    if not isinstance(source, list) or not source:
        raise ValueError("Director plan must contain non-empty scenes")
    cue_by_index = {cue.index: cue for cue in cues}
    expected = cues[0].index
    normalized = []
    used_grammars: set[str] = set()
    allowed_grammars = {value.strip() for value in GRAMMARS.split(",")}
    for position, scene in enumerate(source, start=1):
        start_index, end_index = int(scene["cue_start"]), int(scene["cue_end"])
        if start_index != expected or end_index < start_index:
            raise ValueError(f"Scene {position} has non-contiguous cue range {start_index}..{end_index}; expected {expected}")
        if start_index not in cue_by_index or end_index not in cue_by_index:
            raise ValueError(f"Scene {position} references unknown cues")
        grammar = str(scene.get("grammar", "")).strip()
        if grammar not in allowed_grammars:
            raise ValueError(f"Scene {position} has unsupported grammar: {grammar}")
        meaning = str(scene.get("meaning", "")).strip()
        visual_goal = str(scene.get("visual_goal", "")).strip()
        subject = str(scene.get("subject", meaning)).strip()
        if not meaning or not visual_goal or not subject or visual_goal in {"展示文字", "套模板"}:
            raise ValueError(f"Scene {position} lacks semantic meaning, subject or a concrete visual goal")
        on_screen_copy = [str(value).strip() for value in scene.get("on_screen_copy", []) if str(value).strip()]
        spoken = "".join(cue_by_index[index].text for index in range(start_index, end_index + 1))
        unsupported = [value for value in on_screen_copy if value not in spoken]
        if unsupported:
            raise ValueError(f"Scene {position} has on-screen copy not found in its subtitles: {unsupported}")
        try:
            energy = float(scene.get("energy", 0.5))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Scene {position} has invalid energy") from exc
        if not 0 <= energy <= 1:
            raise ValueError(f"Scene {position} energy must be between 0 and 1")
        density = str(scene.get("density", "medium")).strip()
        contrast = str(scene.get("contrast_with_previous", "medium")).strip()
        transition_intent = str(scene.get("transition_intent", "hard_cut")).strip()
        if density not in DENSITIES:
            raise ValueError(f"Scene {position} has unsupported density: {density}")
        if contrast not in CONTRAST_LEVELS:
            raise ValueError(f"Scene {position} has unsupported contrast: {contrast}")
        if transition_intent not in TRANSITION_INTENTS:
            raise ValueError(f"Scene {position} has unsupported transition intent: {transition_intent}")
        normalized.append(
            {
                "start": cue_by_index[start_index].start,
                "end": cue_by_index[end_index].end,
                "cue_start": start_index,
                "cue_end": end_index,
                "meaning": meaning,
                "visual_goal": visual_goal,
                "grammar": grammar,
                "section": str(scene.get("section", "body")),
                "on_screen_copy": on_screen_copy,
                "subject": subject,
                "energy": round(energy, 3),
                "density": density,
                "visual_reset": bool(scene.get("visual_reset", False)),
                "contrast_with_previous": "strong" if position == 1 else contrast,
                "transition_intent": transition_intent,
            }
        )
        used_grammars.add(grammar)
        expected = end_index + 1
    if expected != cues[-1].index + 1:
        raise ValueError(f"Director plan stops at cue {expected - 1}, expected {cues[-1].index}")
    for first, second, third in zip(normalized, normalized[1:], normalized[2:]):
        if first["grammar"] == second["grammar"] == third["grammar"]:
            raise ValueError(f"Director plan repeats grammar three times: {first['grammar']}")
    duration = cues[-1].end - cues[0].start
    minimum_grammars = 5 if duration > 90 else (4 if len(cues) >= 20 else 1)
    if len(used_grammars) < minimum_grammars:
        raise ValueError("Director plan lacks visual grammar diversity")
    first_minute_grammars = {scene["grammar"] for scene in normalized if scene["start"] < cues[0].start + 60}
    if duration >= 60 and len(first_minute_grammars) < 3:
        raise ValueError("Director plan needs at least three visual grammars in the first minute")
    high_density_run = 0
    for scene in normalized:
        high_density_run = high_density_run + 1 if scene["density"] == "high" else 0
        if high_density_run >= 4 and not scene["visual_reset"]:
            raise ValueError("Director plan contains four high-density scenes without a visual reset")
    return {
        "version": DIRECTOR_SCHEMA_VERSION,
        "prompt_version": DIRECTOR_PROMPT_VERSION,
        "scenes": normalized,
        "grammar_count": len(used_grammars),
    }


def direct(run_dir: Path, *, timeout: int = 900) -> dict:
    cues = parse_srt(run_dir / "transcription.srt")
    output = run_dir / "director-plan.json"
    output.unlink(missing_ok=True)
    prompt = _director_prompt(cues)
    last_error: Exception | None = None
    normalized: dict | None = None
    config = config_for_run(run_dir)
    graph = StateGraph(run_dir / "harness-state.json")
    for attempt in range(2):
        if attempt:
            prompt += (
                "\n\n上次输出未通过自动校验："
                f"{last_error}。立即重新输出完整、合法且满足全部约束的JSON；不得解释或提问。"
            )
        try:
            response = _run_role(
                run_dir, prompt, timeout, json_schema=DIRECTOR_SCHEMA,
                config=config, role="director", state_graph=graph,
            )
            raw = extract_json_object(response)
            normalized = validate_and_normalize_director(raw, cues)
            break
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            last_error = exc
    if normalized is None:
        raise RuntimeError(f"Director failed structured output after 2 attempts: {last_error}")
    write_json(output, normalized)
    graph.complete(
        "directed",
        director_fingerprint(run_dir, config),
        outputs=[output],
        metadata={
            "provider": config.route("director").provider,
            "model": config.route("director").model,
            "prompt_version": DIRECTOR_PROMPT_VERSION,
            "schema_version": DIRECTOR_SCHEMA_VERSION,
        },
    )
    return normalized
