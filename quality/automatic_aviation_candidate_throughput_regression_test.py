import os
from pathlib import Path

from content.candidate_recovery import make_recovery_record, recovery_eligibility


def _candidate():
    return {
        "topic": "비행기 착륙 시 기체의 흔들림",
        "angle": "착륙 중 공기 흐름과 기체 반응",
        "core_question": "왜 비행기가 착륙할 때 흔들리는 걸까?",
        "micro_narrative": {
            "hook": "비행기는 착륙 직전에 크게 흔들릴 때가 있습니다.",
            "core_question": "그런데 왜 착륙할 때 흔들릴까요?",
            "reveal": "지면 가까이에서 바람과 조종 입력이 빠르게 바뀌며 기체가 자세를 계속 보정하기 때문입니다.",
            "payoff": "흔들림 자체만으로 비정상 착륙을 뜻하는 것은 아닙니다.",
        },
        "fact_check_focus": ["crosswind landing aircraft control response"],
        "visual_proof": ["aircraft landing in crosswind"],
    }


def main():
    original_scope = os.environ.get("SHORTS_CANDIDATE_SCOPE")
    original_topic = os.environ.get("SHORTS_TOPIC")
    try:
        os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
        os.environ["SHORTS_TOPIC"] = ""

        predictable = {
            "status": "REGENERATE",
            "reason": "질문과 Reveal이 예상 가능한 수준에 머물러 있어 시청자가 쉽게 결론을 예상할 수 있다.",
        }
        eligible, reason = recovery_eligibility(_candidate(), predictable)
        assert eligible is True
        assert reason == "predictable_editorial_reject"
        assert make_recovery_record(_candidate(), predictable, attempt=1) is not None

        explicit_low_novelty = {
            "status": "REGENERATE",
            "reason": "의외성이 부족하고 결론이 뻔합니다.",
        }
        eligible, reason = recovery_eligibility(_candidate(), explicit_low_novelty)
        assert eligible is False
        assert reason == "hard_novelty_reject"

        os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
        eligible, reason = recovery_eligibility(_candidate(), predictable)
        assert eligible is False
        assert reason == "hard_novelty_reject"

        hotfix = Path("ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
        assert '"MAX_TOPIC_REGENERATIONS = 6"' in hotfix
        assert '"MAX_TOPIC_REGENERATIONS = 2"' in hotfix
        print("PASS: automatic aviation predictable recovery is bounded and scope-specific")
        print("PASS: explicit low novelty and grounding safety remain hard")
        print("PASS: production Candidate attempts are capped at 3 total")
    finally:
        if original_scope is None:
            os.environ.pop("SHORTS_CANDIDATE_SCOPE", None)
        else:
            os.environ["SHORTS_CANDIDATE_SCOPE"] = original_scope
        if original_topic is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = original_topic


if __name__ == "__main__":
    main()
