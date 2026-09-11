"""Production-composed regression for AIRCRAFT_WINDOW_STRESS_V1.

Run 34625637738 was machine-green but human review found two visual escapes:
UNKNOWN aircraft-window stock was accepted for the opening and the explanatory
section occupied only a small repeated panel. This suite composes the real
hotfix chain, verifies claim-specific large presentations, and verifies the
closed aircraft-window stock gate without adding network/LLM/Vision calls.
"""
from __future__ import annotations

import runpy
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SCRATCH = Path(tempfile.mkdtemp(prefix="gde_renderer_"))
_REPO = _SCRATCH / "repo"
shutil.copytree(ROOT, _REPO, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
sys.path.insert(0, str(_REPO))

_CHAIN = [
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_aviation_candidate_specificity_hotfix.py", "ci_aviation_context_signature_compat_hotfix.py",
    "ci_aviation_specificity_output_repair_hotfix.py", "ci_aviation_specificity_projection_hotfix.py",
    "ci_candidate_grounded_recovery_hotfix.py", "ci_growth_candidate_shadow_hotfix.py",
    "ci_final_render_content_integrity_hotfix.py", "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py", "ci_design_causality_hotfix.py",
    "ci_query_semantic_integrity_hotfix.py", "ci_concrete_visual_evidence_hotfix.py",
    "ci_visible_evidence_provenance_hotfix.py", "ci_hook_production_parity_hotfix.py",
    "ci_hook_fallback_quality_floor_hotfix.py", "ci_ai_visual_fallback_hotfix.py",
    "ci_ai_visual_mechanism_fallback_hotfix.py", "ci_problem_solution_narrative_hotfix.py",
    "ci_causal_information_progression_hotfix.py", "ci_retention_structure_experiment_hotfix.py",
    "ci_subscriber_conversion_hotfix.py", "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py", "ci_adaptive_scene_count_hotfix.py",
    "ci_general_scene_visual_parity_hotfix.py", "ci_script_validation_recovery_hotfix.py",
    "ci_script_v2_visual_goal_hotfix.py", "ci_script_v2_gunggeum_formal_ending_hotfix.py",
    "ci_final_visual_semantic_qa_hotfix.py", "ci_cross_process_video_dedupe_hotfix.py",
    "ci_writer_observable_opening_hotfix.py",
    "ci_grounded_deterministic_explanation_hotfix.py",
]

import subprocess  # noqa: E402

for script in _CHAIN:
    subprocess.run([sys.executable, script], check=True, cwd=_REPO, capture_output=True)

vx = runpy.run_module("video.visual_explanation", run_name="video.visual_explanation")
plan_explanation = vx["plan_explanation"]
annotation_fact_safe = vx["annotation_fact_safe"]
_draw_concept_panel = vx["_draw_concept_panel"]
_apply_subtle_inspection = vx["_gde_apply_subtle_inspection"]
reset_visual_explanation_budget = vx["reset_visual_explanation_budget"]

_FAA_SOURCE = "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"
_CANONICAL = "modern aircraft passenger window with rounded/oval corners"


def _window_scene(**overrides):
    scene = {
        "scene_id": 5,
        "role": "payoff",
        "text": "각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 이어질 수 있었습니다.",
        "keyword": "modern aircraft window squarish fatigue rupture comet",
        "_canonical_visual_supply": {
            "canonical_subject": _CANONICAL,
            "grounding_source": _FAA_SOURCE,
        },
    }
    scene.update(overrides)
    return scene


def _claim_scene(claim_id):
    if claim_id == "squarish_window_stress_concentration":
        return _window_scene(
            owned_claim_id=claim_id,
            causal_role="constraint",
            role="causal_clue",
            text="각진 창문 모서리에는 높은 응력이 집중됐습니다.",
            keyword="aircraft window squarish corner stress concentration",
        )
    if claim_id == "rounded_window_stress_distribution":
        return _window_scene(
            owned_claim_id=claim_id,
            causal_role="mechanism_change",
            role="reveal",
            text="둥근 모서리에서는 응력이 곡선을 따라 흘러 한 지점에 쌓이는 것을 줄입니다.",
            keyword="aircraft window rounded corner stress distribution",
        )
    return _window_scene(
        owned_claim_id=claim_id,
        causal_role="primary_result",
        role="payoff",
    )


def test_positive_plan_and_render():
    reset_visual_explanation_budget()
    scene = _window_scene()
    plan = plan_explanation(scene)
    assert plan is not None
    assert plan["template"] == "AIRCRAFT_WINDOW_STRESS_V1"
    assert plan["evidence_source"] == "TRUSTED_GROUNDING"
    assert plan["motion_profile"] == "SUBTLE_INSPECTION"
    assert plan["presentation_variant"] == "LEFT_FATIGUE_PAYOFF"
    assert annotation_fact_safe(scene, plan) is True

    from PIL import Image
    frame = Image.new("RGBA", (1080, 1920), (28, 31, 38, 255))
    out = _draw_concept_panel(frame, plan, 0.4)
    assert out.size == (1080, 1920)


def test_claims_have_large_distinct_presentations():
    claims = [
        "squarish_window_stress_concentration",
        "rounded_window_stress_distribution",
        "squarish_window_fatigue_rupture",
    ]
    plans = [plan_explanation(_claim_scene(claim)) for claim in claims]
    assert all(plan and plan["template"] == "AIRCRAFT_WINDOW_STRESS_V1" for plan in plans), plans
    assert {plan["presentation_variant"] for plan in plans} == {
        "LEFT_STRESS_INSPECTION",
        "RIGHT_FLOW_INSPECTION",
        "LEFT_FATIGUE_PAYOFF",
    }
    assert {plan["motion_profile"] for plan in plans} == {"SUBTLE_INSPECTION"}
    assert [plan["scene_role"] for plan in plans] == ["mechanism", "mechanism", "result"]

    from PIL import Image, ImageChops
    base = Image.new("RGBA", (1080, 1920), (28, 31, 38, 255))
    rendered = [_draw_concept_panel(base.copy(), plan, 0.55) for plan in plans]
    for image in rendered:
        bbox = ImageChops.difference(base, image).getbbox()
        assert bbox is not None and bbox[3] >= 1300, bbox
    assert ImageChops.difference(rendered[0], rendered[1]).getbbox() is not None
    assert ImageChops.difference(rendered[1], rendered[2]).getbbox() is not None


def test_subtle_inspection_moves_composed_layer():
    from PIL import Image, ImageChops, ImageDraw

    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((100, 120, 500, 620), fill=(255, 255, 255, 255))
    plan = {
        "motion_profile": "SUBTLE_INSPECTION",
        "presentation_variant": "LEFT_STRESS_INSPECTION",
    }
    start = _apply_subtle_inspection(overlay, plan, 0.0)
    end = _apply_subtle_inspection(overlay, plan, 1.0)
    assert start.size == end.size == (1080, 1920)
    assert ImageChops.difference(start, end).getbbox() is not None


def test_window_unknown_stock_is_not_human_quality_safe():
    downloader = runpy.run_module("video.video_downloader", run_name="video.video_downloader")
    helper = downloader["_window_hq_candidate_ok"]
    globals_ = helper.__globals__
    old_visible = globals_["candidate_visible_component_evidence"]
    old_compat = globals_["candidate_anchor_compatibility"]
    candidate = {"provider": "pixabay", "source_id": "fixture-window"}
    try:
        globals_["candidate_visible_component_evidence"] = lambda *_a, **_k: {"state": "UNKNOWN"}
        globals_["candidate_anchor_compatibility"] = lambda *_a, **_k: {"matched": 2, "total": 2}
        assert helper(candidate, "aircraft passenger window rounded") is False
        assert helper(candidate, "aircraft wing clouds") is True

        globals_["candidate_visible_component_evidence"] = lambda *_a, **_k: {"state": "TRUE"}
        assert helper(candidate, "aircraft passenger window rounded") is True
        globals_["candidate_anchor_compatibility"] = lambda *_a, **_k: {"matched": 1, "total": 2}
        assert helper(candidate, "aircraft passenger window rounded") is False
    finally:
        globals_["candidate_visible_component_evidence"] = old_visible
        globals_["candidate_anchor_compatibility"] = old_compat


def test_negative_full_integration_building_window():
    scene = _window_scene(
        keyword="modern building window frame corner stress",
        _canonical_visual_supply={
            "canonical_subject": "modern office building window with square corners",
            "grounding_source": _FAA_SOURCE,
        },
    )
    plan = plan_explanation(scene)
    assert plan is None or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1"


def test_negative_full_integration_cockpit_windshield():
    scene = _window_scene(
        keyword="aircraft cockpit windshield frame",
        _canonical_visual_supply={
            "canonical_subject": "aircraft cockpit windshield with flat panels",
            "grounding_source": _FAA_SOURCE,
        },
    )
    plan = plan_explanation(scene)
    assert plan is None or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1"


def test_negative_full_integration_wrong_claim():
    scene = _window_scene(owned_claim_id="flap_low_landing_speed")
    plan = plan_explanation(scene)
    assert plan is None or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1"


def test_negative_full_integration_no_grounding():
    scene = _window_scene()
    del scene["_canonical_visual_supply"]
    plan = plan_explanation(scene)
    assert plan is None or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1"


def test_negative_vision_only_verified_full_integration():
    scene = _window_scene()
    del scene["_canonical_visual_supply"]
    scene["_vision_evidence"] = {"pass": True, "state": "VERIFIED"}
    plan = plan_explanation(scene)
    assert plan is None or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1"


def test_existing_winglet_template_unaffected():
    scene = {"text": "날개 끝 윙렛 주변에서 공기가 소용돌이를 만듭니다.", "visual_goal": "winglet vortex", "keyword": "winglet vortex"}
    plan = plan_explanation(scene)
    assert plan is not None
    assert plan["template"] == "WINGLET_VORTEX"
    assert annotation_fact_safe(scene, plan) is True


def test_existing_chevron_flow_mixing_unaffected():
    scene = {
        "scene_id": 4,
        "role": "reveal",
        "owned_claim_id": "chevron_flow_mixing",
        "text": "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
        "visual_goal": "제트 엔진 뒤 셰브론과 두 흐름이 섞이는 관계를 보여준다.",
        "keyword": "jet engine chevron flow mixing",
        "_canonical_visual_supply": {
            "canonical_subject": "jet engine nacelle/nozzle chevrons",
            "identity_confidence": 0.98,
            "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
            "grounding_source": "trusted-fixture",
        },
    }
    plan = plan_explanation(scene)
    assert plan is not None
    assert plan["template"] == "CHEVRON_FLOW_MIXING"


def test_existing_static_wick_unaffected():
    scene = {"owned_claim_id": "static_charge_dissipation", "text": "x", "keyword": "x"}
    plan = plan_explanation(scene)
    assert plan is not None
    assert plan["template"] == "STATIC_WICK_DISCHARGE"


def test_no_downstream_qa_bypass_flags():
    reset_visual_explanation_budget()
    scene = _window_scene()
    plan = plan_explanation(scene)
    forbidden = ("trusted", "skip_vision", "auto_pass", "director_bypass")
    for key in forbidden:
        assert key not in plan, key


def test_render_frame_is_deterministic_across_calls():
    scene = _window_scene()
    plan1 = plan_explanation(scene)
    plan2 = plan_explanation(_window_scene())
    assert plan1["param_signature"] == plan2["param_signature"]
    assert plan1["presentation_variant"] == plan2["presentation_variant"]


def main():
    test_positive_plan_and_render()
    test_claims_have_large_distinct_presentations()
    test_subtle_inspection_moves_composed_layer()
    test_window_unknown_stock_is_not_human_quality_safe()
    test_negative_full_integration_building_window()
    test_negative_full_integration_cockpit_windshield()
    test_negative_full_integration_wrong_claim()
    test_negative_full_integration_no_grounding()
    test_negative_vision_only_verified_full_integration()
    test_existing_winglet_template_unaffected()
    test_existing_chevron_flow_mixing_unaffected()
    test_existing_static_wick_unaffected()
    test_no_downstream_qa_bypass_flags()
    test_render_frame_is_deterministic_across_calls()
    shutil.rmtree(_SCRATCH, ignore_errors=True)
    print("AIRCRAFT WINDOW STRESS RENDERER PHASE 5+7 REGRESSION: PASS")


if __name__ == "__main__":
    main()
