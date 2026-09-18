"""Novelty Judge rubric calibration: separate "subject is named in the title"
from "the mechanism/reveal is guessable from the title".

Authority: Run 35303531397 tested a genuinely new, never-before-attempted
grounded subject (jet-engine chevron). Prewriter Novelty (which only sees the
terse hook/core_question/reveal/payoff) scored it 6.0/10, but the full
post-Writer Novelty Judge (same rubric, full 5-scene script) scored it 4.0/10
both before and after a Rewrite, with reasoning that repeatedly cited
"제목만으로도 대략적인 내용을 예상할 수 있어" (guessable from the title alone).
Every candidate topic in this system is, by design, named after the visible
physical subject it explains (e.g. "비행기 엔진 뒤쪽의 톱니 모양 가장자리") --
so if the Novelty rubric's criterion 2 ("제목만 보고 답을 쉽게 예상할 수 있는가")
is read as "the subject is nameable from the title", every candidate is
structurally unable to pass regardless of how obscure the underlying
mechanism actually is.

Fix: clarify criterion 2 in quality/judge.py's Novelty criteria so it
distinguishes "the visible subject is named in the title" (expected, not a
penalty) from "the mechanism/reveal itself is guessable from the title alone"
(the actual criterion). Also add explicit 0-10 score anchors, since the
un-anchored scale invited inconsistent scoring for the same topic. No numeric
threshold (NOVELTY_HARD_REGENERATE_SCORE, _PREWRITER_NOVELTY_MIN_SCORE) is
touched -- only the judge's own calibration is clarified.
"""
from quality.judge import build_judge_prompt


def case_a_criterion_two_distinguishes_subject_naming_from_mechanism_guessing():
    prompt = build_judge_prompt("novelty", {"title": "x", "topic": "x", "scenes": []})
    assert "대상의 이름이 제목에 있다는 이유만으로" in prompt
    assert "2번 기준을 위반했다고 판단하지 마라" in prompt
    assert "mechanism" in prompt or "실제 이유" in prompt
    print("CASE A criterion 2 clarification present: PASS")


def case_b_score_anchors_present():
    prompt = build_judge_prompt("novelty", {"title": "x", "topic": "x", "scenes": []})
    for anchor in ("0~2:", "3~4:", "5~6:", "7~8:", "9~10:"):
        assert anchor in prompt, anchor
    print("CASE B explicit 0-10 score anchors present: PASS")


def case_c_other_judge_types_unchanged():
    for judge_type in ("hook", "fact", "visual"):
        prompt = build_judge_prompt(judge_type, {"title": "x", "topic": "x", "scenes": []})
        assert "2번 기준을 위반했다고 판단하지 마라" not in prompt
        assert "0~2:" not in prompt
    print("CASE C hook/fact/visual judges untouched: PASS")


def case_d_no_threshold_constant_touched():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    text = (root / "quality" / "judge.py").read_text(encoding="utf-8")
    forbidden = (
        "NOVELTY_HARD_REGENERATE_SCORE =",
        "_PREWRITER_NOVELTY_MIN_SCORE =",
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "MAX_TOPIC_REGENERATIONS =",
    )
    for token in forbidden:
        assert token not in text, f"unexpectedly touched {token}"
    print("CASE D no numeric threshold constant touched: PASS")


def main():
    case_a_criterion_two_distinguishes_subject_naming_from_mechanism_guessing()
    case_b_score_anchors_present()
    case_c_other_judge_types_unchanged()
    case_d_no_threshold_constant_touched()
    print("NOVELTY JUDGE TITLE-GUESSABILITY CALIBRATION REGRESSION: PASS")


if __name__ == "__main__":
    main()
