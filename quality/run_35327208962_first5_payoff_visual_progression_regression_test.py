"""Regression for Run 35327208962 visual progression completion."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_35327208962_first5_payoff_visual_progression_hotfix import (
    ENGINE_MARKER,
    STILL_MARKER,
    patch_still_fallback,
    patch_video_engine,
)


ENGINE_FIXTURE = r'''
def create_scene(idx, item, create_voice):
        elif idx == 1:

            try:

                from video.hook_visual import (
                    fetch_early_retention_pexels_video,
                )

                video_url = (
                    fetch_early_retention_pexels_video(
                        item
                    )
                )

            except Exception as e:

                print(
                    "⚠️ First-5s strict visual selector 실패, "
                    "기존 Pexels 경로로 fallback: "
                    f"{e}"
                )

                video_url = (
                    fetch_pexels_video(
                        keyword
                    )
                )

'''

STILL_FIXTURE = r'''
STILL_IMAGE_MAX_PER_VIDEO = 2
_GENERATION_COUNT = 1
_VERIFIED_SOURCE_USE_COUNTS = {"still-a": 1}

def _scene_id(scene):
    return str(scene.get("id") or "unknown")

def verified_source_use_count(source_id):
    return int(_VERIFIED_SOURCE_USE_COUNTS.get(str(source_id or ""), 0))

def _source_reuse_allowed(source_id, scene):
    return verified_source_use_count(source_id) < 2
'''


def run():
    engine = patch_video_engine(ENGINE_FIXTURE)
    assert ENGINE_MARKER in engine
    assert engine == patch_video_engine(engine)
    assert "fetch_hook_pexels_video" in engine
    assert "fetch_early_retention_pexels_video" not in engine
    assert "fetch_pexels_video(\n                        keyword" not in engine
    assert "video_url = None" in engine
    print("CASE A Scene 2 uses bounded frame verifier and cannot reopen generic stock: PASS")

    still = patch_still_fallback(STILL_FIXTURE)
    assert STILL_MARKER in still
    assert still == patch_still_fallback(still)
    ns = {}
    exec(compile(still, "synthetic-still.py", "exec"), ns)

    # One existing use + one free generation slot: question/payoff prefer a new
    # verified still rather than repeating the opening physical asset.
    assert ns["_source_reuse_allowed"](
        "still-a", {"role": "question", "id": 2}
    ) is False
    assert ns["_source_reuse_allowed"](
        "still-a", {"role": "payoff", "id": 5}
    ) is False
    assert ns["_source_reuse_allowed"](
        "still-a", {"causal_role": "primary_result", "id": 5}
    ) is False
    print("CASE B question/payoff prefer fresh still while existing budget remains: PASS")

    # Mechanism/setup behavior stays unchanged.
    assert ns["_source_reuse_allowed"](
        "still-a", {"role": "mechanism", "id": 3}
    ) is True

    # Never trade reliability for novelty after the existing generation budget
    # is exhausted: verified reuse becomes available exactly as before.
    ns["_GENERATION_COUNT"] = 2
    assert ns["_source_reuse_allowed"](
        "still-a", {"role": "question", "id": 2}
    ) is True
    assert ns["_source_reuse_allowed"](
        "still-a", {"role": "payoff", "id": 5}
    ) is True
    print("CASE C budget-exhausted verified reuse remains available: PASS")

    source = Path(
        "ci_run_35327208962_first5_payoff_visual_progression_hotfix.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "HOOK_VISUAL_MIN_SCORE =",
        "HOOK_SUBJECT_DOMINANCE_MIN =",
    )
    for token in forbidden:
        # The constant name may be read, but this installer must not assign it.
        if token == "STILL_IMAGE_MAX_PER_VIDEO =":
            assert token not in source
        else:
            assert token not in source, token

    print("RUN 35327208962 FIRST5/PAYOFF VISUAL PROGRESSION REGRESSION: PASS")


if __name__ == "__main__":
    run()
