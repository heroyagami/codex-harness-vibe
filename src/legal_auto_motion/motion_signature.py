from __future__ import annotations


def _band(value: float, *, low: float, high: float) -> str:
    if value < low:
        return "low"
    if value >= high:
        return "high"
    return "medium"


def motion_signature(change_scores: list[float], *, meaningful_threshold: float = 0.012) -> dict:
    """Convert sampled frame-difference scores into a compact motion signature.

    The signature is intentionally coarse. It is designed for sequence-level
    anti-repetition checks, not for reconstructing the animation itself.
    """
    if not change_scores:
        return {
            "intensity": "none",
            "phase_bias": "none",
            "burstiness": "none",
            "motion_density": "none",
            "signature": "none:none:none:none",
        }

    mean = sum(change_scores) / len(change_scores)
    midpoint = max(1, len(change_scores) // 2)
    early = change_scores[:midpoint]
    late = change_scores[midpoint:] or early
    early_mean = sum(early) / len(early)
    late_mean = sum(late) / len(late)

    if early_mean > late_mean * 1.35:
        phase_bias = "front_loaded"
    elif late_mean > early_mean * 1.35:
        phase_bias = "back_loaded"
    else:
        phase_bias = "balanced"

    meaningful = [score >= meaningful_threshold for score in change_scores]
    density = sum(meaningful) / len(meaningful)

    bursts = 0
    active = False
    for flag in meaningful:
        if flag and not active:
            bursts += 1
        active = flag
    burst_ratio = bursts / max(1, len(change_scores))

    intensity = _band(mean, low=0.018, high=0.055)
    motion_density = _band(density, low=0.30, high=0.68)
    burstiness = _band(burst_ratio, low=0.12, high=0.28)
    signature = f"{intensity}:{phase_bias}:{burstiness}:{motion_density}"

    return {
        "intensity": intensity,
        "phase_bias": phase_bias,
        "burstiness": burstiness,
        "motion_density": motion_density,
        "mean_change": round(mean, 5),
        "early_mean": round(early_mean, 5),
        "late_mean": round(late_mean, 5),
        "meaningful_ratio": round(density, 4),
        "burst_count": bursts,
        "signature": signature,
    }


def repeated_signature_runs(items: list[dict], *, minimum_run: int = 3) -> list[list[str]]:
    """Return consecutive scene runs that share the same coarse motion signature."""
    runs: list[list[str]] = []
    current: list[str] = []
    current_signature = ""
    for item in items:
        signature = str(item.get("signature", ""))
        scene_id = str(item.get("scene_id", ""))
        if signature and signature != "none:none:none:none" and signature == current_signature:
            current.append(scene_id)
        else:
            if len(current) >= minimum_run:
                runs.append(current[:])
            current_signature = signature
            current = [scene_id]
    if len(current) >= minimum_run:
        runs.append(current)
    return runs
