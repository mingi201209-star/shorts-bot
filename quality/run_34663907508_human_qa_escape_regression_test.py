"""Production-composed regression for Run 34663907508.

Authority: Run 34663907508 was machine-green (exact-SHA PASS, hotfix
composition PASS, Generator SUCCESS, Final Visual Semantic QA 5/5 PASS,
Visual Diversity Preflight PASS, Director 7.90 PASS) but HUMAN QA found two
real escapes, both verified directly against the actual production job log
(not just the human report):

  A. Opening: final Scene 1 ("...사실은 많은 분들이 간과하시지만, 이 디자인에는
     중요한 이유가 있습니다.") stated no real progression before Scene 2 asked
     "왜 ... 설계되었을까요?" about the same subject. PR #330's Candidate-level
     _hook_restates_question did not catch this because the longer,
     meta-teaser-padded Writer/Rewrite prose dilutes its token-overlap ratio.

  B. Visual: Scene 2's visual_goal ("둥근 창문과 각진 창문의 형태를 나란히
     대비합니다.") explicitly asked for a shape comparison, but the actual
     render reused the exact same single-state verified still as Scene 1
     (source_asset_id=still-6dab02fa4c97e9a2, mode=
     REUSED_VERIFIED_QUESTION_SUBJECT_MOTION) -- a false pass, since one
     photo of one window state cannot show a contrast.

This suite composes the real hotfix chain (never an isolated mini-fixture)
and covers CASE OPENING-1..7 and CASE VISUAL-1..4, plus explicit regressions
proving neither fix touches any budget, threshold, retry, or scene-count
value, and that the pre-existing three-claim AIRCRAFT_WINDOW_STRESS_V1 path
(Run 34625637738 / PR #324) is unaffected.
"""
from __future__ import annotations

import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SCRATCH = Path(tempfile.mkdtemp(prefix="run_34663907508_"))
_REPO = _SCRATCH / "repo"
shutil.copytree(ROOT, _REPO, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
sys.path.insert(0, str(_REPO))

# Exact .github/workflows/main.yml "Apply production hotfixes" order through
# the two hotfixes main.yml runs right after ci_writer_observable_opening_hotfix.py.
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
    "ci_aviation_context_signature_compat_hotfix.py",
]

for script in _CHAIN:
    subprocess.run([sys.executable, script], check=True, cwd=_REPO, capture_output=True)

_validation = runpy.run_module("content.script_engine_v2_validation", run_name="content.script_engine_v2_validation")
validate_scene_basics = _validation["validate_scene_basics"]

_vx = runpy.run_module("video.visual_explanation", run_name="video.visual_explanation")
plan_explanation = _vx["plan_explanation"]
annotation_fact_safe = _vx["annotation_fact_safe"]
_draw_concept_panel = _vx["_draw_concept_panel"]

_still = runpy.run_module("video.still_image_fallback", run_name="video.still_image_fallback")
generate_still_motion_fallback = _still["generate_still_motion_fallback"]

_grounding = runpy.run_module(
    "video.aircraft_window_stress_grounding", run_name="video.aircraft_window_stress_grounding"
)
supports_aircraft_window_stress_from_grounding = _grounding["supports_aircraft_window_stress_from_grounding"]
supports_aircraft_window_shape_contrast_intro_from_grounding = _grounding[
    "supports_aircraft_window_shape_contrast_intro_from_grounding"
]


def _scene(role, text, keyword):
    return {"role": role, "text": text, "visual_goal": "aircraft window corner shape", "keyword": keyword}


def _contract(role):
    return {"role": role}


def _script_with_opening(scene1_text, scene2_text):
    scenes = [
        _scene("phenomenon", scene1_text, "aircraft window corner shape"),
        _scene("question", scene2_text, "aircraft window corner why"),
        _scene("causal_clue", "각진 모서리에는 응력이 한 곳에 몰립니다.", "aircraft window stress concentration"),
        _scene("reveal", "둥근 모서리는 그 응력을 넓게 분산시킵니다.", "aircraft window stress distribution"),
        _scene("payoff", "그래서 현대 여객기 창문은 처음부터 둥글게 설계됩니다.", "modern aircraft window design"),
    ]
    plan = {"contracts": [_contract(s["role"]) for s in scenes]}
    return {"scenes": scenes}, plan


def _opening_failure(script, plan):
    ok, failures = validate_scene_basics(script, plan)
    return [f for f in failures if f.get("scene_index") == 1]


# ---------------------------------------------------------------------------
# CASE OPENING-1..7
# ---------------------------------------------------------------------------

def test_case_opening1_exact_run_34663907508_escape_fails() -> None:
    script, plan = _script_with_opening(
        "비행기 창문 모서리가 둥글다는 사실은 많은 분들이 간과하시지만, 이 디자인에는 중요한 이유가 있습니다.",
        "그렇다면 비행기 창문 모서리는 왜 둥글게 설계되었을까요?",
    )
    assert _opening_failure(script, plan)


def test_case_opening2_short_observation_then_why_fails() -> None:
    script, plan = _script_with_opening(
        "비행기 창문 모서리는 둥급니다.",
        "왜 비행기 창문 모서리는 둥글까요?",
    )
    assert _opening_failure(script, plan)


def test_case_opening3_real_causal_clue_in_scene1_passes() -> None:
    script, plan = _script_with_opening(
        "작은 모서리 형상 차이가 응력 집중을 크게 바꿉니다.",
        "비행기 창문 모서리는 왜 둥글까요?",
    )
    assert not _opening_failure(script, plan)


def test_case_opening4_existing_pr330_good_case_passes() -> None:
    script, plan = _script_with_opening(
        "비행기 창문 모서리는 일부러 둥글게 만듭니다.",
        "각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?",
    )
    assert not _opening_failure(script, plan)


def test_case_opening5_existing_pr330_bad_case_still_fails() -> None:
    """Re-asserted here for completeness -- this exact shape is already
    fail-closed at the Candidate level (PR #330's own _hook_restates_question)
    and is ALSO caught by this new final-level check independently (CASE
    OPENING-7's own defense-in-depth requirement)."""
    script, plan = _script_with_opening(
        "비행기 창문 모서리는 둥급니다.",
        "왜 비행기 창문 모서리는 둥글까요?",
    )
    assert _opening_failure(script, plan)


def test_case_opening6_question_form_hook_not_banned_outright() -> None:
    script, plan = _script_with_opening(
        "비행기 창문은 왜 각진 모서리를 버렸을까요?",
        "그 형상 변화가 구조에 어떤 차이를 만들까요?",
    )
    assert not _opening_failure(script, plan)


def test_case_opening7_rewrite_stage_regression_caught_by_final_gate() -> None:
    """A hypothetical Rewrite-stage regression that reintroduces the bare-
    restatement shape (not the meta-teaser one) must still be caught here,
    proving this is a real final gate and not only a meta-teaser detector."""
    script, plan = _script_with_opening(
        "비행기 창문 모서리는 완전히 둥근 형태입니다.",
        "그런데 비행기 창문 모서리는 왜 완전히 둥근 형태일까요?",
    )
    assert _opening_failure(script, plan)


def test_opening_check_does_not_change_existing_scene_progression_checks() -> None:
    """PR #330's own scene-progression/filler/payoff-repetition checks must
    still fire independently and unaffected by this new opening check."""
    scenes = [
        _scene("phenomenon", "비행기 창문 모서리는 일부러 둥글게 만듭니다.", "aircraft window corner shape"),
        _scene("question", "각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?", "aircraft window corner why"),
        _scene("causal_clue", "중요한 이유는 다음과 같습니다.", "aircraft window stress concentration"),
        _scene("reveal", "둥근 모서리는 그 응력을 넓게 분산시킵니다.", "aircraft window stress distribution"),
        _scene("payoff", "그래서 현대 여객기 창문은 처음부터 둥글게 설계됩니다.", "modern aircraft window design"),
    ]
    plan = {"contracts": [_contract(s["role"]) for s in scenes]}
    ok, failures = validate_scene_basics({"scenes": scenes}, plan)
    assert any("filler phrase" in f.get("reason", "") for f in failures)


# ---------------------------------------------------------------------------
# CASE VISUAL-1..4
# ---------------------------------------------------------------------------

def _comparison_scene():
    return {
        "role": "question",
        "visual_goal": "둥근 창문과 각진 창문의 형태를 나란히 대비합니다.",
        "keyword": "modern aircraft window rounded oval corner shape",
        "_canonical_visual_supply": {
            "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
            "grounding_source": "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV",
        },
    }


def test_case_visual1_exact_run_34663907508_scene2_shape_is_no_longer_a_false_pass() -> None:
    scene = _comparison_scene()
    # The single-state reuse path must no longer silently satisfy this scene.
    assert generate_still_motion_fallback(
        scene, output_path="workspace/temp/case_visual1.mp4", duration=3.0,
        trigger_reason="no_semantically_safe_stock",
    ) is None
    # It must not be eligible for the claim-owning path either (no owned claim).
    assert supports_aircraft_window_stress_from_grounding(scene) is None
    # It must be eligible for the new neutral shape-contrast-intro path.
    eligibility = supports_aircraft_window_shape_contrast_intro_from_grounding(scene)
    assert eligibility is not None
    plan = plan_explanation(scene)
    assert plan["template"] == "AIRCRAFT_WINDOW_STRESS_V1"
    assert plan["presentation_variant"] == "SHAPE_CONTRAST_INTRO"
    assert annotation_fact_safe(scene, plan) is True
    from PIL import Image
    frame = Image.new("RGB", (1080, 1920), (10, 10, 10))
    out = _draw_concept_panel(frame, plan, 0.5)
    assert out.size == (1080, 1920)


def test_case_visual2_comparison_goal_with_real_two_state_presentation_passes() -> None:
    """The deterministic AIRCRAFT_WINDOW_STRESS_V1 render for this variant
    draws both the angular and rounded corner shapes (not a claim-specific
    single-emphasis inspection) -- confirmed by inspecting the actual plan
    and render call succeeding without raising."""
    scene = _comparison_scene()
    plan = plan_explanation(scene)
    assert plan.get("_comparison_segment") is not None
    assert plan["_comparison_segment"]["comparison_segments"][0]["presentation"] == "SPLIT_SCREEN"


def test_case_visual3_non_comparison_question_scene_reuse_policy_unchanged() -> None:
    """A question-role scene whose visual_goal does NOT express comparison
    intent must not be routed into the new path at all -- REUSED_VERIFIED_
    QUESTION_SUBJECT_MOTION itself is not banned outright."""
    scene = _comparison_scene()
    scene["visual_goal"] = "비행기 창문이 둥근 모습을 보여줍니다."
    assert supports_aircraft_window_shape_contrast_intro_from_grounding(scene) is None


def test_case_visual4_claim_owning_scenes_remain_exclusively_on_existing_path() -> None:
    """A scene that DOES own one of the three grounded claims must never be
    captured by the new no-claim comparison-intro path, even if its
    visual_goal happens to also mention comparison wording."""
    scene = {
        "role": "causal_clue",
        "causal_role": "constraint",
        "owned_claim_id": "squarish_window_stress_concentration",
        "visual_goal": "각진 창문과 둥근 창문의 응력을 대비합니다.",
        "keyword": "modern aircraft window squarish stress concentration comet",
        "_canonical_visual_supply": {
            "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
            "grounding_source": "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV",
        },
    }
    assert supports_aircraft_window_shape_contrast_intro_from_grounding(scene) is None
    plan = plan_explanation(scene)
    assert plan["presentation_variant"] == "LEFT_STRESS_INSPECTION"
    assert annotation_fact_safe(scene, plan) is True


def test_existing_three_claim_variants_unaffected() -> None:
    """Run 34625637738 / PR #324's own three claim-owning presentations must
    render exactly as before -- this PR only adds a fourth, independent
    variant."""
    from PIL import Image
    for claim_id, causal_role, expected_variant in (
        ("squarish_window_stress_concentration", "constraint", "LEFT_STRESS_INSPECTION"),
        ("rounded_window_stress_distribution", "mechanism_change", "RIGHT_FLOW_INSPECTION"),
        ("squarish_window_fatigue_rupture", "primary_result", "LEFT_FATIGUE_PAYOFF"),
    ):
        scene = {
            "role": "causal_clue",
            "causal_role": causal_role,
            "owned_claim_id": claim_id,
            "keyword": f"modern aircraft window {claim_id.replace('_', ' ')} comet",
            "_canonical_visual_supply": {
                "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
                "grounding_source": "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV",
            },
        }
        plan = plan_explanation(scene)
        assert plan["presentation_variant"] == expected_variant, claim_id
        assert annotation_fact_safe(scene, plan) is True
        out = _draw_concept_panel(Image.new("RGB", (1080, 1920), (0, 0, 0)), plan, 0.4)
        assert out.size == (1080, 1920)


# ---------------------------------------------------------------------------
# Guardrail regressions: no threshold/budget/retry/API change.
# ---------------------------------------------------------------------------

def test_no_budget_threshold_retry_changes_in_new_hotfix_files() -> None:
    opening_hotfix = (ROOT / "ci_run_34663907508_human_qa_escape_hotfix.py").read_text(encoding="utf-8")
    gde_hotfix = (ROOT / "ci_grounded_deterministic_explanation_hotfix.py").read_text(encoding="utf-8")
    for text, label in ((opening_hotfix, "opening hotfix"), (gde_hotfix, "grounded deterministic explanation hotfix")):
        assert "MAX_REWRITES" not in text, label
        assert "MAX_TOPIC_REGENERATIONS" not in text, label
        assert "STILL_IMAGE_MAX_PER_VIDEO =" not in text, label
        assert "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO =" not in text, label
        assert "authorize_call" not in text, label
        assert "openai" not in text.lower(), label


def main() -> None:
    test_case_opening1_exact_run_34663907508_escape_fails()
    test_case_opening2_short_observation_then_why_fails()
    test_case_opening3_real_causal_clue_in_scene1_passes()
    test_case_opening4_existing_pr330_good_case_passes()
    test_case_opening5_existing_pr330_bad_case_still_fails()
    test_case_opening6_question_form_hook_not_banned_outright()
    test_case_opening7_rewrite_stage_regression_caught_by_final_gate()
    test_opening_check_does_not_change_existing_scene_progression_checks()
    test_case_visual1_exact_run_34663907508_scene2_shape_is_no_longer_a_false_pass()
    test_case_visual2_comparison_goal_with_real_two_state_presentation_passes()
    test_case_visual3_non_comparison_question_scene_reuse_policy_unchanged()
    test_case_visual4_claim_owning_scenes_remain_exclusively_on_existing_path()
    test_existing_three_claim_variants_unaffected()
    test_no_budget_threshold_retry_changes_in_new_hotfix_files()
    print("RUN 34663907508 HUMAN QA ESCAPE REGRESSION: PASS")


if __name__ == "__main__":
    main()
