import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.final_visual_semantic_qa import (
    record_final_visual_scene,
    reset_final_visual_semantic_report,
    validate_final_visual_semantic_qa,
)
from quality.visual_semantic_contract import phenomenon_preserving_query


def _scene():
    return {
        "text": "비행 중 날개 끝이 위로 휘는 건 실제 하중을 받는 날개의 탄성 변형입니다.",
        "keyword": "aircraft wing stage 1",
        "visual_goal": "날개가 하중 때문에 휘어지는 모습",
    }


def _expect_failure(scenes, reason):
    try:
        validate_final_visual_semantic_qa(scenes)
    except RuntimeError:
        report = Path("final_visual_semantic_qa.json").read_text(encoding="utf-8")
        assert reason in report, report
        return
    raise AssertionError("final visual semantic QA should fail closed")


def case_a_retrieval_query_preserves_phenomenon():
    query = phenomenon_preserving_query(_scene(), base_query="aircraft wing stage 1")
    assert query.startswith("aircraft wing stage 1"), query
    assert "flex" in query and "bending" in query and "deformation" in query, query
    print("CASE A phenomenon-preserving query keeps deformation evidence: PASS")


def case_b_verified_still_evidence_reaches_final_qa(tmp):
    old = os.getcwd()
    try:
        os.chdir(tmp)
        scenes = [_scene()]
        reset_final_visual_semantic_report()
        record_final_visual_scene(0, "aircraft wing flex bending deformation", {
            "accepted": True,
            "mode": "GENERATED_STILL_MOTION_VERIFIED",
            "tier": 2,
            "visual_state": "TRUE",
            "anchor_matched": 2,
            "anchor_total": 2,
            "provider": "openai_image",
            "source_id": "still-wing-flex",
            "source_asset_id": "still-wing-flex",
            "metadata": "verified generated still",
            "visible_components": ["aircraft", "wing"],
            "visible_subject_groups": {"aircraft": True, "wing": True},
            "current_scene_verification": {
                "pass": True,
                "reason": "The aircraft wing is visibly flexing with bending deformation under load.",
            },
        })
        assert validate_final_visual_semantic_qa(scenes)["status"] == "PASS"
    finally:
        os.chdir(old)
    print("CASE B verified still structured evidence reaches final QA: PASS")


def case_c_verified_still_without_action_evidence_fails(tmp):
    old = os.getcwd()
    try:
        os.chdir(tmp)
        scenes = [_scene()]
        reset_final_visual_semantic_report()
        record_final_visual_scene(0, "aircraft wing flex bending deformation", {
            "accepted": True,
            "mode": "GENERATED_STILL_MOTION_VERIFIED",
            "tier": 2,
            "visual_state": "TRUE",
            "anchor_matched": 2,
            "anchor_total": 2,
            "provider": "openai_image",
            "source_id": "still-static-wing",
            "source_asset_id": "still-static-wing",
            "metadata": "verified generated still",
            "visible_components": ["aircraft", "wing"],
            "visible_subject_groups": {"aircraft": True, "wing": True},
            "current_scene_verification": {
                "pass": False,
                "reason": "The aircraft and wing are visible, but no observable action is present.",
            },
        })
        _expect_failure(scenes, "missing_required_visual_evidence")
    finally:
        os.chdir(old)
    print("CASE C visible subject without phenomenon evidence fails: PASS")


def main():
    old = os.getcwd()
    case_a_retrieval_query_preserves_phenomenon()
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_b_verified_still_evidence_reaches_final_qa(temp_dir)
        with tempfile.TemporaryDirectory() as temp_dir:
            case_c_verified_still_without_action_evidence_fails(temp_dir)
    finally:
        os.chdir(old)
    print("RUN 35419810434 VISUAL LINEAGE REGRESSION: PASS")


if __name__ == "__main__":
    main()
