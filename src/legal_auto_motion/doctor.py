from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .config import HarnessConfig, load_config


KNOWN_VENDOR_OVERRIDES = {
    "prepare-scenes.py",
    "prepare-transitions.py",
    "sceneFolder/claude-scene-prompt.md",
    "sceneFolder/frame.md",
    "sceneFolder/scripts/remotion-browser-executable.mjs",
    "shared_dependencies.py",
    "resources/backgrounds/darkbg.png",
    "resources/backgrounds/lightbg.png",
}


def _files(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def compare_vendor(upstream: Path, vendor: Path) -> dict:
    source, installed = _files(upstream), _files(vendor)
    paths = sorted(set(source) | set(installed))
    differences = [path for path in paths if source.get(path) != installed.get(path)]
    unexpected = [
        path for path in differences
        if path not in KNOWN_VENDOR_OVERRIDES
        and not (path.startswith("resources/") and ("猫学长" in path or "avatar" in path.lower()))
    ]
    return {
        "status": "pass" if not unexpected else "rejected",
        "difference_count": len(differences),
        "known_overrides": [path for path in differences if path in KNOWN_VENDOR_OVERRIDES],
        "unexpected_differences": unexpected,
    }


def required_agent_commands(config: HarnessConfig) -> dict[str, str]:
    required: dict[str, str] = {}
    for role, route in config.models.items():
        if route.provider == "claude":
            required[f"{role}:claude"] = "claude"
        elif route.provider in {"codex_text", "codex_worker", "codex_images"}:
            required[f"{role}:codex"] = "codex"
        elif route.provider == "generic_cli":
            required[f"{role}:generic_cli"] = route.command[0]
    return required


def doctor(project: Path) -> dict:
    config_path = project / "harness.toml"
    config = load_config(config_path if config_path.exists() else None)
    commands = {
        "python": shutil.which("python") or shutil.which("python.exe"),
        "node": shutil.which("node") or shutil.which("node.exe"),
        "pnpm": shutil.which("pnpm") or shutil.which("pnpm.cmd"),
        "ffmpeg": shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or str(Path.home() / "bin" / "ffmpeg.exe"),
        "ffprobe": shutil.which("ffprobe") or shutil.which("ffprobe.exe") or str(Path.home() / "bin" / "ffprobe.exe"),
    }
    for label, executable in required_agent_commands(config).items():
        commands[label] = shutil.which(executable) or executable
    available = {name: bool(path and Path(path).exists()) for name, path in commands.items()}
    upstream = project / ".private" / "sxhzju-auto-motion" / "auto-vibe-"
    vendor = project / "vendor" / "auto-vibe"
    if upstream.exists() and vendor.exists():
        vendor_report = compare_vendor(upstream, vendor)
        vendor_report["mode"] = "verified_against_local_upstream"
    elif vendor.exists():
        vendor_report = {"status": "pass", "mode": "bundled_private_base"}
    else:
        vendor_report = {"status": "rejected", "problem": "Missing vendor/auto-vibe production base"}
    return {
        "status": "pass" if all(available.values()) and vendor_report["status"] == "pass" else "rejected",
        "commands": available,
        "vendor": vendor_report,
    }
