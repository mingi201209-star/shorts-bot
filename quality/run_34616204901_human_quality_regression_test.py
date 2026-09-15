import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.human_quality_floor import opening_repeat_issue, normalize_aircraft_window_opening


def main():
    bad = [
        {"text": "비행기 창문 모서리는 둥글게 되어 있습니다."},
        {"text": "그런데 비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?"},
    ]
    assert opening_repeat_issue(bad), "repetitive Scene 2 reason-question must be rejected"

    good = [
        {"text": "비행기 창문은 네모가 아니라 모서리가 둥근 형태입니다."},
        {"text": "그 곡선은 동체에 걸리는 응력이 한곳에 몰리는 것을 줄입니다."},
    ]
    assert opening_repeat_issue(good) is None

    candidate = {
        "topic": "비행기 창문 모서리는 왜 둥글까",
        "core_question": "비행기 창문 모서리가 둥근 이유는 무엇일까요?",
        "micro_narrative": {
            "hook": "비행기 창문 모서리는 둥글게 되어 있습니다.",
            "core_question": "비행기 창문 모서리가 둥근 이유는 무엇일까요?",
            "payoff": "피로 균열이 동체 파열로 빠르게 이어질 수 있었습니다",
        },
    }
    fixed = normalize_aircraft_window_opening(candidate)
    assert fixed["micro_narrative"]["hook"] == "비행기 창문은 네모가 아니라 모서리가 둥근 형태입니다."
    assert fixed["micro_narrative"]["core_question"] == "그런데 왜 굳이 이런 모양일까요?"
    assert "빠르게" not in fixed["micro_narrative"]["payoff"]

    unrelated = {
        "topic": "도시 지하 배수관",
        "micro_narrative": {"hook": "도시 아래에는 배수관이 있습니다."},
    }
    assert normalize_aircraft_window_opening(unrelated) == unrelated
    print("PASS: deterministic human-quality helper regression")


if __name__ == "__main__":
    main()
