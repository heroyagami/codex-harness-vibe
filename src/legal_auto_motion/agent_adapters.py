from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .config import ModelRoute, config_for_run
from .context_policy import CONTEXT_POLICY_VERSION
from .providers import claude_command, codex_text_command, codex_worker_command
from .revision_router import discover_revision_route, revision_prompt


DEFAULT_MAX_SCENE_PROMPT_CHARS = 18000


@dataclass(frozen=True)
class AgentInvocation:
    command: list[str]
    stdin: str | None
    env: dict[str, str]
    response_path: Path | None = None
    prompt_path: Path | None = None


def _claude_executable() -> str:
    npm_shim = shutil.which("claude.cmd")
    if npm_shim:
        native = Path(npm_shim).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if native.exists():
            return str(native)
    return shutil.which("claude.exe") or shutil.which("claude") or "claude"


def _expand_command(command: tuple[str, ...], values: dict[str, str]) -> list[str]:
    result = []
    for argument in command:
        try:
            result.append(argument.format_map(values))
        except KeyError as exc:
            raise ValueError(f"Unsupported generic_cli placeholder: {exc.args[0]}") from exc
    return result


def _is_scene_worker_cwd(cwd: Path) -> bool:
    return cwd.name.startswith("scene-") and cwd.parent.name == "scenes"


def _isolation_prefix() -> str:
    return (
        f"# Context Isolation ({CONTEXT_POLICY_VERSION})\n"
        "This invocation is a fresh, single-scene worker context. Do not continue or reconstruct any prior scene session.\n"
        "Work only on the current scene directory. Never read sibling scene prompts, frame.md files, source code, artifacts, worker logs, or conversation history.\n"
        "Cross-scene consistency may use only the compact boundary_context in fact-contract.json and bounded artifacts/style-memory-guidance.md.\n"
        "Style memory is abstract guidance only: never copy a historical scene layout or code wholesale.\n"
        "Do not spawn subagents or create a persistent session. A retry is a new independent invocation.\n\n"
    )


def _adaptive_revision_overlay(cwd: Path, prompt: str) -> tuple[str, dict | None]:
    discovered = discover_revision_route(cwd, prompt)
    if discovered is None:
        return prompt, None
    route, report_path, _report = discovered
    instruction = revision_prompt(route, report_path)
    manifest = {
        "route": route.kind,
        "priority": route.priority,
        "report_path": report_path,
        "instruction_sha256": hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
        "created_at": time.time(),
    }
    artifacts = cwd / ".harness"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "revision-route.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return (
        "# Adaptive Revision Route\n"
        f"{instruction}\n"
        "This route narrows the repair scope. Do not broaden the rewrite unless the selected report makes the narrow repair impossible.\n\n"
        + prompt,
        manifest,
    )


def _write_invocation_manifest(
    artifacts: Path, cwd: Path, route: ModelRoute, prompt: str, *,
    max_prompt_chars: int, style_memory_chars: int, max_style_memory_chars: int,
    revision_manifest: dict | None = None,
) -> None:
    payload = {
        "version": CONTEXT_POLICY_VERSION,
        "scene_id": cwd.name,
        "fresh_context": True,
        "provider": route.provider,
        "model": route.model,
        "prompt_chars": len(prompt),
        "max_prompt_chars": int(max_prompt_chars),
        "style_memory_chars": int(style_memory_chars),
        "max_style_memory_chars": int(max_style_memory_chars),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "created_at": time.time(),
        "session_history_inherited": False,
        "sibling_scene_history_allowed": False,
    }
    if revision_manifest is not None:
        payload["adaptive_revision"] = revision_manifest
    (artifacts / "invocation-context.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_invocation(
    cwd: Path,
    prompt: str,
    route: ModelRoute,
    *,
    structured: bool = False,
    schema_path: Path | None = None,
    max_prompt_chars: int | None = None,
) -> AgentInvocation:
    cwd = cwd.resolve()
    artifacts = cwd / ".harness"
    artifacts.mkdir(parents=True, exist_ok=True)
    response_path = artifacts / "last-response.txt"
    response_path.unlink(missing_ok=True)
    env = os.environ.copy()

    effective_prompt = prompt
    revision_manifest = None
    if _is_scene_worker_cwd(cwd):
        config = config_for_run(cwd.parents[1])
        configured_prompt_limit = int(config.context.get("max_prompt_chars", DEFAULT_MAX_SCENE_PROMPT_CHARS))
        prompt_limit = int(max_prompt_chars or configured_prompt_limit)
        memory_limit = int(config.context.get("max_style_memory_chars", 3500))
        guidance_path = cwd / "artifacts" / "style-memory-guidance.md"
        style_memory_chars = 0
        if guidance_path.exists():
            style_memory_chars = len(guidance_path.read_text(encoding="utf-8"))
            if style_memory_chars > memory_limit:
                raise ValueError(
                    f"Style Memory exceeds isolated context budget: {style_memory_chars} > {memory_limit} chars"
                )
        routed_prompt, revision_manifest = _adaptive_revision_overlay(cwd, prompt)
        effective_prompt = _isolation_prefix() + routed_prompt
        if len(effective_prompt) > prompt_limit:
            raise ValueError(
                f"Scene worker prompt exceeds isolated context budget: {len(effective_prompt)} > {prompt_limit} chars"
            )
        env["HARNESS_CONTEXT_POLICY"] = CONTEXT_POLICY_VERSION
        env["HARNESS_SCENE_ID"] = cwd.name
        env["HARNESS_FRESH_CONTEXT"] = "1"
        if revision_manifest is not None:
            env["HARNESS_REVISION_ROUTE"] = str(revision_manifest["route"])
        _write_invocation_manifest(
            artifacts, cwd, route, effective_prompt,
            max_prompt_chars=prompt_limit,
            style_memory_chars=style_memory_chars,
            max_style_memory_chars=memory_limit,
            revision_manifest=revision_manifest,
        )

    if route.provider == "claude":
        command = claude_command(_claude_executable(), route, structured=structured)
        if structured and schema_path is not None:
            command.extend(["--json-schema", schema_path.read_text(encoding="utf-8")])
        if route.model:
            env["CLAUDE_CODE_SUBAGENT_MODEL"] = route.model
        return AgentInvocation(command, effective_prompt, env, response_path=None)

    if route.provider == "codex_text":
        return AgentInvocation(codex_text_command(route, response_path, schema_path), effective_prompt, env, response_path)

    if route.provider == "codex_worker":
        return AgentInvocation(codex_worker_command(route, response_path), effective_prompt, env, response_path)

    if route.provider == "generic_cli":
        if not route.command:
            raise ValueError("generic_cli provider requires models.<role>.command")
        if _is_scene_worker_cwd(cwd) and "{prompt_file}" not in " ".join(route.command):
            raise ValueError("generic_cli scene workers must consume the per-invocation {prompt_file}")
        prompt_path = artifacts / "agent-prompt.txt"
        prompt_path.write_text(effective_prompt, encoding="utf-8")
        values = {
            "cwd": str(cwd),
            "model": route.model,
            "prompt_file": str(prompt_path),
            "response_file": str(response_path),
            "schema_file": str(schema_path or ""),
        }
        return AgentInvocation(_expand_command(route.command, values), None, env, response_path, prompt_path)

    raise ValueError(f"Unsupported text provider: {route.provider}")
