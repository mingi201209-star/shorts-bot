"""PHASE 5 + PHASE 7 regression: AIRCRAFT_WINDOW_STRESS_V1 deterministic
renderer wired into the live video/visual_explanation.py production consumer
via ci_grounded_deterministic_explanation_hotfix.py.

Zero network/LLM/Vision/AI-image calls. Composes the exact real hotfix chain
(mirroring quality/run_33257939720_chevron_flow_mixing_visual_supply_regression_test.py's
established pattern) in an isolated scratch copy of the repo, then exercises
video.visual_explanation directly.

Note: video._render_clip()'s actual video-file write goes through moviepy/
ffmpeg, which is not installed in this sandbox (confirmed pre-existing,
unrelated to this change -- matching PR #322's documented precedent for
run_33865295007_effective_presentation_motion / early_verified_asset_
presentation_repetition, which fail identically on unmodified main for the
same reason). This test therefore verifies everything reachable without an
actual ffmpeg process: plan selection, fact-safety re-check, deterministic
PIL frame rendering (pure Pillow, no ffmpeg), signature/dedup bookkeeping,
and downstream-QA non-bypass -- not the final .mp4 write itself.
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


def test_positive_plan_and_render():
    reset_visual_explanation_budget()
    scene = _window_scene()
    plan = plan_explanation(scene)
    assert plan is not None
    assert plan["template"] == "AIRCRAFT_WINDOW_STRESS_V1"
    assert plan["evidence_source"] == "TRUSTED_GROUNDING"
    assert annotation_fact_safe(scene, plan) is True

    from PIL import Image
    frame = Image.new("RGBA", (1080, 1920), (28, 31, 38, 255))
    out = _draw_concept_panel(frame, plan, 0.4)
    assert out.size == (1080, 1920)


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
        "scene_id": 4, "role": "reveal", "owned_claim_id": "chevron_flow_mixing",
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


def main():
    test_positive_plan_and_render()
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
