from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .facts import write_audit
from .config import HarnessConfig, ModelRoute, config_for_run
from .providers import claude_command, codex_command, codex_text_command, is_retryable_model_failure, read_manual_critique
from .srt import parse_srt
from .state import StateGraph, file_hash, input_hash
from .timing import write_timing_audit
from .visual_gate import inspect_render


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "auto-vibe"
CRITIC_PROMPT_VERSION = "direct-three-frame-rubric-v2"


class WorkerQuotaExceeded(RuntimeError):
    """The external scene worker is temporarily unavailable due to quota."""


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    media_bin = Path.home() / "bin"
    if media_bin.exists():
        env["PATH"] = f"{media_bin}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(command, cwd=cwd, check=check, text=True, env=env)


def init_run(run_dir: Path, srt: Path, audio: Path, config_path: Path | None = None) -> None:
    if run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")
    shutil.copytree(
        VENDOR,
        run_dir,
        ignore=shutil.ignore_patterns("node_modules", "scenes", "transitions", "*.mov", "*.mp4"),
    )
    shutil.copy2(srt, run_dir / "transcription.srt")
    shutil.copy2(audio, run_dir / f"narration{audio.suffix.lower()}")
    source_config = config_path or (ROOT / "harness.toml")
    if source_config.exists():
        shutil.copy2(source_config, run_dir / "harness.toml")
    write_json(
        run_dir / "run-state.json",
        {"status": "initialized", "srt": "transcription.srt", "audio": f"narration{audio.suffix.lower()}"},
    )
    graph = StateGraph(run_dir / "harness-state.json")
    fingerprint = input_hash([run_dir / "transcription.srt", run_dir / f"narration{audio.suffix.lower()}", run_dir / "harness.toml"])
    graph.complete("initialized", fingerprint, outputs=[run_dir / "transcription.srt", run_dir / f"narration{audio.suffix.lower()}"])


def reset_directed_outputs(run_dir: Path) -> None:
    """Discard only generated artifacts downstream of semantic direction."""
    for name in ("scenes", "transitions", "reports"):
        target = run_dir / name
        if target.exists():
            shutil.rmtree(target)
    for name in (
        "director-plan.json", "scene-plan.json", "fact-contracts.json",
        "scene-production-results.json", "transition-production-results.json",
        "assembled-visual.mov", "final.mp4", "completion-report.json",
    ):
        (run_dir / name).unlink(missing_ok=True)
    StateGraph(run_dir / "harness-state.json").invalidate_from("directed")
    state_path = run_dir / "run-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "initialized"
    write_json(state_path, state)


def sync_run_inputs(run_dir: Path, srt: Path, audio: Path) -> bool:
    destinations = [run_dir / "transcription.srt", run_dir / f"narration{audio.suffix.lower()}"]
    sources = [srt, audio]
    changed = any(not destination.exists() or file_hash(source) != file_hash(destination) for source, destination in zip(sources, destinations))
    if not changed:
        return False
    reset_directed_outputs(run_dir)
    for existing in run_dir.glob("narration.*"):
        existing.unlink(missing_ok=True)
    shutil.copy2(srt, destinations[0])
    shutil.copy2(audio, destinations[1])
    state_path = run_dir / "run-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update({"srt": "transcription.srt", "audio": destinations[1].name})
    write_json(state_path, state)
    config_path = run_dir / "harness.toml"
    StateGraph(run_dir / "harness-state.json").complete(
        "initialized", input_hash(destinations + ([config_path] if config_path.exists() else [])), outputs=destinations,
    )
    return True


def build_from_director(run_dir: Path, director_plan: Path) -> tuple[dict, dict]:
    cues = parse_srt(run_dir / "transcription.srt")
    director = json.loads(director_plan.read_text(encoding="utf-8"))
    source_scenes = director.get("scenes", [])
    if not source_scenes:
        raise ValueError("Director plan has no scenes")
    scenes: list[dict] = []
    contracts: dict[str, dict] = {}
    for index, source in enumerate(source_scenes, start=1):
        scene_id = f"scene-{index:03d}"
        start, end = float(source["start"]), float(source["end"])
        assigned = [cue for cue in cues if cue.start >= start - 0.002 and cue.end <= end + 0.002]
        if not assigned:
            raise ValueError(f"{scene_id} contains no SRT cues")
        narration = " ".join(cue.text for cue in assigned)
        approved = [str(value) for value in source.get("on_screen_copy", [])]
        scenes.append(
            {
                "time_range_seconds": [f"{start:.3f}", f"{end:.3f}"],
                "subtitle_text": "\n".join(cue.block for cue in assigned),
                "research_brief": f"本段含义：{source.get('meaning', narration)}。事实、金额、日期和结论严格以字幕为准。",
                "image_resources": [],
            }
        )
        contracts[scene_id] = {
            "scene_id": scene_id,
            "narration": narration,
            "approved_copy": approved,
            "meaning": source.get("meaning", ""),
            "visual_goal": source.get("visual_goal", ""),
        }
    transitions = []
    hard_boundaries = {
        index
        for index, (left, right) in enumerate(zip(source_scenes, source_scenes[1:]), start=1)
        if left.get("section") != right.get("section")
    }
    for index in range(len(scenes) - 1):
        boundary_number = index + 1
        if boundary_number in hard_boundaries or boundary_number % 3 != 1:
            reason = (
                "论证章节明确转换，直接切换强化信息落点。"
                if boundary_number in hard_boundaries
                else "相邻镜头视觉命题已经完整，使用硬切维持短视频节奏。"
            )
            transitions.append({"type": "hard_cut", "reason": reason})
            continue
        boundary = float(scenes[index]["time_range_seconds"][1])
        transitions.append(
            {
                "type": "parallax",
                "time_range_seconds": [f"{boundary - 0.300:.3f}", f"{boundary + 0.300:.3f}"],
                "reason": "相邻语义连续，用共享背景和前景差速保持讲解动势。",
            }
        )
    plan = {
        "fps": 30,
        "total_duration_seconds": f"{float(scenes[-1]['time_range_seconds'][1]) - float(scenes[0]['time_range_seconds'][0]):.3f}",
        "scenes": scenes,
        "transitions": transitions,
    }
    write_json(run_dir / "scene-plan.json", plan)
    write_json(run_dir / "fact-contracts.json", contracts)
    return plan, contracts


def _find_pnpm() -> str:
    return shutil.which("pnpm.cmd") or shutil.which("pnpm") or "pnpm"


def _ensure_dependencies(run_dir: Path) -> None:
    template = run_dir / "sceneFolder"
    modules = template / "node_modules"
    if not (modules / "remotion" / "package.json").exists():
        run_command(
            [_find_pnpm(), "install", "--frozen-lockfile", "--ignore-scripts", "--registry=https://registry.npmmirror.com"],
            template,
        )
    if os.name == "nt":
        # Remotion 4 may place Chromium in its shared per-user cache rather than
        # node_modules/.remotion. Trust the official ensure command's exit code;
        # the render helper resolves the same shared cache at runtime.
        result = run_command([_find_pnpm(), "run", "remotion:ensure-browser"], template, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Remotion browser installation failed with {result.returncode}")


def _junction(link: Path, target: Path) -> None:
    if link.exists():
        return
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
        )
        if result.returncode:
            raise RuntimeError("Could not create Windows directory junction")
    else:
        link.symlink_to(target, target_is_directory=True)


def _fact_prompt(contract: dict) -> str:
    allowed = "、".join(contract.get("approved_copy", [])) or "仅使用字幕原文中的必要短语"
    return (
        "\n\n# 本场景事实与屏幕文字契约\n\n"
        f"- 旁白事实源：{contract['narration']}\n"
        f"- 批准的屏幕短文案：{allowed}\n"
        "- 屏幕上的中文、数字、金额、比例、日期、案号和裁判结论必须逐字来自上述事实源或批准文案。\n"
        "- 可用纯几何、图标、罗马数字和无文字装饰表达层级；写代码后先执行事实审计，再渲染。\n"
        "\n# 观众可理解性契约\n\n"
        f"- 本镜头必须让观众直接理解：{contract.get('visual_goal') or contract.get('meaning')}\n"
        "- 先表现旁白中的人物、物体、动作或关系，再添加装饰性排版。\n"
        "- 不得用一排无标签圆点、孤立细线、纯数字或抽象徽章替代核心事件。\n"
        "- 金额、日期等大字不能冲出画布；主要内容保持在 x=80..1000、y=100..1000。\n"
        "- 每个元素的运动必须对应叙事变化；若删掉旁白仍看不出镜头含义，应重新设计。\n"
    )


def prepare(run_dir: Path) -> None:
    plan = run_dir / "scene-plan.json"
    contracts = json.loads((run_dir / "fact-contracts.json").read_text(encoding="utf-8"))
    run_command([sys.executable, "scene_plan.py", str(plan)], run_dir)
    _ensure_dependencies(run_dir)
    run_command(
        [sys.executable, "prepare-scenes.py", "sceneFolder", "scenes", "design-systems", str(plan)],
        run_dir,
    )
    shared = (run_dir / "sceneFolder" / "node_modules").resolve()
    background = run_dir / "resources" / "backgrounds" / "darkbg.png"
    for scene_dir in sorted((run_dir / "scenes").glob("scene-*")):
        _junction(scene_dir / "node_modules", shared)
        shutil.copy2(background, scene_dir / "public" / "img" / "darkbg.png")
        contract = contracts[scene_dir.name]
        write_json(scene_dir / "fact-contract.json", contract)
        prompt = scene_dir / "claude-scene-prompt.md"
        prompt.write_text(prompt.read_text(encoding="utf-8") + _fact_prompt(contract), encoding="utf-8")
    run_command(
        [
            sys.executable,
            "prepare-transitions.py",
            "sceneFolder",
            "transitionFolder",
            "transitions",
            str(plan),
            "--shared-node-modules",
            str(shared),
        ],
        run_dir,
    )
    state_path = run_dir / "run-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update({"status": "prepared", "scene_count": len(contracts)})
    write_json(state_path, state)
    StateGraph(run_dir / "harness-state.json").complete(
        "prepared", input_hash([run_dir / "scene-plan.json", run_dir / "fact-contracts.json"]),
        outputs=[run_dir / "scene-plan.json", run_dir / "fact-contracts.json"],
        metadata={"scene_count": len(contracts)},
    )


def audit_scene(scene_dir: Path) -> dict:
    contract = json.loads((scene_dir / "fact-contract.json").read_text(encoding="utf-8"))
    facts = write_audit(scene_dir, contract)
    timing = write_timing_audit(scene_dir)
    return {
        "scene_id": scene_dir.name,
        "status": "accepted" if facts["status"] == timing["status"] == "accepted" else "rejected",
        "facts": facts,
        "timing": timing,
    }


def worker_prompt(revision: bool = False) -> str:
    if revision:
        return (
            "读取 artifacts/fact-revision-request.json 和 artifacts/timing-revision-request.json（存在的文件才处理）。"
            "只修复被列出的屏幕事实或局部帧问题，保留镜头构图，然后重新运行技术检查；不要渲染。"
        )
    return (
        "执行 claude-scene-prompt.md：先完成 frame.md，再写 Remotion 场景。"
        "让人物、物体、动作或关系直接解释旁白；围绕一个视觉主体安排开始、中点、高潮和结束。"
        "屏幕事实遵守 fact-contract.json，主体保持在安全区。完成技术检查后停下，不渲染。"
    )


def scene_fingerprints(scene_dir: Path, config: HarnessConfig) -> tuple[str, str]:
    authored = input_hash(
        [scene_dir / "fact-contract.json", scene_dir / "scene-metadata.json", scene_dir / "claude-scene-prompt.md"],
        [
            config.route("scene_worker").provider, config.route("scene_worker").model,
            config.route("scene_worker").fallback_model, worker_prompt(),
        ],
    )
    images = [scene_dir / "artifacts" / "visual-gate" / f"{label}-review.jpg" for label in ("early", "mid", "late")]
    critic = input_hash(
        images,
        [config.route("critic").provider, config.route("critic").model, CRITIC_PROMPT_VERSION],
    )
    return authored, critic


def _claude_executable() -> str:
    npm_shim = shutil.which("claude.cmd")
    if npm_shim:
        native = Path(npm_shim).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if native.exists():
            return str(native)
    return shutil.which("claude.exe") or shutil.which("claude") or "claude"


def _run_claude(
    scene_dir: Path,
    prompt: str,
    timeout: int,
    *,
    json_schema: dict | None = None,
    disable_tools: bool = False,
    route: ModelRoute | None = None,
    state_graph: StateGraph | None = None,
    config: HarnessConfig | None = None,
) -> str:
    route = route or ModelRoute("claude")
    if state_graph and config:
        state_graph.reserve_call(
            max_calls=int(config.budget.get("max_model_calls", 0)),
            max_cost_usd=float(config.budget.get("max_total_cost_usd", 0.0)),
            estimated_cost_usd=route.estimated_cost_usd,
        )
    if route.provider == "codex_text":
        artifact_dir = scene_dir / ".harness"
        artifact_dir.mkdir(exist_ok=True)
        response_path = artifact_dir / "last-response.txt"
        response_path.unlink(missing_ok=True)
        schema_path = None
        if json_schema is not None:
            schema_path = artifact_dir / "response-schema.json"
            write_json(schema_path, json_schema)
        command = codex_text_command(route, response_path, schema_path)
        result = subprocess.run(
            command, cwd=scene_dir, input=prompt, check=False, timeout=timeout,
            text=True, encoding="utf-8", errors="replace", capture_output=True,
        )
        combined = "\n".join(value for value in (result.stdout, result.stderr) if value)
        if result.returncode != 0 or not response_path.exists():
            if is_retryable_model_failure(combined):
                raise WorkerQuotaExceeded(combined.strip() or "Codex quota exceeded")
            raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
        return response_path.read_text(encoding="utf-8")
    if route.provider != "claude":
        raise ValueError(f"Unsupported text provider: {route.provider}")
    command = claude_command(_claude_executable(), route, structured=json_schema is not None)
    if json_schema is not None:
        command.extend(["--json-schema", json.dumps(json_schema, ensure_ascii=False)])
    # On Windows, claude.cmd drops the final prompt when --tools receives an
    # empty argument. Director calls remain read-only by contract and their
    # output is captured by the harness, so omitting the flag is safer.
    result = subprocess.run(
        command,
        cwd=scene_dir,
        input=prompt,
        check=False,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    output = "\n".join(value for value in (result.stdout, result.stderr) if value)
    if output:
        console_encoding = sys.stdout.encoding or "utf-8"
        print(output.encode(console_encoding, errors="replace").decode(console_encoding, errors="replace"))
    if result.returncode != 0:
        if is_retryable_model_failure(output):
            raise WorkerQuotaExceeded(output.strip() or "Claude worker quota exceeded")
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
    return result.stdout or ""


def _run_role(
    scene_dir: Path, prompt: str, timeout: int, *, config: HarnessConfig, role: str,
    state_graph: StateGraph, json_schema: dict | None = None,
) -> str:
    route = config.route(role)
    try:
        return _run_claude(
            scene_dir, prompt, timeout, json_schema=json_schema, route=route,
            state_graph=state_graph, config=config,
        )
    except (WorkerQuotaExceeded, subprocess.CalledProcessError):
        if not route.fallback_model or route.fallback_model == route.model:
            raise
        fallback = ModelRoute(route.provider, route.fallback_model, "", route.estimated_cost_usd)
        return _run_claude(
            scene_dir, prompt, timeout, json_schema=json_schema, route=fallback,
            state_graph=state_graph, config=config,
        )


def _render_scene(scene_dir: Path) -> dict:
    env = os.environ.copy()
    ffmpeg_dir = Path.home() / "bin"
    if (ffmpeg_dir / "ffprobe.exe").exists():
        env["PATH"] = f"{ffmpeg_dir}{os.pathsep}{env.get('PATH', '')}"
    pnpm = _find_pnpm()
    subprocess.run([pnpm, "run", "verify"], cwd=scene_dir, env=env, check=True)
    render_env = env | {"REMOTION_OUTPUT": f"{scene_dir.name}.mov"}
    subprocess.run([pnpm, "run", "remotion:render"], cwd=scene_dir, env=render_env, check=True)
    subprocess.run([pnpm, "run", "render:verify"], cwd=scene_dir, env=env, check=True)
    visual = inspect_render(scene_dir)
    if visual["status"] != "accepted":
        problems = "; ".join(visual.get("problems", [])) or "visual gate rejected representative frames"
        raise RuntimeError(f"{scene_dir.name} failed visual gate: {problems}")
    subprocess.run([pnpm, "run", "transition-handles:render"], cwd=scene_dir, env=env, check=True)
    return visual


def _validate_creative_critique(report: dict) -> dict:
    scores = report.get("scores", {})
    expected = {
        "semantic_clarity", "visual_thesis", "information_density", "composition",
        "motion_purpose", "rhythm", "continuity", "caption_safety",
    }
    if set(scores) != expected or any(not isinstance(value, int) or value < 0 or value > 2 for value in scores.values()):
        raise ValueError("Critic returned invalid rubric scores")
    calculated = sum(scores.values())
    evidence = report.get("visual_evidence", [])
    direct_frames = {str(item.get("frame", "")) for item in evidence if isinstance(item, dict) and item.get("observation")}
    text = " ".join(str(value) for value in report.get("problems", []) + report.get("revision", [])).lower()
    inspection_failed = any(marker in text for marker in ("unsupported image", "未做直接视觉", "无法直接", "无法读取", "不能读取"))
    report["total"] = calculated
    report["verdict"] = (
        "pass" if calculated >= 14 and all(value > 0 for value in scores.values())
        and direct_frames == {"early", "mid", "late"} and not inspection_failed else "revise"
    )
    return report


def _creative_critique(scene_dir: Path, timeout: int, *, config: HarnessConfig | None = None, state_graph: StateGraph | None = None) -> dict:
    output = scene_dir / "artifacts" / "creative-critique.json"
    output.unlink(missing_ok=True)
    schema_path = scene_dir / "artifacts" / "creative-critique-schema.json"
    response_path = scene_dir / "artifacts" / "creative-critique-response.json"
    schema = {
        "type": "object",
        "properties": {
            "scores": {"type": "object", "properties": {
                name: {"type": "integer", "minimum": 0, "maximum": 2}
                for name in (
                    "semantic_clarity", "visual_thesis", "information_density", "composition",
                    "motion_purpose", "rhythm", "continuity", "caption_safety",
                )
            }, "required": [
                "semantic_clarity", "visual_thesis", "information_density", "composition",
                "motion_purpose", "rhythm", "continuity", "caption_safety",
            ], "additionalProperties": False},
            "visual_evidence": {"type": "array", "minItems": 3, "maxItems": 3, "items": {
                "type": "object", "properties": {
                    "frame": {"type": "string", "enum": ["early", "mid", "late"]},
                    "observation": {"type": "string"},
                }, "required": ["frame", "observation"], "additionalProperties": False,
            }},
            "problems": {"type": "array", "items": {"type": "string"}},
            "revision": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["scores", "visual_evidence", "problems", "revision"],
        "additionalProperties": False,
    }
    write_json(schema_path, schema)
    prompt = (
        "你是严格的短视频视觉审查员。三张附件依次是 early、mid、late 帧。"
        "结合当前目录 fact-contract.json 与 frame.md，只依据你直接看到的画面，按0到2分评价："
        "semantic_clarity、visual_thesis、information_density、composition、motion_purpose、rhythm、continuity、caption_safety。"
        "每张图必须写一条具体视觉观察；纯文字堆叠、主体难辨、构图空、画面重复、边缘裁切或字幕保留区有主体应扣分。"
        "problems 与 revision 必须具体可执行。只返回符合 schema 的 JSON。"
    )
    config = config or config_for_run(scene_dir.parents[1])
    route = config.route("critic")
    if route.provider == "disabled":
        raise RuntimeError("Visual critic is disabled; production must fail closed")
    if route.provider == "manual":
        report = _validate_creative_critique(read_manual_critique(scene_dir))
        write_json(output, report)
        return report
    if route.provider != "codex_images":
        raise ValueError(f"Unsupported visual critic provider: {route.provider}")
    if state_graph:
        state_graph.reserve_call(
            max_calls=int(config.budget.get("max_model_calls", 0)),
            max_cost_usd=float(config.budget.get("max_total_cost_usd", 0.0)),
            estimated_cost_usd=route.estimated_cost_usd,
        )
    images = [scene_dir / "artifacts" / "visual-gate" / f"{label}-review.jpg" for label in ("early", "mid", "late")]
    if not all(image.exists() for image in images):
        raise RuntimeError("Visual critic cannot run because review images are missing")
    command = codex_command(route, schema_path, response_path, images)
    result = subprocess.run(
        command, cwd=scene_dir, input=prompt, text=True, encoding="utf-8", errors="replace",
        capture_output=True, timeout=timeout, check=False,
    )
    if result.returncode != 0 or not response_path.exists():
        raise RuntimeError(f"{scene_dir.name} Codex visual critic failed: {(result.stderr or result.stdout).strip()}")
    report = _validate_creative_critique(json.loads(response_path.read_text(encoding="utf-8")))
    write_json(output, report)
    return report


def _creative_revision_prompt() -> str:
    return (
        "读取 artifacts/creative-critique.json，把其中problems和revision作为强制返工要求。"
        "允许重写frame.md和scenes/DefaultScene.tsx，不得改变scene-metadata.json、时长或事实契约。"
        "优先让观众一眼看懂，修完运行pnpm run verify，不要自行渲染。"
    )


def _render_with_visual_revisions(
    scene_dir: Path, timeout: int, max_revisions: int, *,
    config: HarnessConfig | None = None, state_graph: StateGraph | None = None,
) -> dict:
    report_path = scene_dir / "artifacts" / "visual-gate" / "visual-gate.json"
    for attempt in range(max_revisions + 1):
        try:
            return _render_scene(scene_dir)
        except RuntimeError as exc:
            if "failed visual gate" not in str(exc) or not report_path.exists() or attempt >= max_revisions:
                raise
            report = json.loads(report_path.read_text(encoding="utf-8"))
            write_json(
                scene_dir / "artifacts" / "visual-revision-request.json",
                {"attempt": attempt + 1, "problems": report.get("problems", []), "report": report},
            )
            if config is None or state_graph is None:
                config = config_for_run(scene_dir.parents[1])
                state_graph = StateGraph(scene_dir.parents[1] / "harness-state.json")
            _run_role(
                scene_dir,
                "读取 artifacts/visual-revision-request.json 并修复全部可见性问题。"
                "允许调整构图和scenes/DefaultScene.tsx，但不得改事实、时长或字幕。"
                "主要内容必须保持在x=80..1000、y=100..1000，尤其不得以全宽前景背景触碰左右边缘。"
                "DefaultScene根AbsoluteFill必须透明，不得设置全画布background或backgroundColor；统一背景由Root提供。"
                "修复后运行pnpm run verify，不要自行渲染。",
                timeout, config=config, role="revision_worker", state_graph=state_graph,
            )
            audit = audit_scene(scene_dir)
            if audit["status"] != "accepted":
                raise RuntimeError(f"{scene_dir.name} visual revision broke fact/timing contract")
    raise RuntimeError(f"{scene_dir.name} visual revision loop exhausted")


def run_scene(
    scene_dir: Path,
    *,
    timeout: int = 900,
    max_fact_revisions: int = 2,
    max_creative_revisions: int = 1,
    critic_enabled: bool = True,
    config: HarnessConfig | None = None,
    state_graph: StateGraph | None = None,
) -> dict:
    run_dir = scene_dir.parents[1]
    config = config or config_for_run(run_dir)
    state_graph = state_graph or StateGraph(run_dir / "harness-state.json")
    state_path = scene_dir / "worker-state.json"
    scene_graph = StateGraph(scene_dir / "scene-state.json")
    contract_path = scene_dir / "fact-contract.json"
    metadata_path = scene_dir / "scene-metadata.json"
    authored_fingerprint, _ = scene_fingerprints(scene_dir, config)
    prior_video = scene_dir / f"{scene_dir.name}.mov"
    authored_current = scene_graph.is_current("authored", authored_fingerprint)
    if prior_video.exists() and prior_video.stat().st_size > 0 and authored_current:
        write_json(state_path, {"status": "resuming_after_render", "scene_id": scene_dir.name})
    else:
        if not authored_current:
            scene_graph.invalidate_from("authored")
            prior_video.unlink(missing_ok=True)
            (scene_dir / "artifacts" / "creative-critique.json").unlink(missing_ok=True)
        write_json(state_path, {"status": "authoring", "scene_id": scene_dir.name})
        _run_role(scene_dir, worker_prompt(), timeout, config=config, role="scene_worker", state_graph=state_graph)
        authored_outputs = [scene_dir / "frame.md", scene_dir / "scenes" / "DefaultScene.tsx"]
        scene_graph.complete(
            "authored", authored_fingerprint, outputs=authored_outputs,
            metadata={"provider": config.route("scene_worker").provider, "model": config.route("scene_worker").model},
        )
    for revision in range(max_fact_revisions + 1):
        report = audit_scene(scene_dir)
        if report["status"] == "accepted":
            audit_fingerprint = input_hash([scene_dir / "scenes" / "DefaultScene.tsx", contract_path, metadata_path])
            scene_graph.complete("fact_passed", audit_fingerprint, outputs=[scene_dir / "artifacts" / "fact-audit.json"])
            scene_graph.complete("timing_passed", audit_fingerprint, outputs=[scene_dir / "artifacts" / "timing-audit.json"])
            break
        if revision >= max_fact_revisions:
            write_json(state_path, {"status": "fact_rejected", "report": report})
            raise RuntimeError(f"{scene_dir.name} failed fact audit after {max_fact_revisions} revisions")
        write_json(state_path, {"status": "fact_revision", "attempt": revision + 1, "report": report})
        _run_role(scene_dir, worker_prompt(revision=True), timeout, config=config, role="revision_worker", state_graph=state_graph)
    write_json(state_path, {"status": "rendering", "fact_audit": "accepted"})
    visual = _render_with_visual_revisions(
        scene_dir, timeout, max_creative_revisions, config=config, state_graph=state_graph,
    )
    render_fingerprint = input_hash([scene_dir / "scenes" / "DefaultScene.tsx", metadata_path])
    scene_graph.complete("rendered", render_fingerprint, outputs=[prior_video])
    scene_graph.complete(
        "visual_passed", input_hash([prior_video]),
        outputs=[scene_dir / "artifacts" / "visual-gate" / "visual-gate.json"],
    )
    critique = None
    if critic_enabled:
        for creative_attempt in range(max_creative_revisions + 1):
            write_json(state_path, {"status": "creative_review", "attempt": creative_attempt + 1})
            critique = _creative_critique(scene_dir, timeout, config=config, state_graph=state_graph)
            if critique["verdict"] == "pass":
                scene_graph.complete(
                    "critic_passed",
                    scene_fingerprints(scene_dir, config)[1],
                    outputs=[scene_dir / "artifacts" / "creative-critique.json"],
                    metadata={"provider": config.route("critic").provider, "model": config.route("critic").model},
                )
                break
            if creative_attempt >= max_creative_revisions:
                write_json(state_path, {"status": "creative_rejected", "critique": critique})
                raise RuntimeError(f"{scene_dir.name} failed creative review")
            write_json(state_path, {"status": "creative_revision", "attempt": creative_attempt + 1, "critique": critique})
            _run_role(scene_dir, _creative_revision_prompt(), timeout, config=config, role="revision_worker", state_graph=state_graph)
            report = audit_scene(scene_dir)
            if report["status"] != "accepted":
                _run_role(scene_dir, worker_prompt(revision=True), timeout, config=config, role="revision_worker", state_graph=state_graph)
                report = audit_scene(scene_dir)
            if report["status"] != "accepted":
                raise RuntimeError(f"{scene_dir.name} creative revision broke fact/timing contract")
            visual = _render_with_visual_revisions(
                scene_dir, timeout, max_creative_revisions, config=config, state_graph=state_graph,
            )
    result = {
        "status": "rendered",
        "scene_id": scene_dir.name,
        "video": str(scene_dir / f"{scene_dir.name}.mov"),
        "fact_audit": "accepted",
        "visual_gate": visual,
        "creative_critique": critique,
    }
    write_json(state_path, result)
    return result


def run_scenes(
    run_dir: Path,
    scene_ids: list[str],
    *,
    concurrency: int = 3,
    timeout: int = 900,
    max_creative_revisions: int = 1,
    critic_enabled: bool = True,
) -> list[dict]:
    config = config_for_run(run_dir)
    state_graph = StateGraph(run_dir / "harness-state.json")
    if not scene_ids:
        scene_ids = [path.name for path in sorted((run_dir / "scenes").glob("scene-*"))]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        jobs = {
            pool.submit(
                run_scene,
                run_dir / "scenes" / scene_id,
                timeout=timeout,
                max_fact_revisions=max(0, int(config.budget.get("max_scene_attempts", 3)) - 1),
                max_creative_revisions=max_creative_revisions,
                critic_enabled=critic_enabled,
                config=config,
                state_graph=state_graph,
            ): scene_id
            for scene_id in scene_ids
        }
        for future in as_completed(jobs):
            scene_id = jobs[future]
            if future.cancelled():
                continue
            try:
                results.append(future.result())
            except WorkerQuotaExceeded as exc:
                failure = {"status": "quota_blocked", "scene_id": scene_id, "error": str(exc)}
                results.append(failure)
                write_json(run_dir / "scenes" / scene_id / "worker-state.json", failure)
                # Do not burn requests on work that has not started yet. Running
                # workers finish naturally; pending futures are resumable later.
                for pending, pending_scene in jobs.items():
                    if pending.cancel():
                        cancelled = {"status": "quota_deferred", "scene_id": pending_scene}
                        results.append(cancelled)
                        write_json(run_dir / "scenes" / pending_scene / "worker-state.json", cancelled)
            except Exception as exc:
                failure = {"status": "failed", "scene_id": scene_id, "error": str(exc)}
                results.append(failure)
                write_json(run_dir / "scenes" / scene_id / "worker-state.json", failure)
    write_json(run_dir / "scene-production-results.json", results)
    return results


def run_transition(run_dir: Path, transition_id: str, *, timeout: int = 900) -> dict:
    plan = run_dir / "scene-plan.json"
    transition_dir = run_dir / "transitions" / transition_id
    run_command([sys.executable, "stage-transition.py", str(plan), transition_id], run_dir)
    prompt = (
        "执行 transition-prompt.md 的全部步骤。只使用已提供的相邻场景边界素材，不新增事实、中文、数字或字幕。"
        "完成Remotion转场、渲染和技术验证。"
    )
    config = config_for_run(run_dir)
    _run_role(
        transition_dir, prompt, timeout, config=config, role="transition_worker",
        state_graph=StateGraph(run_dir / "harness-state.json"),
    )
    output = transition_dir / f"{transition_id}.mov"
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"{transition_id} did not produce {output.name}")
    return {"status": "rendered", "transition_id": transition_id, "video": str(output)}


def run_transitions(run_dir: Path, transition_ids: list[str], *, concurrency: int = 2, timeout: int = 900) -> list[dict]:
    if not transition_ids:
        transition_ids = [path.name for path in sorted((run_dir / "transitions").glob("transition-*"))]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        jobs = {
            pool.submit(run_transition, run_dir, transition_id, timeout=timeout): transition_id
            for transition_id in transition_ids
        }
        for future in as_completed(jobs):
            transition_id = jobs[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"status": "failed", "transition_id": transition_id, "error": str(exc)})
    write_json(run_dir / "transition-production-results.json", results)
    if all(item.get("status") == "rendered" for item in results):
        outputs = [Path(item["video"]) for item in results]
        StateGraph(run_dir / "harness-state.json").complete(
            "transition_ready", input_hash([run_dir / "scene-plan.json"] + outputs), outputs=outputs,
        )
    return results


def _find_media_tool(name: str) -> str:
    executable = f"{name}.exe" if os.name == "nt" else name
    candidate = Path.home() / "bin" / executable
    return str(candidate) if candidate.exists() else (shutil.which(executable) or name)


def assemble(run_dir: Path, output: Path | None = None) -> dict:
    plan_data = json.loads((run_dir / "scene-plan.json").read_text(encoding="utf-8"))
    preflight_problems = []
    state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
    if not (run_dir / state["audio"]).exists():
        preflight_problems.append("missing narration audio")
    if not (run_dir / "transcription.srt").exists():
        preflight_problems.append("missing transcription.srt")
    sequence_path = run_dir / "reports" / "sequence-review.json"
    if not sequence_path.exists() or json.loads(sequence_path.read_text(encoding="utf-8")).get("status") != "pass":
        preflight_problems.append("sequence review has not passed")
    for index in range(1, len(plan_data["scenes"]) + 1):
        scene_id = f"scene-{index:03d}"
        scene_dir = run_dir / "scenes" / scene_id
        if not (scene_dir / f"{scene_id}.mov").exists():
            preflight_problems.append(f"{scene_id}: missing rendered video")
            continue
        for name in ("fact-audit.json", "timing-audit.json"):
            path = scene_dir / "artifacts" / name
            if not path.exists() or json.loads(path.read_text(encoding="utf-8")).get("status") != "accepted":
                preflight_problems.append(f"{scene_id}: {name} is not accepted")
        visual_path = scene_dir / "artifacts" / "visual-gate" / "visual-gate.json"
        if not visual_path.exists() or json.loads(visual_path.read_text(encoding="utf-8")).get("status") != "accepted":
            preflight_problems.append(f"{scene_id}: visual gate is not accepted")
        critique_path = scene_dir / "artifacts" / "creative-critique.json"
        if not critique_path.exists() or json.loads(critique_path.read_text(encoding="utf-8")).get("verdict") != "pass":
            preflight_problems.append(f"{scene_id}: creative critic has not passed")
    for boundary, transition in enumerate(plan_data.get("transitions", []), start=1):
        if transition.get("type") == "hard_cut":
            continue
        transition_id = f"transition-{boundary:03d}"
        path = run_dir / "transitions" / transition_id / f"{transition_id}.mov"
        if not path.exists() or path.stat().st_size == 0:
            preflight_problems.append(f"{transition_id}: missing rendered transition")
    if preflight_problems:
        raise RuntimeError("Assembly preflight rejected:\n" + "\n".join(preflight_problems))
    visual = run_dir / "assembled-visual.mov"
    run_command(
        [sys.executable, "assemble-video.py", str(run_dir / "scene-plan.json"), "--output", str(visual)],
        run_dir,
    )
    audio = run_dir / state["audio"]
    output = output or (run_dir / "final.mp4")
    subtitle_filter = (
        "subtitles=transcription.srt:original_size=1080x1440:force_style='FontName=Microsoft YaHei,"
        "FontSize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H90000000,"
        "BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginL=24,MarginR=24,MarginV=30'"
    )
    subprocess.run(
        [
            _find_media_tool("ffmpeg"), "-y", "-i", str(visual), "-i", str(audio),
            "-vf", subtitle_filter, "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(output),
        ],
        cwd=run_dir,
        check=True,
    )
    probe = subprocess.run(
        [_find_media_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration,size", "-show_entries", "stream=codec_name,width,height,r_frame_rate", "-of", "json", str(output)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    report = {"status": "complete", "output": str(output), "probe": json.loads(probe.stdout)}
    write_json(run_dir / "completion-report.json", report)
    StateGraph(run_dir / "harness-state.json").complete(
        "assembled",
        input_hash([run_dir / "scene-plan.json", run_dir / "transcription.srt", audio, visual]),
        outputs=[output, run_dir / "completion-report.json"],
    )
    return report
