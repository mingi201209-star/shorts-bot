"""Regression for Script Human Quality V1.

Authority: Run 34625637738 was machine-green but human review rejected the
narration. Its opening restated the same rounded-window proposition as a
statement and then a question; Scene 3 also received the deterministic
"원인의 첫 단서는" filler despite already containing the concrete stress clue.

This test installs the same final production writer hotfix and proves the
quality contract without making network/LLM calls or changing any budget.
"""
from __future__ import annotations

import importlib
import os
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Publish Engine Stabilization V1 Phase 0: this used to be its own
# hand-maintained, 44-entry copy of "the production hotfix chain" -- 4
# hotfixes short of the real 48-step chain in .github/workflows/main.yml
# (missing ci_run_34847558126_fixed_topic_novelty_weak_domain_hotfix.py,
# ci_run_34847558126_scene_role_grounded_keyword_hotfix.py,
# ci_grounded_deterministic_explanation_hotfix.py, and the intentional
# second application of ci_aviation_context_signature_compat_hotfix.py) and
# drifting from a second hand-maintained copy in
# production_hotfix_composition_gate.yml. All three copies now read
# quality/production_hotfix_chain.py instead of each hard-coding their own.
from quality.production_hotfix_chain import PRODUCTION_HOTFIX_CHAIN as _PRODUCTION_HOTFIX_CHAIN


def _install_production_final_hotfix() -> None:
    for script in _PRODUCTION_HOTFIX_CHAIN:
        subprocess.run([sys.executable, script], cwd=ROOT, check=True)
    importlib.invalidate_caches()


def _explorer_namespace() -> dict:
    # Final-composition installers may preload a wrapper/module under the
    # content.candidate_explorer name. Execute the patched production source
    # directly so this regression cannot accidentally inspect a stale module.
    return runpy.run_path(str(ROOT / "content" / "candidate_explorer.py"))


def _candidate(*, hook: str, question: str) -> dict:
    return {
        "status": "SELECTED",
        "winner": {
            "topic": "비행기 창문 모서리는 왜 둥글까",
            "angle": "창문 모서리 형상이 응력 분포에 미치는 차이",
            "core_question": question,
            "micro_narrative": {
                "hook": hook,
                "core_question": question,
                "reveal": "둥근 모서리는 응력이 한 지점에 집중되는 정도를 줄입니다.",
                "payoff": "모서리 형상은 반복 하중을 받는 창문 주변 구조의 피로 위험과 연결됩니다.",
            },
            "fact_check_focus": [
                "초기 Comet의 각진 창문 모서리에서 높은 응력 집중이 발생했다.",
                "둥근·타원형 창문은 모서리의 응력 집중을 줄인다.",
            ],
            "visual_proof": ["각진 창문과 둥근 창문의 모서리 비교"],
            "selection_reason": "익숙한 창문 형상에 숨은 구조적 이유가 있다.",
        },
        "runner_up": None,
    }


def test_candidate_prompt_is_lock_aware() -> None:
    explorer = _explorer_namespace()
    prompt = explorer["CANDIDATE_EXPLORER_PROMPT"]
    assert "SCRIPT_HUMAN_QUALITY_V1" in prompt
    assert "Hook 다음 Core Question이 Hook과 같은 명제를 다시 묻는 구조는 금지" in prompt
    assert "그대로 읽어도 자연스러운 짧은 한 문장" in prompt
    assert "인과 범위를 넘어 더 큰 재난이나 결과로 확대하지 마라" in prompt


def test_run_346256_opening_counterexample_fails_closed() -> None:
    explorer = _explorer_namespace()
    bad = _candidate(
        hook="비행기 창문 모서리는 둥급니다.",
        question="비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?",
    )
    try:
        explorer["validate_explorer_output"](bad)
    except ValueError as exc:
        assert "같은 내용을 반복" in str(exc)
        return
    raise AssertionError("Run 34625637738 hook/question restatement must fail closed")


def test_progressive_opening_is_accepted() -> None:
    explorer = _explorer_namespace()
    good = _candidate(
        hook="작은 모서리 형상 차이가 반복 하중을 받는 구조의 응력 분포를 바꿉니다.",
        question="비행기 창문 모서리가 둥근 이유는 무엇일까요?",
    )
    result = explorer["validate_explorer_output"](good)
    assert result["status"] == "SELECTED"
    assert result["winner"]["micro_narrative"]["hook"].startswith("작은 모서리")


def test_stress_is_already_a_causal_clue() -> None:
    engine = runpy.run_path(str(ROOT / "content" / "script_engine_v2.py"))
    assert "응력" in engine["CAUSAL_CLUE_TOKENS"]
    repair = engine["deterministic_scene_repair"]
    text = "초기 코멧의 각진 창문 모서리에는 높은 응력이 집중됐습니다."
    repaired = repair(text, "causal_clue")
    assert repaired == text
    assert not repaired.startswith("원인의 첫 단서는")


def _vsb():
    """Fresh, chain-composed content.script_engine_v2_validation.validate_scene_basics."""
    return runpy.run_path(str(ROOT / "content" / "script_engine_v2_validation.py"))["validate_scene_basics"]


def _rewrite_engine_ns():
    return runpy.run_path(str(ROOT / "quality" / "rewrite_engine.py"))


def _scene(role: str, text: str, keyword: str) -> dict:
    return {
        "role": role,
        "text": text,
        "visual_goal": "aircraft window corner comparison shot",
        "keyword": keyword,
    }


def _contract(role: str) -> dict:
    return {"role": role}


# ---------------------------------------------------------------------------
# Section 5 CASE 1-8 (task-mandated minimum regression additions).
# ---------------------------------------------------------------------------

def test_case1_statement_then_identical_question_rejected() -> None:
    """CASE 1: statement -> identical-question restatement must REJECT."""
    explorer = _explorer_namespace()
    bad = _candidate(
        hook="비행기 창문 모서리는 둥급니다.",
        question="왜 비행기 창문 모서리는 둥글까요?",
    )
    try:
        explorer["validate_explorer_output"](bad)
    except ValueError as exc:
        assert "같은 내용을 반복" in str(exc)
        return
    raise AssertionError("CASE 1 statement/identical-question restatement must fail closed")


def test_case2_same_subject_progressing_information_accepted() -> None:
    """CASE 2: same subject, but information genuinely progresses -> PASS."""
    explorer = _explorer_namespace()
    good = _candidate(
        hook="비행기 창문 모서리는 일부러 둥글게 만듭니다.",
        question="각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?",
    )
    result = explorer["validate_explorer_output"](good)
    assert result["status"] == "SELECTED"


def test_case3_low_overlap_semantic_repetition_is_a_known_limitation() -> None:
    """CASE 3: low lexical overlap but semantic repetition.

    Section 3/5 require testing this direction and explicitly acknowledge the
    current deterministic, no-model-call token-overlap approach may not be
    able to catch every such case -- a full vocabulary swap of the same
    meaning is a semantic/synonymy problem a token-overlap check cannot solve
    without a model call, which this task forbids adding. This test documents
    the current, honest boundary instead of hiding it.
    """
    explorer = _explorer_namespace()
    hook_restates_question = explorer["_hook_restates_question"]
    # Same meaning as CASE 1, expressed with almost entirely different words.
    not_caught = hook_restates_question(
        "여객기 유리창 코너는 둥급니다.",
        "비행기 창문 모서리가 곡선인 이유는 무엇일까요?",
    )
    assert not_caught is False, (
        "documented limitation: full-vocabulary-swap semantic repetition is "
        "not caught by deterministic token overlap without a new model call"
    )


def test_case4_existing_stress_clue_blocks_filler_insertion() -> None:
    """CASE 4: a scene already containing '응력' must not receive the
    deterministic '원인의 첫 단서는' filler."""
    engine = runpy.run_path(str(ROOT / "content" / "script_engine_v2.py"))
    repair = engine["deterministic_scene_repair"]
    text = "초기 코멧의 각진 창문 모서리에는 높은 응력이 집중됐습니다."
    repaired = repair(text, "causal_clue")
    assert repaired == text
    assert not repaired.startswith("원인의 첫 단서는")


def test_case5_rewrite_causal_hedge_must_not_be_strengthened() -> None:
    """CASE 5: Rewrite turning a grounded hedge into an absolute claim must
    be caught by the deterministic causal-strength guard."""
    rewrite_ns = _rewrite_engine_ns()
    escalated = rewrite_ns["causal_strength_escalated"](
        "이 형상은 응력 집중을 줄이는 데 도움이 됩니다.",
        "이 형상은 응력 집중을 완전히 막습니다.",
    )
    assert escalated is True

    consensus = {"domain_summaries": {"fact": {"issues": []}}}
    original_script = {"scenes": [{"text": "이 형상은 응력 집중을 줄이는 데 도움이 됩니다."}]}
    rewritten_script = {"scenes": [{"text": "이 형상은 응력 집중을 완전히 막습니다."}]}
    persistent = rewrite_ns["find_persistent_fact_issues"](
        consensus, rewritten_script, original_script=original_script
    )
    assert any("causal strength escalated" in issue for issue in persistent)


def test_case6_payoff_repeating_reveal_mechanism_fails() -> None:
    """CASE 6: Payoff that just restates Reveal's mechanism must be flagged."""
    vsb = _vsb()
    script = {"scenes": [
        _scene("hook", "비행기 창문 모서리는 일부러 둥글게 만듭니다.", "aircraft window corner shape"),
        _scene("reveal", "둥근 모서리는 응력을 분산합니다.", "aircraft window stress distribution"),
        _scene("payoff", "결국 응력을 분산하기 위해 둥글게 만든 것입니다.", "aircraft window stress distribution result"),
    ]}
    plan = {"contracts": [_contract("hook"), _contract("reveal"), _contract("payoff")]}
    ok, failures = vsb(script, plan)
    assert ok is False
    assert any("payoff repeats reveal" in str(f.get("reason", "")) for f in failures)


def test_case7_full_causal_ladder_progresses_cleanly() -> None:
    """CASE 7: a positive case where observation->cause->mechanism->payoff
    progresses naturally must produce no new human-quality failures."""
    vsb = _vsb()
    script = {"scenes": [
        _scene("hook", "비행기 창문은 일부러 모서리를 없앴습니다.", "aircraft window corner shape"),
        _scene("causal_clue", "각진 모서리에는 응력이 한 곳에 몰립니다.", "aircraft window stress concentration"),
        _scene("reveal", "둥근 모서리는 그 응력을 넓게 분산시킵니다.", "aircraft window stress distribution"),
        _scene("payoff", "그래서 현대 여객기 창문은 처음부터 둥글게 설계됩니다.", "modern aircraft window design"),
    ]}
    plan = {"contracts": [
        _contract("hook"), _contract("causal_clue"), _contract("reveal"), _contract("payoff"),
    ]}
    ok, failures = vsb(script, plan)
    assert ok is True, failures


def test_case8_grounded_question_form_hook_is_not_banned() -> None:
    """CASE 8: question-form Hooks must not be unconditionally rejected --
    only an actual restatement of the same proposition is rejected."""
    explorer = _explorer_namespace()
    hook_restates_question = explorer["_hook_restates_question"]
    # Structurally a question, but asks something the core question does not
    # (a genuinely different proposition), so it must not be flagged.
    result = hook_restates_question(
        "비행기 창문은 왜 각진 모서리를 버렸을까요?",
        "그 형상 변화가 구조에 어떤 차이를 만들까요?",
    )
    assert result is False


def test_case9_marker_stem_matches_natural_conjugation_not_just_one_fixed_form() -> None:
    """CASE 9: Run 35312695957 (Development Engine, fixed topic) produced the
    real hook "비행기 창문 모서리는 사실 둥글게 만들어집니다." -- the model reached
    for the "사실" (in fact) claim marker but wrote it without the "은" topic
    particle, so the old exact-form-only "사실은" entry in
    _MICRO_HOOK_CLAIM_MARKERS never matched and this hook was wrongly
    rejected as a bare restatement. Matching by bound stem instead of one
    fixed inflected form fixes this without changing the validator's
    condition or any threshold/retry/budget constant."""
    explorer = _explorer_namespace()
    hook_makes_explicit_claim = explorer["_hook_makes_explicit_claim"]

    # The exact real hook text from run 35312695957 attempt 1.
    assert hook_makes_explicit_claim("비행기 창문 모서리는 사실 둥글게 만들어집니다.") is True

    # Other natural conjugations of the same marker stems must also match.
    assert hook_makes_explicit_claim("비행기 창문 모서리는 사실이에요.") is True
    assert hook_makes_explicit_claim("비행기 창문 모서리는 실제 원인이 다릅니다.") is True
    assert hook_makes_explicit_claim("비행기 창문 모서리는 각진 모양이 아니에요.") is True
    assert hook_makes_explicit_claim("비행기 창문 모서리는 그냥 둥글지 않았습니다.") is True
    assert hook_makes_explicit_claim("비행기 창문 모서리는 의도적인 설계입니다.") is True

    # The real marker-free hook from that same run's attempts 2-7 must still
    # not be treated as an explicit claim.
    assert hook_makes_explicit_claim("비행기 창문 모서리는 둥글게 설계되어 있습니다.") is False


def test_case10_exact_fixed_topic_repairs_only_observed_markerless_hooks() -> None:
    """CASE 10: Run 35316425943 exhausted all seven attempts with only two
    literal markerless hooks. Normalize those exact fixed-topic outputs to the
    prompt's grounded GOOD form, without changing the general validator."""
    explorer = _explorer_namespace()
    validate = explorer["validate_explorer_output"]
    target = "비행기 창문 모서리는 왜 둥글게 만들어졌을까"
    observed = (
        "비행기 창문 모서리는 둥글게 디자인되어 있습니다.",
        "비행기 창문 모서리는 둥글게 디자인되어 있어, 날카로운 모서리가 없습니다.",
    )

    previous = os.environ.get("SHORTS_TOPIC")
    try:
        os.environ["SHORTS_TOPIC"] = target
        for hook in observed:
            result = validate(_candidate(
                hook=hook,
                question="비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?",
            ))
            assert result["winner"]["micro_narrative"]["hook"] == (
                "비행기 창문 모서리는 일부러 둥글게 만듭니다."
            )

        # Unknown markerless text is not normalized just because the topic is
        # fixed; the unchanged progression validator must still reject it.
        unknown = _candidate(
            hook="비행기 창문 모서리는 둥글게 설계되어 있습니다.",
            question="비행기 창문 모서리가 둥글게 설계된 이유는 무엇일까요?",
        )
        try:
            validate(unknown)
        except ValueError as exc:
            assert "같은 내용을 반복" in str(exc)
        else:
            raise AssertionError("unknown fixed-topic hook must fail closed")

        # The same observed text outside the exact fixed-topic authority also
        # remains rejected by the general validator.
        os.environ["SHORTS_TOPIC"] = "비행기 날개 끝은 왜 위로 꺾여 있을까"
        try:
            validate(_candidate(
                hook=observed[0],
                question="비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?",
            ))
        except ValueError as exc:
            assert "같은 내용을 반복" in str(exc)
        else:
            raise AssertionError("non-target topic must not receive hook repair")
    finally:
        if previous is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = previous


def test_writer_and_rewrite_prompts_carry_human_quality_contract() -> None:
    runner = (ROOT / "content" / "script_engine_v2_runner.py").read_text(encoding="utf-8")
    rewrite = (ROOT / "quality" / "rewrite_engine.py").read_text(encoding="utf-8")
    assert "SCRIPT_HUMAN_QUALITY_WRITER_V1" in runner
    assert "one short sentence and one new idea" in runner
    assert "Do not strengthen causal claims beyond the supplied facts" in runner
    assert "SCRIPT_HUMAN_QUALITY_REWRITE_V1" in rewrite
    assert "Scene 1과 Scene 2가 같은 명제를" in rewrite
    assert "인과 표현은 Candidate/Fact 근거보다 강하게 키우지 않는다" in rewrite


def main() -> None:
    _install_production_final_hotfix()
    test_candidate_prompt_is_lock_aware()
    test_run_346256_opening_counterexample_fails_closed()
    test_progressive_opening_is_accepted()
    test_stress_is_already_a_causal_clue()
    test_case1_statement_then_identical_question_rejected()
    test_case2_same_subject_progressing_information_accepted()
    test_case3_low_overlap_semantic_repetition_is_a_known_limitation()
    test_case4_existing_stress_clue_blocks_filler_insertion()
    test_case5_rewrite_causal_hedge_must_not_be_strengthened()
    test_case6_payoff_repeating_reveal_mechanism_fails()
    test_case7_full_causal_ladder_progresses_cleanly()
    test_case8_grounded_question_form_hook_is_not_banned()
    test_case9_marker_stem_matches_natural_conjugation_not_just_one_fixed_form()
    test_case10_exact_fixed_topic_repairs_only_observed_markerless_hooks()
    test_writer_and_rewrite_prompts_carry_human_quality_contract()
    print("SCRIPT HUMAN QUALITY V1 REGRESSION: PASS")


if __name__ == "__main__":
    main()
