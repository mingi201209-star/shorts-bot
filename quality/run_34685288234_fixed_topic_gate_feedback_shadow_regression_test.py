"""Run 34685288234 fixed-topic Explorer gate-feedback shadow-package regression.

Authority: production Run 34685288234 (canary on main
`7a6be4dda42628c0d9c66b3534c7280282701dc2`, immediately after PR #343 landed)
exhausted all 7 Candidate attempts on the fixed topic
"비행기 창문 모서리는 왜 둥글까" with the *identical* Explorer rejection reason
every single time ("winner.micro_narrative hook이 Core Question과 같은 내용을
반복합니다"), even though `ci_run_34645762458_candidate_feedback_hotfix.py` /
`ci_topic_input_hotfix.py` already wire a "[PREVIOUS CANDIDATE GATE FEEDBACK]"
prompt section specifically to stop that from happening.

Root cause: `content/candidate_explorer/__init__.py` is a *package* that
shadows the legacy `content/candidate_explorer.py` *module* of the same name
(a package always wins Python's import resolution over a same-named module).
Every `ci_*.py` hotfix that adds behavior to the Explorer -- including
`fixed_topic_gate_feedback` support -- patches the legacy module file, which
this wrapper package loads by file path and calls, but the wrapper's own
`explore_candidates(...)` signature never accepted `fixed_topic_gate_feedback`
so the argument was silently dropped, and `main.py`'s real call always hit
`TypeError: ... unexpected keyword argument 'fixed_topic_gate_feedback'`. The
existing `ci_fixed_topic_runtime_call_compat_hotfix.py` swallows exactly that
TypeError and falls back to stuffing the rejection reason into
`rejected_topics`, which is a no-op in fixed-topic mode (the topic itself
never changes) -- so the model never actually saw why the previous attempt
failed, and kept regenerating the same broken Hook/Core-Question pair.

This regression composes the real production hotfix chain in a scratch copy,
proves the wrapper package now forwards `fixed_topic_gate_feedback` end to
end into the legacy Explorer's prompt-building step, and proves nothing about
quality floors, budgets, retries, models, or API allowances changed.
"""
from __future__ import annotations

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

TOPIC = "비행기 창문 모서리는 왜 둥글까"
REJECTION_REASON = (
    "malformed Candidate Explorer response: winner.micro_narrative hook이 "
    "Core Question과 같은 내용을 반복합니다. 첫 두 beat는 새 정보를 전진시켜야 합니다."
)


def _prepare_repo() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="run_34685288234_"))
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


def main():
    repo = _prepare_repo()
    try:
        init_source = (repo / "content/candidate_explorer/__init__.py").read_text(encoding="utf-8")
        assert "RUN_34685288234_FIXED_TOPIC_GATE_FEEDBACK_SHADOW_FIX_V1" in init_source
        print("CASE A fix marker present in shadowing package: PASS")

        sys.path.insert(0, str(repo))
        try:
            import importlib

            for name in list(sys.modules):
                if name == "content" or name.startswith("content."):
                    del sys.modules[name]

            ce = importlib.import_module("content.candidate_explorer")

            import inspect

            sig = inspect.signature(ce.explore_candidates)
            assert "fixed_topic_gate_feedback" in sig.parameters, sig
            print("CASE B shadow package now exposes fixed_topic_gate_feedback: PASS")

            # The exact call shape main.py's primary explorer call site uses.
            # Before the fix this raised TypeError and only reached the
            # legacy module through the runtime-compatibility fallback
            # (which drops the feedback text entirely).
            captured_kwargs = {}
            real_legacy_call = ce._call_legacy_explore_candidates

            def _spy(topic_info, kwargs):
                captured_kwargs.update(kwargs)
                return {"status": "REGENERATE", "reason": "stub"}

            ce._call_legacy_explore_candidates = _spy
            try:
                ce.explore_candidates(
                    {"category": "지정 주제", "topic": TOPIC},
                    recent_topics=[],
                    rejected_topics=[],
                    fixed_topic=TOPIC,
                    fixed_topic_gate_feedback=REJECTION_REASON,
                )
            finally:
                ce._call_legacy_explore_candidates = real_legacy_call

            assert captured_kwargs.get("fixed_topic_gate_feedback") == REJECTION_REASON, captured_kwargs
            print("CASE C fixed_topic_gate_feedback reaches the legacy call kwargs: PASS")

            # End-to-end: the legacy module's own prompt builder must receive
            # and render the feedback section -- this is the actual behavior
            # that stops the model from repeating the same Hook/Core Question.
            legacy = ce._LEGACY
            ctx_with_feedback = legacy.build_execution_context(
                {"category": "지정 주제", "topic": TOPIC},
                recent_topics=[],
                fixed_topic=TOPIC,
                fixed_topic_gate_feedback=REJECTION_REASON,
            )
            assert "[PREVIOUS CANDIDATE GATE FEEDBACK]" in ctx_with_feedback
            assert REJECTION_REASON in ctx_with_feedback
            print("CASE D previous-attempt rejection reason reaches the Explorer prompt: PASS")

            # Backward compatibility: omitting fixed_topic_gate_feedback
            # entirely (every non-fixed-topic caller, and every caller
            # written before this fix) must behave exactly as before.
            captured_kwargs.clear()
            ce._call_legacy_explore_candidates = _spy
            try:
                ce.explore_candidates(
                    {"category": "자동 탐색", "topic": ""},
                    recent_topics=["기존 주제"],
                )
            finally:
                ce._call_legacy_explore_candidates = real_legacy_call
            assert "fixed_topic_gate_feedback" not in captured_kwargs, captured_kwargs
            assert "fixed_topic" not in captured_kwargs, captured_kwargs
            print("CASE E automatic-exploration callers unaffected: PASS")

            ctx_without_fixed_topic = legacy.build_execution_context(
                {"category": "자동 탐색", "topic": "일상 속 과학 원리"},
                recent_topics=[],
            )
            assert "[PREVIOUS CANDIDATE GATE FEEDBACK]" not in ctx_without_fixed_topic
            print("CASE F automatic-exploration prompt unaffected: PASS")

        finally:
            sys.path.remove(str(repo))

        for forbidden in (
            "V3_MAX_COST_USD =",
            "V3_MAX_API_CALLS =",
            "HOOK_MIN_SCORE =",
            "total_topic_attempts =",
            "temperature=0.",
        ):
            assert forbidden not in init_source, forbidden
        print("CASE G budgets/floors/retries/model temperature unchanged in the fix: PASS")

        print("RUN 34685288234 FIXED-TOPIC GATE FEEDBACK SHADOW REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
