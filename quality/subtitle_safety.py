"""Deterministic subtitle obstruction calibration for Visual Quality V1.

Uses the existing renderer scorer only. No API, vision model, detector, or provider
call is introduced here. Lower risk is safer.

Calibration (quality/subtitle_safety_regression_test.py, deterministic 1080x1920
frames): flat background ~= 0.000; moderate seeded texture ~= 0.21; high-contrast
checker ~= 0.95; skin-like occupied band ~= 1.40 before the existing positional
bias. A 0.35 ceiling deliberately leaves ~0.13 headroom above the moderate
fixture while rejecting the clearly busy fixtures. A 0.12 relocation margin is
larger than every existing position bias (max 0.030), so bias or small texture
noise alone can never trigger relocation. This favors false negatives over false
positive subtitle movement/jitter.
"""
from video.subtitle_engine import (
    VIDEO_HEIGHT,
    SUBTITLE_POSITION_CANDIDATES,
    HOOK_SUBTITLE_POSITION_CANDIDATES,
    SUBTITLE_POSITION_BIAS,
    HOOK_SUBTITLE_POSITION_BIAS,
    _visual_region_score,
)

SUBTITLE_SAFE_CEILING = 0.35
SUBTITLE_RELOCATION_MIN_MARGIN = 0.12
HOOK_SUBTITLE_SAFE_CEILING = 0.35


def _samples(video_clip, hook_mode=False):
    try:
        duration = float(video_clip.duration or 0.0)
    except Exception:
        duration = 0.0
    if duration <= 0:
        return []
    ratios = (0.08, 0.22, 0.40, 0.60, 0.82) if hook_mode else (0.20, 0.50, 0.80)
    return [max(0.0, min(duration - 0.01, duration * r)) for r in ratios]


def subtitle_position_risks(video_clip, subtitle_height=180, hook_mode=False):
    """Return the same mean scorer+bias values used by choose_safe_subtitle_y."""
    candidates = HOOK_SUBTITLE_POSITION_CANDIDATES if hook_mode else SUBTITLE_POSITION_CANDIDATES
    bias = HOOK_SUBTITLE_POSITION_BIAS if hook_mode else SUBTITLE_POSITION_BIAS
    times = _samples(video_clip, hook_mode)
    risks = {}
    for name, ratio in candidates:
        values = []
        for sample_time in times:
            try:
                frame = video_clip.get_frame(sample_time)
            except Exception:
                continue
            values.append(_visual_region_score(frame, int(VIDEO_HEIGHT * ratio), subtitle_height))
        if values:
            risks[name] = sum(values) / len(values) + float(bias.get(name, 0.0))
    return risks


def position_name_for_y(y, hook_mode=False):
    candidates = HOOK_SUBTITLE_POSITION_CANDIDATES if hook_mode else SUBTITLE_POSITION_CANDIDATES
    if y is None:
        return "bottom"
    return min(candidates, key=lambda item: abs(int(VIDEO_HEIGHT * item[1]) - int(y)))[0]


def position_y(name, hook_mode=False):
    candidates = dict(HOOK_SUBTITLE_POSITION_CANDIDATES if hook_mode else SUBTITLE_POSITION_CANDIDATES)
    if name not in candidates:
        raise ValueError(f"unknown subtitle position: {name}")
    return int(VIDEO_HEIGHT * candidates[name])


def assess_subtitle_placement(video_clip, current_position="bottom", hook_mode=False, excluded_positions=None):
    risks = subtitle_position_risks(video_clip, hook_mode=hook_mode)
    ceiling = HOOK_SUBTITLE_SAFE_CEILING if hook_mode else SUBTITLE_SAFE_CEILING
    excluded = set(excluded_positions or [])
    current_risk = risks.get(current_position)
    safe = [(name, risk) for name, risk in risks.items() if risk <= ceiling and name not in excluded]
    safe.sort(key=lambda item: (item[1], item[0]))
    all_unsafe = bool(risks) and not any(risk <= ceiling for risk in risks.values())
    recommended = None
    if current_risk is not None and current_risk > ceiling and safe:
        best_name, best_risk = safe[0]
        if current_risk - best_risk >= SUBTITLE_RELOCATION_MIN_MARGIN:
            recommended = best_name
    obstruction = recommended is not None
    return {
        "selected_position": current_position,
        "selected_risk": current_risk,
        "safe_ceiling": ceiling,
        "relocation_min_margin": SUBTITLE_RELOCATION_MIN_MARGIN,
        "alternatives": dict(risks),
        "safe_alternative_available": obstruction,
        "recommended_position": recommended,
        "subtitle_obstruction": obstruction,
        "subtitle_all_positions_unsafe": all_unsafe,
        "hook_mode": bool(hook_mode),
    }
