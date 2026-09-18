"""Teach the Candidate Explorer the hook/core_question contract it is
already held to.

Authority: Development Engine dispatch with a fixed topic ("비행기 창문
모서리는 왜 둥글게 만들어졌을까") failed all 7/7 Candidate attempts with the
identical reason: "winner.micro_narrative hook이 Core Question과 같은 내용을
반복합니다. 첫 두 beat는 새 정보를 전진시켜야 합니다." (Run 35306883492).

That rejection comes from `_validate_hook_question_progression` /
`_hook_restates_question`, injected by ci_writer_observable_opening_hotfix.py
(Run 34625637738 / PR #330) and already locked in by
quality/script_human_quality_v1_regression_test.py's CASE 1/CASE 2: a bare
physical-observation hook followed by a generic "왜 ~ 까요?" question is
rejected, and a hook that carries an explicit intent/twist marker (e.g.
"일부러") paired with a more specific question is accepted. That contract is
correct and deliberately tested -- this is not a validator bug.

The actual gap: content/candidate_explorer.py's own prompt (PHASE 2B — MICRO
NARRATIVE) explains what HOOK/CORE QUESTION/REVEAL/PAYOFF each are, but never
tells the model about this specific rejection rule or shows it the worked
good/bad example the validator and regression suite already encode. The
model was being held to a contract it was never shown, so for a topic whose
natural phrasing is itself a "왜 ~ 까" question, it kept regenerating the same
disallowed shape on every one of its 7 attempts and never reached the
Script Writer at all -- burning the whole Candidate budget on a topic that
`quality/production_safe_topic_pool.py` already lists as production-safe.

Fix: teach the Explorer prompt the same CASE 1 (bad) / CASE 2 (good) example
already codified in quality/script_human_quality_v1_regression_test.py, and
name the specific marker words the deterministic validator's claim-marker
allowlist checks for. Purely additive prompt guidance -- no validator logic,
threshold, retry, or budget constant touched.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def case_a_hook_question_relationship_guidance_present():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    assert "HOOK와 CORE QUESTION의 관계" in text
    assert "자동으로 REGENERATE된다" in text
    print("CASE A hook/core_question relationship guidance present: PASS")


def case_b_worked_bad_and_good_examples_match_the_locked_in_regression_cases():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    # Exact strings from quality/script_human_quality_v1_regression_test.py's
    # test_case1_statement_then_identical_question_rejected /
    # test_case2_same_subject_progressing_information_accepted, so the
    # prompt teaches the model precisely the contract the validator enforces.
    assert "비행기 창문 모서리는 둥급니다." in text
    assert "비행기 창문 모서리는 일부러 둥글게 만듭니다." in text
    assert "각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?" in text
    print("CASE B worked examples match the locked-in regression cases: PASS")


def case_c_marker_words_named_match_the_validators_own_allowlist():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    hotfix_text = (ROOT / "ci_writer_observable_opening_hotfix.py").read_text(encoding="utf-8")
    for marker in ("일부러", "의도적으로", "사실은", "실제로는", "오히려", "대신"):
        assert marker in text, marker
        assert marker in hotfix_text, marker
    print("CASE C named marker words match the deterministic validator's own allowlist: PASS")


def case_d_no_threshold_budget_retry_or_validator_logic_touched():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    forbidden = (
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "MAX_TOPIC_REGENERATIONS =",
        "NOVELTY_HARD_REGENERATE_SCORE =",
        "_PREWRITER_NOVELTY_MIN_SCORE =",
        "def _hook_restates_question",
        "def _validate_hook_question_progression",
    )
    for token in forbidden:
        assert token not in text, f"unexpectedly touched {token}"
    print("CASE D no threshold/budget/retry constant or validator logic touched: PASS")


def main():
    case_a_hook_question_relationship_guidance_present()
    case_b_worked_bad_and_good_examples_match_the_locked_in_regression_cases()
    case_c_marker_words_named_match_the_validators_own_allowlist()
    case_d_no_threshold_budget_retry_or_validator_logic_touched()
    print("CANDIDATE EXPLORER HOOK/QUESTION PROGRESSION GUIDANCE REGRESSION: PASS")


if __name__ == "__main__":
    main()
