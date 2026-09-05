"""Run 33977099845 verified-still budget rescue counterexamples.

This regression is intended to run after the exact production hotfix composition,
including ci_run_33977099845_verified_still_rescue_hotfix.py.
"""
from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import quality.visual_diversity_preflight as diversity
import video.still_image_fallback as still


SOURCE_ID = "still-run33977099845-flap-proof"
FLAP_SIGNATURE = ("aircraft", "wing")


def _fake_motion(image_path, output_path, duration, presentation=None):
    assert Path(image_path).is_file()
    assert float(duration) > 0
    if presentation is not None:
        assert presentation.get("presentation_id") == "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1"
        assert float(presentation.get("zoom_max", 0)) <= 1.12
        assert presentation.get("pan_x") == "center"
        assert presentation.get("pan_y") == "center"
    Path(output_path).write_bytes(b"verified-motion")


def _seed_verified_flap(image_path: Path, *, uses=2):
    still.reset_still_image_budget()
    still._GENERATION_COUNT = still.STILL_IMAGE_MAX_PER_VIDEO
    still._VERIFIED_STILL_CACHE[FLAP_SIGNATURE] = {
        "image_path": str(image_path),
        "provider": "openai_image",
        "source_id": SOURCE_ID,
        "verification_evidence": {
            "visible_components": ["aircraft", "wing", "flap"],
            "factual_visual_contradiction": False,
        },
    }
    still._VERIFIED_SOURCE_USE_COUNTS[SOURCE_ID] = uses


def _scene5(*, verify=True):
    return {
        "scene_id": "5",
        "role": "payoff",
        "text": "플랩은 필요할 때 전개해 낮은 착륙 속도를 가능하게 합니다.",
        "keyword": "aircraft trailing-edge flap low landing speed tradeoff",
        "visual_goal": "플랩의 작동과 비행 성능",
        "_test_verify": verify,
    }


def _install_test_doubles():
    still._motion_clip = _fake_motion
    still.is_physical_asset_excluded = lambda source_id: False

    def verify(scene, output_path):
        passed = bool(scene.get("_test_verify", True))
        return passed, {
            "visible_components": ["aircraft", "wing", "flap"] if passed else ["aircraft", "wing"],
            "factual_visual_contradiction": not passed,
            "subject_visibility": 9.0 if passed else 4.0,
        }

    still._verify_motion_clip = verify

    def no_generation(_scene):
        raise AssertionError("budget rescue must not generate another still")

    still._generate_image = no_generation


def case_a_budget_exhausted_verified_reuse(tmp: Path):
    image_path = tmp / "flap.png"
    image_path.write_bytes(b"flap-proof")
    _seed_verified_flap(image_path, uses=2)
    _install_test_doubles()

    assert "presentation" in inspect.signature(still._motion_clip).parameters
    output = tmp / "scene5.mp4"
    result = still.generate_still_motion_fallback(
        _scene5(verify=True),
        output_path=output,
        duration=8.5,
        trigger_reason="no_semantically_safe_stock",
    )
    assert result, "compatible verified flap asset must rescue Scene 5"
    assert result["source_id"] == SOURCE_ID
    assert result["source_asset_id"] == SOURCE_ID
    assert result["presentation_id"] == "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1"
    assert result["template_type"] == "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1"
    assert result["verification_evidence_reused"] is False
    assert result["current_scene_verification"]["factual_visual_contradiction"] is False
    assert still.still_image_generation_count() == still.STILL_IMAGE_MAX_PER_VIDEO == 2
    assert still._VERIFIED_RESCUE_USE_COUNTS[SOURCE_ID] == 1
    assert output.is_file()

    # The exceptional rescue is source-bounded to exactly one extra use.
    second = still.generate_still_motion_fallback(
        _scene5(verify=True),
        output_path=tmp / "scene5-again.mp4",
        duration=8.5,
        trigger_reason="no_semantically_safe_stock",
    )
    assert second is None
    print("CASE A budget-exhausted compatible verified reuse: PASS")


def case_b_semantic_or_component_mismatch_fails_closed(tmp: Path):
    image_path = tmp / "flap-b.png"
    image_path.write_bytes(b"flap-proof")
    _seed_verified_flap(image_path, uses=2)
    _install_test_doubles()

    output = tmp / "scene5-reject.mp4"
    result = still.generate_still_motion_fallback(
        _scene5(verify=False),
        output_path=output,
        duration=8.5,
        trigger_reason="no_semantically_safe_stock",
    )
    assert result is None
    assert not output.exists()
    assert still._VERIFIED_RESCUE_USE_COUNTS.get(SOURCE_ID, 0) == 0
    assert still.still_image_generation_count() == 2
    print("CASE B incompatible current-scene verification fails closed: PASS")


def case_c_lineage_truth_and_diversity_variant():
    scenes = [
        {"role": "phenomenon", "text": "플랩이 펼쳐집니다."},
        {"role": "mechanism", "text": "플랩이 날개 형상을 바꿉니다."},
        {"role": "payoff", "text": "플랩은 낮은 착륙 속도를 돕습니다."},
    ]
    lineage = [
        {
            "scene_index": 0,
            "source_id": SOURCE_ID,
            "source_asset_id": SOURCE_ID,
            "mode": "GENERATED_STILL_MOTION_VERIFIED",
        },
        {
            "scene_index": 1,
            "source_id": SOURCE_ID,
            "source_asset_id": SOURCE_ID,
            "mode": "REUSED_VERIFIED_STILL_MOTION",
        },
        {
            "scene_index": 2,
            "source_id": SOURCE_ID,
            "source_asset_id": SOURCE_ID,
            "mode": "REUSED_VERIFIED_STILL_MOTION",
            "template_type": "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1",
            "presentation_id": "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1",
        },
    ]
    assert {diversity.physical_asset_identity(item) for item in lineage} == {SOURCE_ID}
    result = diversity.evaluate_visual_diversity(scenes, lineage)
    assert result["pass"] is True, result
    group = result["repetition_groups"][0]
    variants = [member["variant"] for member in group["members"]]
    assert variants.count("raw_physical_asset") == 2
    assert variants.count("presentation:verified_flap_feature_inspection_center_v1") == 1
    assert group["asset_id"] == SOURCE_ID
    print("CASE C physical lineage preserved; bounded presentation is not a fake asset: PASS")


def case_d_failed_generation_verification_never_cached(tmp: Path):
    still.reset_still_image_budget()
    still._motion_clip = _fake_motion
    still._verify_motion_clip = lambda scene, output_path: (
        False,
        {
            "visible_components": ["aircraft", "wing"],
            "factual_visual_contradiction": True,
            "subject_visibility": 4.0,
        },
    )
    still._generate_image = lambda scene: (b"not-a-real-png-needed-by-test-double", "run33977099845-test-prompt")
    result = still.generate_still_motion_fallback(
        {
            "scene_id": "1",
            "role": "phenomenon",
            "keyword": "aircraft wing flap deployment",
            "visual_goal": "플랩 전개",
            "text": "플랩이 펼쳐집니다.",
        },
        output_path=tmp / "failed-vision.mp4",
        duration=4.0,
        trigger_reason="no_semantically_safe_stock",
    )
    assert result is None
    assert not still._VERIFIED_STILL_CACHE
    print("CASE D Vision-failed generated still never enters verified cache: PASS")


def case_e_cross_subject_reuse_blocked(tmp: Path):
    image_path = tmp / "flap-e.png"
    image_path.write_bytes(b"flap-proof")
    _seed_verified_flap(image_path, uses=2)
    _install_test_doubles()
    landing_gear_scene = {
        "scene_id": "5",
        "role": "payoff",
        "keyword": "aircraft landing gear wheel touchdown",
        "visual_goal": "착륙 장치가 활주로에 닿는 모습",
        "text": "착륙 장치는 충격을 흡수합니다.",
        "_test_verify": True,
    }
    result = still.generate_still_motion_fallback(
        landing_gear_scene,
        output_path=tmp / "cross-subject.mp4",
        duration=5.0,
        trigger_reason="no_semantically_safe_stock",
    )
    assert result is None
    assert still._VERIFIED_RESCUE_USE_COUNTS.get(SOURCE_ID, 0) == 0
    print("CASE E cross-subject verified reuse blocked: PASS")


def main():
    assert still.STILL_IMAGE_MAX_PER_VIDEO == 2
    assert still.MAX_INFORMATION_USES_PER_PHYSICAL_STILL == 2
    assert hasattr(still, "_reuse_verified_budget_rescue")
    assert hasattr(still, "_VERIFIED_RESCUE_USE_COUNTS")
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp = Path(temp_dir)
        case_a_budget_exhausted_verified_reuse(tmp)
        case_b_semantic_or_component_mismatch_fails_closed(tmp)
        case_c_lineage_truth_and_diversity_variant()
        case_d_failed_generation_verification_never_cached(tmp)
        case_e_cross_subject_reuse_blocked(tmp)
    print("RUN 33977099845 VERIFIED STILL RESCUE REGRESSION: PASS")


if __name__ == "__main__":
    main()
