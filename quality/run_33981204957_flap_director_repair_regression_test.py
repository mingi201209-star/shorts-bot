"""Run 33981204957 / 34460549351 flap Director repetition-repair counterexamples.

Production evidence: the verified-still rescue succeeded, Final Visual Semantic QA
and Visual Diversity passed, then Director correctly rejected three uses of the
same physical still. Its selective repair re-entered the flap family with the
unchanged 2/2 still-generation budget.

Run 34006225743 proved the deterministic FLAP_CAMBER repair and explicit
FLAP_TRAILING_EDGE_IDENTITY split. Run 34460549351 exposed two remaining bounded
problems: the opening carries explicit flap deployment-stage semantics not covered
by either prior template, and a three-use repetition group only needs one scene
replacement even though the old repair planner selected two before re-running QA.

This regression proves the minimum repair cardinality plus a genuinely distinct,
fact-bounded FLAP_DEPLOYMENT deterministic asset without changing Director
thresholds, still budgets, transform budgets, normal source-use caps, or physical
lineage.
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


SCENE1 = {
    "scene_id": "1",
    "role": "hook",
    "text": "플랩이 이착륙 때 펼쳐지는 모습을 먼저 보여줍니다.",
    "keyword": "aircraft wing flap trailing-edge deployment stage 1",
    "visual_goal": "aircraft trailing-edge flap deployment stage 1",
}

SCENE3 = {
    "scene_id": "3",
    "role": "causal_clue",
    "text": "플랩을 펼치면 날개 형상이 바뀌어 양력과 항력 조건이 달라집니다.",
    "keyword": "wing flap aircraft trailing-edge camber lift drag",
    "visual_goal": "aircraft trailing-edge flap camber lift drag",
}

# Exact live payload family from Run 34006225743. The text intentionally
# includes "고양력" while keyword carries explicit identity semantics.
SCENE4 = {
    "scene_id": "4",
    "role": "reveal",
    "text": "플랩은 항공기 날개 뒤쪽에 붙는 고양력 장치입니다.",
    "keyword": "aircraft wing flap trailing-edge trailing edge identity",
    "visual_goal": "플랩의 위치와 기능 설명",
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
    from quality.final_visual_director import director_qa, selective_repair_plan

    vx = importlib.reload(vx)
    vx.reset_visual_explanation_budget()

    # The Run 34460549351 opening gets its own state-change visual. Existing
    # camber/identity routing must stay unchanged despite shared flap wording.
    plan1 = vx.plan_explanation(SCENE1)
    plan3 = vx.plan_explanation(SCENE3)
    plan4 = vx.plan_explanation(SCENE4)
    assert plan1 and plan1["template"] == "FLAP_DEPLOYMENT", plan1
    assert plan3 and plan3["template"] == "FLAP_CAMBER", plan3
    assert plan4 and plan4["template"] == "FLAP_TRAILING_EDGE_IDENTITY", plan4
    assert vx.annotation_fact_safe(SCENE1, plan1) is True
    assert vx.annotation_fact_safe(SCENE3, plan3) is True
    assert vx.annotation_fact_safe(SCENE4, plan4) is True
    assert vx.plan_explanation({"keyword": "aircraft landing gear wheel", "text": "착륙 장치"}) is None

    # Flap Director repair must not wrap the already repeated physical still in
    # a fresh source id. It must force genuinely distinct explanatory_2d assets.
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
            # Reproduce the production budget shape: two existing explanatory
            # transforms have already been consumed before Director repairs the
            # opening. FLAP_DEPLOYMENT must succeed in the third and final slot.
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
            out1 = vx.generate_visual_explanation_fallback(
                SCENE1,
                output_path=tmp / "scene1-deployment-repair.mp4",
                duration=5.0,
                trigger_reason="director_repetition_repair",
            )
            exhausted = vx.generate_visual_explanation_fallback(
                SCENE1,
                output_path=tmp / "must-not-render.mp4",
                duration=5.0,
                trigger_reason="director_repetition_repair",
            )
    finally:
        vx._render_clip = original_render
        vx._RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET = original_cached

    assert out1 and out3 and out4
    assert out1["source_type"] == out3["source_type"] == out4["source_type"] == "explanatory_2d"
    assert out1["mode"] == out3["mode"] == out4["mode"] == "EXPLANATORY_2D"
    assert out1["source_asset_id"].startswith("deterministic-explanatory:FLAP_DEPLOYMENT:")
    assert out3["source_asset_id"].startswith("deterministic-explanatory:FLAP_CAMBER:")
    assert out4["source_asset_id"].startswith("deterministic-explanatory:FLAP_TRAILING_EDGE_IDENTITY:")
    assert len({out1["source_asset_id"], out3["source_asset_id"], out4["source_asset_id"]}) == 3
    assert len({out1["source_id"], out3["source_id"], out4["source_id"]}) == 3
    assert vx.visual_explanation_transform_count() == vx.MAX_EXPLANATION_TRANSFORMS_PER_VIDEO == 3
    assert exhausted is None
    assert still.still_image_generation_count() == generation_before == still.STILL_IMAGE_MAX_PER_VIDEO == 2

    # Preserve the Director hard repetition rule: three uses still FAIL. Repair
    # planning now asks for only N-2 replacements because that is the minimum
    # needed to make the exact same hard rule pass on the next QA round.
    repeated = [
        {"scene_index": i, "role": "setup", "source_id": "still-repeat", "scores": _passing_scores()}
        for i in range(3)
    ]
    repeated_qa = director_qa(repeated)
    assert repeated_qa["overall_pass"] is False
    assert all(issue["type"] == "repetition_risk" for issue in repeated_qa["issues"])
    assert all(issue["source_id"] == "still-repeat" for issue in repeated_qa["issues"])
    assert all(issue["repetition_count"] == 3 for issue in repeated_qa["issues"])
    repair3 = selective_repair_plan(repeated_qa, 0)
    assert repair3["status"] == "REPAIR"
    assert repair3["scene_indexes"] == [0], repair3

    repeated4 = [
        {"scene_index": i, "role": "setup", "source_id": "still-repeat-4", "scores": _passing_scores()}
        for i in range(4)
    ]
    repair4 = selective_repair_plan(director_qa(repeated4), 0)
    assert repair4["scene_indexes"] == [0, 1], repair4

    # Exact three-use shape: replacing only one repeated scene with the new
    # deployment asset drops the old source to two uses, so Director passes and
    # no second transform slot is required.
    repaired_once = [
        {"scene_index": 0, "role": "hook", "source_id": out1["source_id"], "scores": _passing_scores()},
        {"scene_index": 1, "role": "setup", "source_id": "still-repeat", "scores": _passing_scores()},
        {"scene_index": 2, "role": "setup", "source_id": "still-repeat", "scores": _passing_scores()},
        {"scene_index": 3, "role": "mechanism", "source_id": out3["source_id"], "scores": _passing_scores()},
        {"scene_index": 4, "role": "result", "source_id": out4["source_id"], "scores": _passing_scores()},
    ]
    repaired_qa = director_qa(repaired_once)
    assert repaired_qa["overall_pass"] is True, repaired_qa
    assert not repaired_qa["issues"], repaired_qa

    print("RUN 33981204957 / 34460549351 FLAP DIRECTOR REPAIR REGRESSION: PASS")


if __name__ == "__main__":
    main()
