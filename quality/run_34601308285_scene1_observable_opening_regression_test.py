"""Regression for Run 34601308285 pre-Writer Scene 1 observable-opening failure.

No network/API call. Applies the exact production hotfix chain from
.github/workflows/main.yml (through ci_writer_observable_opening_hotfix.py,
the last hotfix that touches Scene 1 opening conversion) against an isolated
copy of the repo, then reproduces the real Run 34601308285 counterexample
against build_narrative_plan()/_grounded_opening() -- the actual function in
the real traceback (content/script_engine_v2.py:870), not the earlier
router-level best-effort pass in content/script_generator_router.py.

Authority (Run 34601308285, main 1be7916a9e64f2b05471689cc8d8061f6e11da64,
topic "비행기 창문 모서리는 왜 둥글까"):

    CANONICAL_SUBJECT_GROUNDING PASS role=Winner ... confidence=0.97
    CANONICAL_SUBJECT_GROUNDING PASS role=pre-Writer ... confidence=0.97
    Router locked narration normalized without API: core_question,scene2_question
    scene 1 hook must be an observable statement, not a question
    ValueError: scene 1 hook must be an observable statement, not a question

Root cause: _QUESTION_HOOK_REPAIRS (content/script_engine_v2.py) is a closed
list of previously-seen literal Korean question endings, reactively grown one
exact incident at a time (e.g. "둥글게 설계되었을까$", "둥근가$", "펼쳐질까$").
The plain adjective-stem ending "둥글까" (round?) -- this run's own topic and
core_question, once the embedded "왜" is stripped -- had no entry, so both
the hook-side and the grounded topic-question fallback inside
_question_hook_to_observation() returned "" and _grounded_opening() raised.

Fix: one additional literal entry, "둥글까$" -> "둥급니다", installed next to
the existing "둥근가$" sibling (same canonical subject, different question
ending) in ci_script_v2_gunggeum_formal_ending_hotfix.py. No broad adjective
class or generic "왜 X?" regex was added -- only this exact previously-unseen
ending, matching the codebase's own established one-incident-at-a-time
pattern for this list.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

# Exact .github/workflows/main.yml "Apply production hotfixes" order, through
# the last hotfix that touches Scene 1 opening conversion.
HOTFIX_CHAIN = [
    "ci_hotfix.py",
    "ci_novelty_budget_hotfix.py",
    "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py",
    "ci_first5_retention_tts_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_aviation_candidate_specificity_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
    "ci_aviation_specificity_output_repair_hotfix.py",
    "ci_aviation_specificity_projection_hotfix.py",
    "ci_candidate_grounded_recovery_hotfix.py",
    "ci_growth_candidate_shadow_hotfix.py",
    "ci_final_render_content_integrity_hotfix.py",
    "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py",
    "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py",
    "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py",
    "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py",
    "ci_hook_fallback_quality_floor_hotfix.py",
    "ci_ai_visual_fallback_hotfix.py",
    "ci_ai_visual_mechanism_fallback_hotfix.py",
    "ci_problem_solution_narrative_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_retention_structure_experiment_hotfix.py",
    "ci_subscriber_conversion_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
    "ci_general_scene_visual_parity_hotfix.py",
    "ci_script_validation_recovery_hotfix.py",
    "ci_script_v2_visual_goal_hotfix.py",
    "ci_script_v2_gunggeum_formal_ending_hotfix.py",
    "ci_final_visual_semantic_qa_hotfix.py",
    "ci_cross_process_video_dedupe_hotfix.py",
    "ci_writer_observable_opening_hotfix.py",
]


def _prepare_worktree(apply_fix: bool) -> Path:
    """Copy the repo to an isolated scratch dir; optionally revert the fix."""
    scratch = Path(tempfile.mkdtemp(prefix="run_34601308285_"))
    dest = scratch / "repo"
    shutil.copytree(
        ROOT,
        dest,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    if not apply_fix:
        # RED: revert only this fix's own literal addition; every other
        # already-shipped hotfix stays exactly as committed.
        target = dest / "ci_script_v2_gunggeum_formal_ending_hotfix.py"
        text = target.read_text(encoding="utf-8")
        marker = "            # Run 34601308285"
        # The hotfix source is itself Python source containing a string
        # literal; read as raw text, its embedded "\n" is the two literal
        # characters backslash+n, not an evaluated newline.
        needle = '    (r"둥글까$", "둥급니다"),\\n\'\n'
        if needle not in text:
            raise RuntimeError("RED setup: fix line not found in source to revert")
        # Strip the fix line and its explanatory comment block.
        lines = text.splitlines(keepends=True)
        out = []
        skipping = False
        for line in lines:
            if line.strip().startswith(marker.strip()):
                skipping = True
                continue
            if skipping and line.endswith(needle):
                skipping = False
                continue
            if skipping:
                continue
            out.append(line)
        target.write_text("".join(out), encoding="utf-8")
        if '(r"둥글까$"' in target.read_text(encoding="utf-8"):
            raise RuntimeError("RED setup: fix line still present after revert")
    return dest


def _apply_chain(repo: Path) -> None:
    for script in HOTFIX_CHAIN:
        subprocess.run([sys.executable, script], check=True, cwd=repo, capture_output=True)


def _candidate():
    # Exact Run 34601308285 fields: SHORTS_TOPIC and the printed Core Question
    # line. The hook field itself was not printed in production logs (no raw
    # candidate dump exists in generator.log), so both plausible shapes are
    # exercised: the hook mirroring core_question, and the hook mirroring the
    # fixed topic phrased as a question. Both independently reduce to the
    # same "...왜 둥글까" shape once "왜" is stripped and reach the identical
    # ValueError in the real trace -- see main() below.
    topic = "비행기 창문 모서리는 왜 둥글까"
    core_question = "왜 비행기 창문 모서리는 둥글게 디자인되었을까?"
    return topic, core_question


def _run_case(repo: Path, hook: str, *, topic: str = "", core_question: str = ""):
    sys.path.insert(0, str(repo))
    for mod in list(sys.modules):
        if mod == "content" or mod.startswith("content."):
            del sys.modules[mod]
    import content.script_engine_v2 as engine

    if not topic and not core_question:
        topic, core_question = _candidate()
    candidate = {
        "topic": topic,
        "core_question": core_question,
        "micro_narrative": {
            "hook": hook,
            "core_question": core_question,
            "reveal": "둥근 모서리는 응력이 한 지점에 집중되는 것을 줄입니다.",
            "payoff": "그래서 창문 주변의 응력 집중을 줄이는 데 도움이 됩니다.",
        },
        "fact_check_focus": ["rounded aircraft window"],
        "visual_proof": ["modern passenger aircraft rounded window"],
        "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
        "subject_kind": "physical_entity",
    }
    sys.path.remove(str(repo))
    return engine._grounded_opening(candidate)


def _cleanup(repo: Path):
    shutil.rmtree(repo.parent, ignore_errors=True)


def red():
    repo = _prepare_worktree(apply_fix=False)
    try:
        _apply_chain(repo)
        topic, core_question = _candidate()
        for label, hook in (
            ("core-question-shaped hook", core_question),
            ("topic-shaped hook", topic + "?"),
        ):
            try:
                _run_case(repo, hook)
            except ValueError as exc:
                assert "observable statement" in str(exc), (label, str(exc))
            else:
                raise AssertionError(f"RED setup invalid: {label} unexpectedly passed")
        print("RUN 34601308285 SCENE1 OBSERVABLE OPENING RED: PASS (reproduces production ValueError)")
    finally:
        _cleanup(repo)


def green():
    repo = _prepare_worktree(apply_fix=True)
    try:
        _apply_chain(repo)
        topic, core_question = _candidate()

        for label, hook in (
            ("core-question-shaped hook", core_question),
            ("topic-shaped hook", topic + "?"),
        ):
            hook_out, question_out = _run_case(repo, hook)
            assert hook_out == "비행기 창문 모서리는 둥급니다.", (label, hook_out)
            assert "?" not in hook_out
            assert question_out == "그런데 " + core_question, (label, question_out)

        # Negative control: already-valid observable statement passes through
        # untouched (gate never triggers for a non-question hook).
        already = _run_case(repo, "비행기 창문 모서리는 둥글게 생겼습니다.")
        assert already[0] == "비행기 창문 모서리는 둥글게 생겼습니다."

        # Negative control: a different adjective-stem "-까" ending that was
        # never observed in any incident stays fail-closed -- proves no
        # broad adjective-class or generic "왜 X?" regex was introduced. Both
        # hook AND topic are deliberately unrelated to this run's own
        # "...둥글까" topic, so neither the hook-side match nor the grounded
        # topic-question fallback can accidentally succeed through it.
        for bad_hook, bad_topic in (
            ("이 창문은 왜 클까?", "비행기 창문 크기 비교"),
            ("이 통로는 왜 좁을까?", "기내 통로 폭"),
        ):
            try:
                _run_case(repo, bad_hook, topic=bad_topic, core_question="그런데 " + bad_hook)
            except ValueError as exc:
                assert "observable statement" in str(exc)
            else:
                raise AssertionError(f"unsupported adjective ending must stay fail-closed: {bad_hook}")

        # Negative control: unknown/abstract subject with no embedded
        # physical observation stays fail-closed.
        try:
            _run_case(
                repo,
                "이 현상은 왜 그럴까?",
                topic="알 수 없는 현상",
                core_question="그런데 왜 그럴까?",
            )
        except ValueError as exc:
            assert "observable statement" in str(exc)
        else:
            raise AssertionError("unknown-subject question must stay fail-closed")

        # Regression: existing sibling literal patterns in the same list are
        # untouched. Distinct, unrelated topics isolate the hook-side match
        # itself from this run's own grounded topic-question fallback.
        h, _ = _run_case(
            repo, "비행기 창문은 왜 둥근가?",
            topic="비행기 창문 모양", core_question="그런데 왜 둥근가?",
        )
        assert h == "비행기 창문은 둥급니다."
        h, _ = _run_case(
            repo, "왜 비행기 창문은 둥글게 설계되었을까?",
            topic="기내 압력 조절 시스템의 창문 디자인", core_question="그런데 왜 설계되었을까?",
        )
        assert h == "비행기 창문은 둥글게 설계되었습니다."
        h, _ = _run_case(
            repo, "이 부품은 왜 있을까?",
            topic="부품 필요성", core_question="그런데 왜 있을까?",
        )
        assert h == "이 부품은 있습니다."

        print("RUN 34601308285 SCENE1 OBSERVABLE OPENING GREEN: PASS")
        print("RUN 34601308285 SCENE1 OBSERVABLE OPENING NEGATIVE CONTROLS: PASS")
        print("RUN 34601308285 SCENE1 OBSERVABLE OPENING REGRESSION CONTROLS: PASS")
    finally:
        _cleanup(repo)


def main():
    red()
    green()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--red-only", action="store_true")
    args = parser.parse_args()
    if args.red_only:
        red()
    else:
        main()
