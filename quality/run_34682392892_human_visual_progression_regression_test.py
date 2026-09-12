"""Run 34682392892 machine-green / MP4-human-fail regression.

Authority production Run 34682392892 on main
`d851ec1e56a6adf6b8c8e69d34473761922cc34c` produced a verified MP4 but direct
frame inspection found two independent escapes:

1. Hook-only body reuse paired a new Scene 1 ("reason is not aesthetic") with
   the preserved Scene 2 asking the same reason. The final opening contract did
   not treat a negated superficial explanation as a no-information teaser.
2. Scene 5 owned the grounded `squarish_window_fatigue_rupture` payoff, but the
   verified-still path accepted a subject-visible still even while its Vision
   reason explicitly said no fatigue/rupture action was observable. That raw
   reuse bypassed the already-existing `LEFT_FATIGUE_PAYOFF` deterministic
   explanatory state.

This regression composes the real production hotfix chain in a scratch copy and
proves both escapes are closed without network/LLM/Vision/image generation or
quality/budget/retry changes.
"""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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
    "ci_writer_observable_opening_hotfix.py", "ci_grounded_deterministic_explanation_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
]

CANONICAL = "modern aircraft passenger window with rounded/oval corners"
PAYOFF_CLAIM = "squarish_window_fatigue_rupture"


def _prepare_repo():
    scratch = Path(tempfile.mkdtemp(prefix="run_34682392892_"))
    repo = scratch / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    for script in _CHAIN:
        result = subprocess.run(
            [sys.executable, script],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"production composition failed at {script}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
    return repo


def _fresh_import(repo: Path, module_name: str):
    for name in list(sys.modules):
        if name == module_name or name.startswith(module_name + "."):
            del sys.modules[name]
        if module_name.startswith("video.") and (name == "video" or name.startswith("video.")):
            del sys.modules[name]
        if module_name.startswith("content.") and (name == "content" or name.startswith("content.")):
            del sys.modules[name]
        if module_name.startswith("quality.") and (name == "quality" or name.startswith("quality.")):
            del sys.modules[name]
    sys.path.insert(0, str(repo))
    try:
        return importlib.import_module(module_name)
    finally:
        sys.path.remove(str(repo))


def _trusted_window_scene5(repo: Path):
    sys.path.insert(0, str(repo))
    try:
        from quality.candidate_pool_grounding_records import (
            CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
        from quality.canonical_subject_grounding_supply import (
            supply_trusted_subject_grounding,
        )
        from video.video_downloader import build_canonical_visual_supply_profile

        records = [
            record
            for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
            if record.get("canonical_subject") == CANONICAL
        ]
        assert len(records) == 1
        candidate = {
            "topic": "비행기 창문 모서리는 왜 둥글까",
            "angle": "비행기 창문은 모서리가 둥글게 디자인",
            "core_question": "비행기 창문 모서리가 둥글게 설계된 이유는 무엇인가?",
            "specific_observation": "현대 여객기 동체의 승객용 창문 가장자리는 둥글거나 타원형입니다.",
            "micro_narrative": {
                "hook": "비행기 창문은 모서리가 둥글게 디자인됩니다.",
                "core_question": "왜 둥글게 설계됐을까요?",
                "reveal": "둥근 모서리는 응력 집중을 줄입니다.",
                "payoff": "각진 창문 모서리의 응력 집중은 재료 피로와 파열 위험을 키웠습니다.",
            },
        }
        supplied = supply_trusted_subject_grounding(candidate, trusted_records=records)
        profile = build_canonical_visual_supply_profile(supplied)
        assert profile.get("canonical_subject") == CANONICAL
        return {
            "scene_id": 5,
            "role": "payoff",
            "causal_role": "primary_result",
            "owned_claim_id": PAYOFF_CLAIM,
            "text": "각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 이어질 수 있었습니다.",
            "visual_goal": "각진 창문 모서리에서 피로 균열이 시작되어 동체로 번지는 과정을 표현합니다.",
            "keyword": "modern aircraft window squarish fatigue rupture comet",
            "_canonical_visual_supply": profile,
        }
    finally:
        sys.path.remove(str(repo))


def main():
    repo = _prepare_repo()
    try:
        validation_source = (repo / "content/script_engine_v2_validation.py").read_text(encoding="utf-8")
        still_source = (repo / "video/still_image_fallback.py").read_text(encoding="utf-8")
        explanation_source = (repo / "video/visual_explanation.py").read_text(encoding="utf-8")
        main_source = (repo / "main.py").read_text(encoding="utf-8")

        assert "RUN_34676516725_FIXED_TOPIC_HOOK_BODY_REUSE_V1" in main_source
        assert "RUN_34682392892_NEGATED_REASON_TEASER_GUARD_V1" in validation_source
        assert "RUN_34682392892_WINDOW_PAYOFF_STATE_SKIP_V1" in still_source
        assert "RUN_34682392892_WINDOW_MECHANISM_WORDING_V1" in explanation_source

        validation = _fresh_import(repo, "content.script_engine_v2_validation")
        bad = validation.opening_human_contract_violation_reason(
            "비행기 창문 모서리가 둥글게 디자인된 이유는 단순한 미적 요소가 아닙니다.",
            "비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?",
        )
        assert "without adding a grounded causal clue" in bad, bad

        good = validation.opening_human_contract_violation_reason(
            "각진 창문 모서리에는 응력이 집중되기 쉽습니다.",
            "비행기 창문 모서리는 왜 둥글게 만들까요?",
        )
        assert not good, good

        grounded_negation = validation.opening_human_contract_violation_reason(
            "비행기 창문 모서리가 둥근 건 장식이 아니라 응력 집중을 줄이기 위해서입니다.",
            "비행기 창문 모서리는 왜 둥글게 만들까요?",
        )
        assert not grounded_negation, grounded_negation
        print("CASE A Run 526 opening no-information negation escape: PASS")

        scene5 = _trusted_window_scene5(repo)
        still = _fresh_import(repo, "video.still_image_fallback")
        assert still._run526_requires_window_payoff_state(scene5) is True

        # The exact Run #526 payoff must not spend/use a raw still at all. The
        # wrapper returns before output-path access or Vision/image generation.
        raw = still.generate_still_motion_fallback(
            scene5,
            output_path=repo / "must_not_exist.mp4",
            duration=6.7,
            trigger_reason="no_semantically_safe_stock",
        )
        assert raw is None
        assert not (repo / "must_not_exist.mp4").exists()

        non_payoff = dict(scene5)
        non_payoff["owned_claim_id"] = "rounded_window_stress_distribution"
        non_payoff["causal_role"] = "mechanism_change"
        assert still._run526_requires_window_payoff_state(non_payoff) is False

        explanation = _fresh_import(repo, "video.visual_explanation")
        plan = explanation.plan_explanation(scene5)
        assert plan is not None, "payoff must reach existing deterministic explanation supply"
        assert plan.get("template") == "AIRCRAFT_WINDOW_STRESS_V1", plan
        assert plan.get("owned_claim_id") == PAYOFF_CLAIM, plan
        assert plan.get("presentation_variant") == "LEFT_FATIGUE_PAYOFF", plan
        assert plan.get("evidence_source") == "TRUSTED_GROUNDING", plan
        assert explanation.annotation_fact_safe(scene5, plan) is True
        print("CASE B Run 526 fatigue/rupture raw-still escape -> LEFT_FATIGUE_PAYOFF: PASS")

        assert "둥근 모서리는 응력을 흘려보냅니다" not in explanation_source
        assert "둥근 모서리는 응력 집중을 줄입니다" in explanation_source
        print("CASE C mechanism overlay wording precision: PASS")

        helper_source = (repo / "ci_run_34682392892_human_visual_progression_hotfix.py").read_text(encoding="utf-8")
        for forbidden in (
            "V3_MAX_COST_USD =",
            "V3_MAX_API_CALLS =",
            "MAX_REWRITES =",
            "MAX_TOPIC_REGENERATIONS =",
            "HOOK_MIN_SCORE =",
            "GOOD_ENOUGH_FLOORS =",
            "responses.create(",
            "chat.completions.create(",
            "images.generate(",
            "generate_script(",
        ):
            assert forbidden not in helper_source, forbidden
        print("CASE D budgets/floors/retries/models/API calls unchanged: PASS")

        print("RUN 34682392892 HUMAN VISUAL PROGRESSION REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
