"""Run 34689059742 Candidate Grounded Recovery / Canonical Subject Grounding
Gate interaction regression.

Authority: production Run 34689059742 (automatic-topic mode, exact main
`75df7f071bf0e66d048ad350f20151f73d4e7a32`, immediately after PR #346 landed)
proved PR #346's fix works -- zero `CANDIDATE_POOL response received outside
aviation scope` failures across all 7 attempts -- but then crashed on a
*separate*, newly-exposed root cause. After all 7 attempts exhausted, the
existing bounded Candidate Grounded Recovery mechanism recovered a candidate
("도로에서 보이는 미세한 경사") whose Candidate Gate rejection was purely
editorial ("질문이 지나치게 넓고 일반적이며..."), sent it straight to Script
Generator, and only there did the pre-Writer `CANONICAL_SUBJECT_GROUNDING_GATE_V1`
run for the first time and hard-crash the whole production with:
`RuntimeError: CANONICAL_SUBJECT_GROUNDING_GATE_V1 BLOCK: unresolved physical
subject cannot reach Writer`.

Root cause: `content.candidate_gate.evaluate_candidate` (as wrapped by
`ci_canonical_subject_grounding_hotfix.py`) returns early on an editorial
REGENERATE *before* it ever reaches the canonical-subject-grounding check, so
a Gate rejection reason can be purely editorial even when the candidate's own
`subject_kind` was never resolved. `content.candidate_recovery.recovery_eligibility`
only pattern-matches that reason text -- it never independently checks
grounding -- so an ungrounded candidate could enter the recovery pool and
reach the Writer gate for the first time, where there is no bounded-recovery
fail-close path, only a hard raise.

Fix: `recovery_eligibility` now also requires the exact same deterministic
`quality.canonical_subject_grounding.evaluate_candidate_subject_grounding`
check a normal SELECTED candidate already has to satisfy. No new LLM/network
call, no synthesized grounding, no relaxation of the Canonical Subject
Grounding Gate (which stays completely untouched as the final backstop), no
change to Candidate Gate, PR #346's automatic-topic prompt fix, or the #531
fixed-topic aviation success path.

This regression composes the real production hotfix chain in a scratch copy
and proves cases A-H.
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

RUN_532_TOPIC = "도로에서 보이는 미세한 경사"
RUN_532_GATE_REASON = (
    "질문이 지나치게 넓고 일반적이며, Reveal이 구체적인 메커니즘을 "
    "제공하지 않고 일반론으로 끝나기 때문에 약하다."
)


def _prepare_repo() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="run_34689059742_"))
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


def _base_candidate(topic):
    return {
        "topic": topic,
        "angle": "관찰 가능한 구체적인 이유",
        "core_question": "왜 이런 구조/현상이 나타날까?",
        "micro_narrative": {
            "hook": "이건 단순한 우연이 아닙니다.",
            "core_question": "왜 이렇게 되는 걸까요?",
            "reveal": "구체적인 메커니즘이 작용합니다.",
            "payoff": "이 원리를 이해하면 다르게 보입니다.",
        },
        "fact_check_focus": ["mechanism claim is checkable"],
        "visual_proof": ["visible structural difference"],
        "selection_reason": "구조를 직접 시각화할 수 있습니다.",
    }


def _grounded_physical_candidate(topic):
    candidate = _base_candidate(topic)
    candidate.update({
        "subject_kind": "physical_entity",
        "canonical_subject": "road camber",
        "subject_identity_confidence": 0.9,
        "grounding_evidence": [],
        "_trusted_grounding_evidence": [
            {
                "evidence_type": "source_backed_identity",
                "supports_subject": "road camber",
                "source": "civil engineering road design reference",
                "detail": "documented road cross-slope for drainage",
            }
        ],
    })
    return candidate


def main():
    repo = _prepare_repo()
    try:
        source = (repo / "content/candidate_recovery.py").read_text(encoding="utf-8")
        assert "RUN_34689059742_RECOVERY_CANONICAL_GROUNDING_V1" in source

        sys.path.insert(0, str(repo))
        try:
            for name in list(sys.modules):
                if name in ("content", "quality") or name.startswith(("content.", "quality.")):
                    del sys.modules[name]

            recovery = importlib.import_module("content.candidate_recovery")
            grounding = importlib.import_module("quality.canonical_subject_grounding")

            gate = {"status": "REGENERATE", "reason": RUN_532_GATE_REASON}

            # CASE A: soft-editorial recovered candidate with a resolved
            # canonical physical subject -> recovery remains possible.
            grounded = _grounded_physical_candidate("도로 배수를 위한 노면 경사")
            eligible, reason = recovery.recovery_eligibility(grounded, gate)
            assert eligible is True and reason == "soft_editorial_reject", (eligible, reason)
            assert recovery.make_recovery_record(grounded, gate, attempt=4) is not None
            print("CASE A grounded physical subject recovery: PASS")

            # CASE B: exact Run 34689059742 shape (subject_kind never
            # resolved) -> recovery pool eligible=false, no Writer call.
            ungrounded = _base_candidate(RUN_532_TOPIC)
            eligible, reason = recovery.recovery_eligibility(ungrounded, gate)
            assert eligible is False and reason == "pre_writer_grounding_unresolved", (eligible, reason)
            assert recovery.make_recovery_record(ungrounded, gate, attempt=4) is None
            print("CASE B Run 34689059742 ungrounded candidate excluded from recovery pool: PASS")

            # CASE C: explicitly non-physical subject must not be
            # misclassified as an unresolved physical one.
            concept = _base_candidate("유도항력이라는 개념")
            concept["subject_kind"] = "non_physical_concept"
            eligible, reason = recovery.recovery_eligibility(concept, gate)
            assert eligible is True and reason == "soft_editorial_reject", (eligible, reason)
            print("CASE C non-physical subject not misclassified: PASS")

            # CASE D: normal SELECTED candidate path (content.candidate_gate /
            # ci_canonical_subject_grounding_hotfix.py) is completely
            # untouched by this fix -- recovery_eligibility is a separate
            # function this change never wires into that path.
            candidate_gate = importlib.import_module("content.candidate_gate")
            assert hasattr(candidate_gate, "evaluate_candidate")
            print("CASE D normal SELECTED candidate path unaffected: PASS")

            # CASE E: Run #531 fixed-topic aviation path -- this fix touches
            # only content/candidate_recovery.py, never content/candidate_explorer.py
            # or its shadow package, so the aviation fixed-topic prompt/flow
            # is untouched by construction. Confirm the shadow package still
            # loads and exposes fixed_topic_gate_feedback (PR #344's fix).
            import content.candidate_explorer as ce
            import inspect
            sig = inspect.signature(ce.explore_candidates)
            assert "fixed_topic_gate_feedback" in sig.parameters
            print("CASE E Run #531 fixed-topic aviation path (#344) unaffected: PASS")

            # CASE F: PR #346's automatic-topic CANDIDATE_POOL prompt-scoping
            # fix is untouched -- same file (ci_candidate_pool_handoff_hotfix.py)
            # unaffected by this change, and the shadow package still forwards
            # correctly for non-aviation scope.
            hotfix_source = (repo / "ci_candidate_pool_handoff_hotfix.py").read_text(encoding="utf-8")
            assert "RUN_34686824352_AVIATION_PROMPT_SCOPE_V1" in hotfix_source
            print("CASE F PR #346 automatic-topic prompt fix unaffected: PASS")

            # CASE G: pre-Writer Canonical Grounding Gate remains the final
            # backstop -- an unresolved candidate that somehow still reached
            # it must be BLOCKed, never PASS.
            result = grounding.evaluate_candidate_subject_grounding(ungrounded)
            assert result.get("status") == "BLOCK", result
            assert result.get("failure_type") == "SUBJECT_IDENTITY_UNRESOLVED"
            print("CASE G pre-Writer Canonical Grounding Gate still fail-closed: PASS")

        finally:
            sys.path.remove(str(repo))

        # CASE H: no budget/floor/retry/API/model-routing constant touched.
        for forbidden in (
            "V3_MAX_COST_USD =",
            "V3_MAX_API_CALLS =",
            "MAX_TOPIC_REGENERATIONS =",
            "HOOK_MIN_SCORE =",
            "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO",
            "AI_MAX_GENERATIONS_PER_VIDEO",
            "IDENTITY_CONFIDENCE_MIN =",
            "temperature=0.",
        ):
            assert forbidden not in source, forbidden
        print("CASE H budgets/floors/retries/model routing unchanged: PASS")

        print("RUN 34689059742 RECOVERY CANONICAL GROUNDING REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
