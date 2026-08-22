from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content.candidate_recovery import (
    make_recovery_record,
    recovery_eligibility,
    select_best_recovery,
)


def candidate(topic="날개 끝 윙렛의 실제 역할", reveal="날개 끝 와류를 줄여 유도항력을 낮춘다"):
    return {
        "topic": topic,
        "angle": "익숙한 구조의 구체적인 설계 이유",
        "core_question": "왜 날개 끝은 위로 꺾여 있을까?",
        "micro_narrative": {
            "hook": "날개 끝이 위로 꺾인 건 장식이 아닙니다.",
            "core_question": "왜 굳이 이렇게 만들었을까요?",
            "reveal": reveal,
            "payoff": "작은 끝단 구조가 비행 전체의 에너지 손실을 줄입니다.",
        },
        "fact_check_focus": ["winglets reduce induced drag under relevant conditions"],
        "visual_proof": ["visible upturned wingtip"],
    }


def test_soft_editorial_reject_is_recoverable():
    gate = {
        "status": "REGENERATE",
        "reason": "결론이 다소 예상 가능하고 두 번째 인과 단계가 약합니다.",
    }
    eligible, reason = recovery_eligibility(candidate(), gate)
    assert eligible is True
    assert reason == "soft_editorial_reject"


def test_hard_grounding_reject_is_never_recoverable():
    gate = {
        "status": "REGENERATE",
        "reason": "핵심 인과관계에 근거가 없어 검증 불가능합니다.",
    }
    eligible, reason = recovery_eligibility(candidate(), gate)
    assert eligible is False
    assert reason == "hard_grounding_reject"


def test_placeholder_is_never_recoverable():
    bad = candidate(topic="placeholder candidate")
    gate = {
        "status": "REGENERATE",
        "reason": "Payoff가 약합니다.",
    }
    record = make_recovery_record(bad, gate, attempt=1)
    assert record is None


def test_best_grounded_candidate_is_selected_deterministically():
    gate = {
        "status": "REGENERATE",
        "reason": "Payoff가 조금 예상 가능합니다.",
    }
    weaker = candidate(
        topic="약한 후보",
        reveal="구조가 공기 흐름에 영향을 줍니다.",
    )
    weaker["fact_check_focus"] = []
    weaker["visual_proof"] = []

    stronger = candidate(
        topic="강한 후보",
        reveal="압력 차로 생기는 끝단 와류를 줄여 유도항력 손실을 낮춥니다.",
    )

    records = [
        make_recovery_record(weaker, gate, attempt=1),
        make_recovery_record(stronger, gate, attempt=2),
    ]
    selected = select_best_recovery(records)
    assert selected is not None
    assert selected["candidate"]["topic"] == "강한 후보"


def test_no_recoverable_candidate_stays_terminal():
    assert select_best_recovery([]) is None
    assert select_best_recovery([None]) is None


def main():
    test_soft_editorial_reject_is_recoverable()
    print("CASE A soft editorial recovery: PASS")
    test_hard_grounding_reject_is_never_recoverable()
    print("CASE B hard grounding exclusion: PASS")
    test_placeholder_is_never_recoverable()
    print("CASE C placeholder exclusion: PASS")
    test_best_grounded_candidate_is_selected_deterministically()
    print("CASE D deterministic strongest selection: PASS")
    test_no_recoverable_candidate_stays_terminal()
    print("CASE E terminal without recoverable candidate: PASS")
    print("CANDIDATE GROUNDED RECOVERY REGRESSION: PASS")


if __name__ == "__main__":
    main()
