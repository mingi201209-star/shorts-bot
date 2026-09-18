"""Strengthen the Hook/Core-Question guidance from PR #403 into an
unconditional, complete requirement.

Authority: Development Engine run 35310570913 re-dispatched the exact same
fixed topic ("비행기 창문 모서리는 왜 둥글게 만들어졌을까") after PR #403 and #404
landed, and still exhausted all 7/7 Candidate attempts with the identical
rejection ("hook이 Core Question과 같은 내용을 반복합니다"). This shows PR #403's
descriptive guidance ("HOOK을 쓸 때 다음 중 하나를 담아라") reduced but did not
eliminate the failure: a prior post-#403 run (35307975489) succeeded by
attempt 6, this one failed all 7 -- the guidance was read as optional/
stylistic rather than a hard requirement, and only named 6 of the
validator's 12 marker words.

`_hook_restates_question` (ci_writer_observable_opening_hotfix.py) is
lenient whenever the hook contains any of its 12
`_MICRO_HOOK_CLAIM_MARKERS` (only the degenerate near-total-overlap case is
still rejected), and the core question almost always contains one of
`_MICRO_QUESTION_MARKERS` ("왜", "이유", "무엇", "어떻게", "어째서", "?"), so a
hook missing a marker is rejected whenever it shares >=50% of its content
words with the question -- which a "왜 ~ 까" topic's natural hook nearly
always does.

Fix: restate the rule as an unconditional, exception-free requirement
("필수 규칙 (예외 없음)"), name the complete 12-marker allowlist (not just
6), and add an explicit self-check instruction plus a warning against the
marker-only-no-new-information degenerate case. Purely additive prompt
guidance -- no validator logic, threshold, retry, or budget constant
touched.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The prompt still shows fully-inflected worked-example forms; the
# validator (since the stem-matching fix below) matches on each one's bound
# stem, so every full form here must literally contain its stem.
_PROMPT_MARKER_FORMS_TO_STEM = {
    "일부러": "일부러",
    "의도적으로": "의도적",
    "고의로": "고의",
    "아니다": "아니",
    "아닙니다": "아닙",
    "아니라": "아니",
    "않습니다": "않",
    "않는다": "않",
    "사실은": "사실",
    "실제로는": "실제",
    "오히려": "오히려",
    "대신": "대신",
}


def case_a_full_marker_allowlist_present_and_matches_validator_stems():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    hotfix_text = (ROOT / "ci_writer_observable_opening_hotfix.py").read_text(encoding="utf-8")
    for full_form, stem in _PROMPT_MARKER_FORMS_TO_STEM.items():
        assert full_form in text, f"prompt missing full form: {full_form}"
        assert stem in full_form, f"stem {stem} not contained in its own full form {full_form}"
        assert stem in hotfix_text, f"validator missing stem: {stem}"
    print("CASE A complete marker allowlist present in prompt and matches validator stems: PASS")


def case_b_rule_is_stated_as_unconditional_requirement():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    assert "필수 규칙" in text
    assert "예외 없음" in text
    assert "반드시 하나 이상을 포함해야 한다" in text
    print("CASE B rule stated as unconditional requirement: PASS")


def case_c_degenerate_marker_only_case_still_warned_against():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    assert "마커만 붙이고 주어만 반복하는 것으로는 부족하다" in text
    print("CASE C degenerate marker-only case explicitly warned against: PASS")


def case_d_original_worked_examples_still_present():
    text = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
    assert "비행기 창문 모서리는 둥급니다." in text
    assert "비행기 창문 모서리는 일부러 둥글게 만듭니다." in text
    assert "각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?" in text
    print("CASE D original PR #403 worked examples preserved: PASS")


def case_e_no_threshold_budget_retry_or_validator_logic_touched():
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
    print("CASE E no threshold/budget/retry constant or validator logic touched: PASS")


def main():
    case_a_full_marker_allowlist_present_and_matches_validator_stems()
    case_b_rule_is_stated_as_unconditional_requirement()
    case_c_degenerate_marker_only_case_still_warned_against()
    case_d_original_worked_examples_still_present()
    case_e_no_threshold_budget_retry_or_validator_logic_touched()
    print("CANDIDATE EXPLORER HOOK MARKER REQUIREMENT REGRESSION: PASS")


if __name__ == "__main__":
    main()
