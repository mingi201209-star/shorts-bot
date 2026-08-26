import numpy as np

from quality.subtitle_safety import (
    SUBTITLE_SAFE_CEILING,
    SUBTITLE_RELOCATION_MIN_MARGIN,
    assess_subtitle_placement,
    subtitle_position_risks,
)
from video.subtitle_engine import VIDEO_HEIGHT, VIDEO_WIDTH, _visual_region_score


class Clip:
    duration = 1.0
    def __init__(self, frame): self.frame = frame
    def get_frame(self, _): return self.frame


def frame(fill=150):
    return np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), fill, dtype=np.uint8)


def checker():
    yy, xx = np.indices((VIDEO_HEIGHT, VIDEO_WIDTH))
    mask = ((xx // 8 + yy // 8) % 2) == 0
    out = np.empty((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    out[mask] = (235, 235, 235); out[~mask] = (20, 20, 20)
    return out


def moderate():
    rng = np.random.default_rng(7)
    mono = np.clip(128 + rng.normal(0, 22, (VIDEO_HEIGHT, VIDEO_WIDTH, 1)), 0, 255).astype(np.uint8)
    return np.repeat(mono, 3, axis=2)


def banded(bottom_busy=False, all_busy=False, hook=False):
    out = frame()
    if all_busy: return checker()
    if bottom_busy:
        busy = checker()
        out[int(VIDEO_HEIGHT * .68):] = busy[int(VIDEO_HEIGHT * .68):]
    if hook:
        busy = checker(); out[:] = busy
        out[int(VIDEO_HEIGHT * .08):int(VIDEO_HEIGHT * .08)+220] = 150
    return out


def log_case(name, clip, hook=False):
    risks = subtitle_position_risks(clip, hook_mode=hook)
    for position, risk in risks.items():
        print(f"[SubtitleCalibration] case={name} position={position} risk={risk:.3f}")
    return risks


def main():
    simple = log_case("simple_background", Clip(frame()))
    moderate_r = log_case("moderate_background", Clip(moderate()))
    busy = log_case("busy_component", Clip(checker()))
    skin = frame(); skin[:] = (180, 100, 60)
    log_case("skin_like_occupied", Clip(skin))
    assert max(simple.values()) <= SUBTITLE_SAFE_CEILING
    assert max(moderate_r.values()) <= SUBTITLE_SAFE_CEILING
    assert min(busy.values()) > SUBTITLE_SAFE_CEILING

    d = Clip(banded(bottom_busy=True))
    bottom_busy_risks = log_case("bottom_busy_top_clear", d)
    result = assess_subtitle_placement(d, "bottom")
    safest_clear_position = min(
        (risk, position)
        for position, risk in bottom_busy_risks.items()
        if risk <= SUBTITLE_SAFE_CEILING
    )[1]
    assert result["subtitle_obstruction"]
    assert result["recommended_position"] == safest_clear_position
    assert result["recommended_position"] != "bottom"

    # A safe current position is stable even when another candidate is slightly lower.
    result = assess_subtitle_placement(Clip(frame()), "bottom")
    assert not result["subtitle_obstruction"] and result["recommended_position"] is None

    result = assess_subtitle_placement(Clip(banded(all_busy=True)), "bottom")
    assert result["subtitle_all_positions_unsafe"] and not result["safe_alternative_available"]

    h = Clip(banded(hook=True))
    hook_risks = log_case("hook_one_safe", h, hook=True)
    assert set(hook_risks) == {"top", "upper", "lower", "bottom"}
    assert assess_subtitle_placement(h, "bottom", hook_mode=True)["recommended_position"] == "top"

    # Excluding the failed position during a repair round prevents immediate oscillation.
    moved = assess_subtitle_placement(d, "top", excluded_positions={"bottom"})
    assert not moved["subtitle_obstruction"]
    assert SUBTITLE_RELOCATION_MIN_MARGIN > .03
    print(f"[SubtitleCalibration] safe_ceiling={SUBTITLE_SAFE_CEILING:.3f} min_margin={SUBTITLE_RELOCATION_MIN_MARGIN:.3f} PASS")


if __name__ == "__main__": main()
