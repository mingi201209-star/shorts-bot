"""Regression for Run 34645762458.

Authority: 7/7 bounded fixed-topic Candidate attempts exhausted with the
identical Explorer-internal rejection reason ("winner.micro_narrative hook이
Core Question과 같은 내용을 반복합니다..."). Root-cause investigation (real
job log for run 34645762458, actual composed main.py, and direct testing of
content/candidate_explorer.py's _hook_restates_question against this task's
own REJECT/PASS worked examples) found:

  - Root cause B (CONFIRMED): the Explorer's own internal validation-failure
    reason was never fed back into the next bounded attempt's prompt. The
    existing fixed_topic_gate_feedback channel was only ever populated from
    a downstream WINNER CANDIDATE GATE rejection (main.py's
    `winner_gate.get("reason", "")`), never from an Explorer-internal
    REGENERATE. Since the Explorer never even reached a winner in any of the
    7 attempts, that channel stayed empty every time and the model had zero
    signal to change its output.
  - Root cause A (NOT reproduced): every REJECT/PASS worked example from the
    task, plus this repo's own existing PR #330 CASE 1/2 fixtures, are
    judged correctly by the current _hook_restates_question. No false
    positive was found against any available evidence. (A separate, narrow
    design tension -- a recognized claim-marker word such as "일부러" added
    to an otherwise word-for-word restated proposition currently PASSES
    rather than REJECTs -- was found during this audit and is documented as
    a known limitation below; it is a false NEGATIVE, the opposite direction
    from what caused this production failure, and is left unchanged.)

This test proves the fix for root cause B: ci_run_34645762458_candidate_feedback_hotfix.py
reuses the existing fixed_topic_gate_feedback channel to carry the Explorer's
own rejection reason into the next attempt, with no validator, retry ceiling,
API, or cost change. It also re-asserts (CASE G-K) that the underlying
_hook_restates_question contract from PR #330 is unchanged.
"""
from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_34645762458_candidate_feedback_hotfix import (
    MARKER,
    apply_candidate_feedback,
)

# Exact .github/workflows/main.yml "Apply production hotfixes" order, through
# ci_writer_observable_opening_hotfix.py (which now chain-imports this fix as
# its last step) plus the two hotfixes main.yml runs immediately after it.
# Section 8 of this task explicitly warns against re-making the mini-fixture
# blind spot that hid a prior composition-order bug -- this exercises the
# real production chain, not an isolated single-hotfix fixture.
_PRODUCTION_HOTFIX_CHAIN = [
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


def _install_production_final_hotfix() -> None:
    for script in _PRODUCTION_HOTFIX_CHAIN:
        subprocess.run([sys.executable, script], cwd=ROOT, check=True)


def _explorer_namespace():
    return runpy.run_path(str(ROOT / "content" / "candidate_explorer.py"))


FIXTURE = '''def main():
    while True:
        for topic_attempt in range(1, total_topic_attempts + 1):
            forced_topic = "비행기 창문 모서리는 왜 둥글까"
            fixed_topic_gate_feedback = ""
            explorer_status = "REGENERATE"
            reason = "winner.micro_narrative hook이 Core Question과 같은 내용을 반복합니다."

            # Mirrors the real WINNER CANDIDATE GATE REJECT block elsewhere
            # in production main.py, which already contains this exact guard
            # shape -- apply_candidate_feedback()'s own installed-once guard
            # checks for it.
            if forced_topic:
                fixed_topic_gate_feedback = "placeholder"

            if explorer_status == "REGENERATE":

                print(
                    "♻️ CANDIDATE EXPLORER REGENERATE"
                )

                print(
                    "이유:",
                    reason,
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    continue
'''


def test_exact_run_shape_captures_feedback() -> None:
    patched = apply_candidate_feedback(FIXTURE)
    assert MARKER in patched
    assert "if forced_topic:" in patched
    assert "fixed_topic_gate_feedback = str(" in patched
    assert "reason or \"\"" in patched
    assert "print_budget_status()" in patched


def test_case_a_fixed_topic_feedback_reaches_next_attempt_prompt() -> None:
    """CASE A: the captured Explorer-internal rejection reason must reach the
    real [REJECTED IN THIS RUN] prompt section the next bounded attempt sees,
    via the already-existing rejected_topics fallback channel (confirmed the
    live path: explore_candidates() has no fixed_topic_gate_feedback kwarg,
    so ci_fixed_topic_runtime_call_compat_hotfix.py's TypeError fallback
    always forwards it as rejected_topics=[fixed_topic_gate_feedback])."""
    explorer = _explorer_namespace()
    build_execution_context = explorer["build_execution_context"]
    reason = (
        "winner.micro_narrative hook이 Core Question과 같은 내용을 반복합니다. "
        "첫 두 beat는 새 정보를 전진시켜야 합니다."
    )
    context = build_execution_context(
        {"category": "aviation", "topic": "비행기 창문 모서리는 왜 둥글까"},
        rejected_topics=[reason],
    )
    assert reason in context
    assert "사실상 동일한" in context


def test_case_b_non_fixed_topic_feedback_does_not_leak() -> None:
    """CASE B: the injected assignment is guarded by `if forced_topic:` --
    a non-fixed-topic run must never see this feedback string."""
    patched = apply_candidate_feedback(FIXTURE)
    injected = patched.split(MARKER, 1)[1]
    assert "if forced_topic:" in injected
    # the assignment itself must be nested under that guard, not top-level
    guard_idx = injected.index("if forced_topic:")
    assign_idx = injected.index("fixed_topic_gate_feedback = str(")
    assert assign_idx > guard_idx


def test_case_c_d_e_f_no_budget_or_threshold_change() -> None:
    """CASE C/D/E/F: attempt ceiling, MAX_REWRITES, Hook floor, and API/cost
    budget are untouched by this hotfix."""
    patched = apply_candidate_feedback(FIXTURE)
    injected = patched.split(MARKER, 1)[1]
    assert "MAX_TOPIC_REGENERATIONS" not in patched
    assert "MAX_REWRITES" not in patched
    assert "total_topic_attempts" not in injected.split("print_budget_status()")[0]
    assert "HOOK" not in injected
    assert "threshold" not in patched.lower()
    # print_budget_status() itself is the pre-existing anchor tail, retained
    # verbatim -- only require no NEW budget-limit constant was introduced.
    assert "authorize_call" not in injected
    assert "BUDGET_LIMIT" not in injected
    assert "$" not in injected


def test_idempotent() -> None:
    once = apply_candidate_feedback(FIXTURE)
    twice = apply_candidate_feedback(once)
    assert once == twice
    assert twice.count(MARKER) == 1


def test_real_main_composition_shape_is_patchable() -> None:
    """Exercise the real, fully-composed production main.py (not an isolated
    single-hotfix fixture) to guarantee the anchor survives the actual
    main.yml hotfix ordering."""
    _install_production_final_hotfix()
    composed = (ROOT / "main.py").read_text(encoding="utf-8")
    assert MARKER in composed
    assert composed.count(MARKER) == 1


# ---------------------------------------------------------------------------
# CASE G-K: re-assert the PR #330 _hook_restates_question contract is
# unchanged by this fix, plus the two new cases this task's own audit
# (Section 6) explicitly requires.
# ---------------------------------------------------------------------------

def test_case_g_bad_statement_then_identical_question_still_rejects() -> None:
    explorer = _explorer_namespace()
    f = explorer["_hook_restates_question"]
    assert f(
        "비행기 창문 모서리는 둥급니다.",
        "왜 비행기 창문 모서리는 둥글까요?",
    ) is True


def test_case_h_genuinely_new_causal_info_passes() -> None:
    explorer = _explorer_namespace()
    f = explorer["_hook_restates_question"]
    assert f(
        "높은 고도에서는 창문 주변 구조에 큰 압력 차이가 생깁니다.",
        "그래서 왜 모서리를 둥글게 만들었을까요?",
    ) is False
    assert f(
        "작은 모서리 형상 차이가 응력 집중을 크게 바꿉니다.",
        "비행기 창문 모서리는 왜 둥글까요?",
    ) is False


def test_case_i_explicit_claim_marker_progression_passes() -> None:
    explorer = _explorer_namespace()
    f = explorer["_hook_restates_question"]
    assert f(
        "비행기 창문 모서리는 일부러 둥글게 만듭니다.",
        "각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?",
    ) is False


def test_case_j_decorative_only_addition_without_claim_marker_still_rejects() -> None:
    """CASE J: a hook that adds a decorative word carrying no real new
    information (and no recognized claim marker) must still reject."""
    explorer = _explorer_namespace()
    f = explorer["_hook_restates_question"]
    assert f(
        "비행기 창문 모서리는 정말 둥급니다.",
        "왜 비행기 창문 모서리는 둥글까요?",
    ) is True


def test_case_k_low_overlap_semantic_duplicate_is_a_known_limitation() -> None:
    """CASE K: documented, not hidden -- a full-vocabulary-swap semantic
    repeat with low token overlap is not caught without a new model call,
    which this task forbids adding."""
    explorer = _explorer_namespace()
    f = explorer["_hook_restates_question"]
    not_caught = f(
        "여객기 유리창 코너는 둥급니다.",
        "비행기 창문 모서리가 곡선인 이유는 무엇일까요?",
    )
    assert not_caught is False


def test_known_limitation_claim_marker_plus_decorative_only_addition() -> None:
    """Documented (not fixed this round, opposite direction from the actual
    production failure): a recognized claim-marker word ("일부러") added to
    an otherwise word-for-word restated proposition currently PASSES rather
    than rejects. This is a false negative, not the false-positive/exhaustion
    shape Run 34645762458 actually hit, and is left unchanged here."""
    explorer = _explorer_namespace()
    f = explorer["_hook_restates_question"]
    result = f(
        "비행기 창문 모서리는 일부러 둥글게 만들어졌습니다.",
        "비행기 창문 모서리는 왜 둥글게 만들어졌을까요?",
    )
    assert result is False, "known limitation: documents current behavior, not a target"


def main() -> None:
    test_exact_run_shape_captures_feedback()
    test_case_a_fixed_topic_feedback_reaches_next_attempt_prompt()
    test_case_b_non_fixed_topic_feedback_does_not_leak()
    test_case_c_d_e_f_no_budget_or_threshold_change()
    test_idempotent()
    test_real_main_composition_shape_is_patchable()
    test_case_g_bad_statement_then_identical_question_still_rejects()
    test_case_h_genuinely_new_causal_info_passes()
    test_case_i_explicit_claim_marker_progression_passes()
    test_case_j_decorative_only_addition_without_claim_marker_still_rejects()
    test_case_k_low_overlap_semantic_duplicate_is_a_known_limitation()
    test_known_limitation_claim_marker_plus_decorative_only_addition()
    print("RUN 34645762458 CANDIDATE FEEDBACK REGRESSION: PASS")


if __name__ == "__main__":
    main()
