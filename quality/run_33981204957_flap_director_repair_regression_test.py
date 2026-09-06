"""Run 33981204957 flap Director repetition-repair counterexample.

Production evidence: the verified-still rescue succeeded, Final Visual Semantic QA
and Visual Diversity passed, then Director correctly rejected three uses of the
same physical still. Its selective repair re-entered Scene 3 with the unchanged
2/2 still-generation budget and the existing Visual Explanation layer failed
closed as unsupported_or_fact_unsafe.

This regression proves the repair can obtain genuinely distinct deterministic
2D flap assets without changing Director thresholds, still budgets, normal
source-use caps, or physical lineage.
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_33981204957_flap_director_repair_hotfix import main as install_hotfix


SCENE3 = {
    "scene_id": "3",
    "role": "causal_clue",
    "text": "플랩을 펼치면 날개 형상이 바뀌어 양력과 항력 조건이 달라집니다.",
    "keyword": "wing flap aircraft trailing-edge camber lift drag",
    "visual_goal": "aircraft trailing-edge flap camber lift drag",
}

SCENE4 = {
    "scene_id": "4",
    "role": "reveal",
    "text": "그 장치는 날개 뒤쪽의 플랩입니다.",
    "keyword": "aircraft wing flap trailing-edge trailing edge identity",
    "visual_goal": "aircraft wing trailing edge flap identity",
}


def _passing_scores():
    return {
        "semantic_match": 9.0,
        "explanatory_power": 9.0,
        "subject_prominence": 9.0,
        "mobile_clarity": 9.0,
        "hook_visual_strength": 9.0,
        "payoff_visual_strength": 9.0,
        "artifact_risk": 1.0,
        "obstruction_risk": 1.0,
    }


def main():
    install_hotfix()

    import video.visual_explanation as vx
    import video.still_image_fallback as still
    from quality.final_visual_director import director_qa

    vx = importlib.reload(vx)
    vx.reset_visual_explanation_budget()

    # Exact production Scene 3/4 family must be supported, while unrelated
    # unsupported subjects still delegate to the existing fail-closed planner.
    plan3 = vx.plan_explanation(SCENE3)
    plan4 = vx.plan_explanation(SCENE4)
    assert plan3 and plan3["template"] == "FLAP_CAMBER", plan3
    assert plan4 and plan4["template"] == "FLAP_TRAILING_EDGE_IDENTITY", plan4
    assert vx.annotation_fact_safe(SCENE3, plan3) is True
    assert vx.annotation_fact_safe(SCENE4, plan4) is True
    assert vx.plan_explanation({"keyword": "aircraft landing gear wheel", "text": "착륙 장치"}) is None

    # Flap Director repair must not wrap the already repeated physical still in
    # a fresh source id. It must force the genuinely distinct explanatory_2d
    # branch, so the cached-still path is forbidden for these two plans.
    original_cached = vx._RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET
    vx._RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET = lambda scene: (_ for _ in ()).throw(
        AssertionError("flap Director repair must not reuse the repeated physical still")
    )

    # No real render is needed for this semantic/lineage regression.
    original_render = vx._render_clip
    vx._render_clip = lambda base, output_path, duration, plan: Path(output_path).write_bytes(
        (plan["template"] + "-deterministic-2d").encode("utf-8")
    )

    still.reset_still_image_budget()
    still._GENERATION_COUNT = still.STILL_IMAGE_MAX_PER_VIDEO
    generation_before = still.still_image_generation_count()

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp = Path(temp_dir)
            out3 = vx.generate_visual_explanation_fallback(
                SCENE3,
                output_path=tmp / "scene3-repair.mp4",
                duration=5.0,
                trigger_reason="director_repetition_repair",
            )
            out4 = vx.generate_visual_explanation_fallback(
                SCENE4,
                output_path=tmp / "scene4-repair.mp4",
                duration=5.0,
                trigger_reason="director_repetition_repair",
            )
    finally:
        vx._render_clip = original_render
        vx._RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET = original_cached

    assert out3 and out4
    assert out3["source_type"] == out4["source_type"] == "explanatory_2d"
    assert out3["mode"] == out4["mode"] == "EXPLANATORY_2D"
    assert out3["source_asset_id"].startswith("deterministic-explanatory:FLAP_CAMBER:")
    assert out4["source_asset_id"].startswith("deterministic-explanatory:FLAP_TRAILING_EDGE_IDENTITY:")
    assert out3["source_asset_id"] != out4["source_asset_id"]
    assert out3["source_id"] != out4["source_id"]
    assert still.still_image_generation_count() == generation_before == still.STILL_IMAGE_MAX_PER_VIDEO == 2

    # Preserve the Director's existing hard repetition behavior: three uses of
    # one physical source still FAIL. The repair passes only because it replaces
    # two repeated scenes with genuinely distinct deterministic physical assets.
    repeated = [
        {"scene_index": i, "role": "setup", "source_id": "still-repeat", "scores": _passing_scores()}
        for i in range(3)
    ]
    repeated_qa = director_qa(repeated)
    assert repeated_qa["overall_pass"] is False
    assert all(issue["type"] == "repetition_risk" for issue in repeated_qa["issues"])

    repaired = [
        {"scene_index": 0, "role": "hook", "source_id": "still-a", "scores": _passing_scores()},
        {"scene_index": 1, "role": "setup", "source_id": "still-a", "scores": _passing_scores()},
        {"scene_index": 2, "role": "cause", "source_id": out3["source_id"], "scores": _passing_scores()},
        {"scene_index": 3, "role": "mechanism", "source_id": out4["source_id"], "scores": _passing_scores()},
        {"scene_index": 4, "role": "result", "source_id": "still-b", "scores": _passing_scores()},
    ]
    repaired_qa = director_qa(repaired)
    assert repaired_qa["overall_pass"] is True, repaired_qa
    assert not repaired_qa["issues"], repaired_qa

    print("RUN 33981204957 FLAP DIRECTOR REPAIR REGRESSION: PASS")


if __name__ == "__main__":
    main()
