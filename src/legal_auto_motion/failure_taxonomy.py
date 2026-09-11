from __future__ import annotations


FAILURE_CATEGORIES = (
    "provider_quota",
    "provider_timeout",
    "context_budget",
    "context_policy",
    "fact_violation",
    "timing_violation",
    "render_toolchain",
    "visibility_safe_zone",
    "motion_quality",
    "creative_rejection",
    "sequence_rejection",
    "permission",
    "interrupted",
    "agent_error",
    "unknown",
)


def classify_failure(error: str, *, status: str = "") -> str:
    text = f"{status} {error}".lower()
    rules = (
        ("provider_quota", ("quota", "usage limit", "rate limit", "429", "overloaded")),
        ("provider_timeout", ("timeout", "timed out")),
        ("context_budget", ("context budget", "max_prompt_chars", "prompt budget", "memory budget")),
        ("context_policy", ("context isolation", "sibling scene", "sibling-scene", "context-policy", "prompt_file")),
        ("fact_violation", ("fact audit", "fact violation", "unsupported visible fact", "broke fact")),
        ("timing_violation", ("timing audit", "beat gate", "timing violation", "broke timing")),
        ("visibility_safe_zone", ("visual gate", "safe zone", "safe-zone", "clipped", "visibility")),
        ("motion_quality", ("motion gate", "freeze", "jitter", "raster oscillation")),
        ("creative_rejection", ("creative critic", "creative revision", "critic rejection")),
        ("sequence_rejection", ("sequence review", "sequence-level", "repeated silhouette")),
        ("render_toolchain", ("ffmpeg", "ffprobe", "remotion", "pnpm", "render failed", "chromium")),
        ("permission", ("permission", "access denied")),
        ("interrupted", ("interrupted", "process ended before")),
    )
    for category, markers in rules:
        if any(marker in text for marker in markers):
            return category
    if status and status not in {"complete", "succeeded", "rendered"}:
        return "agent_error"
    return "unknown"
