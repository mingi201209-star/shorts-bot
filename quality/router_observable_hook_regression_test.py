from content.script_generator_router import _observable_hook_from_candidate


def main():
    candidate = {
        "topic": "비행기 엔진은 날개 아래에 단다",
        "micro_narrative": {
            "hook": "왜 비행기 엔진은 날개 아래에 장착될까?",
            "core_question": "왜 비행기 엔진은 날개 아래에 장착될까?",
        },
    }
    normalized = _observable_hook_from_candidate(candidate)
    assert normalized["micro_narrative"]["hook"] == "비행기 엔진은 날개 아래에 답니다."
    assert normalized["micro_narrative"]["core_question"] == candidate["micro_narrative"]["core_question"]
    assert candidate["micro_narrative"]["hook"].endswith("?")

    fail_closed = {
        "topic": "비행기 엔진 위치의 비밀",
        "micro_narrative": {"hook": "왜 엔진 위치가 중요할까?"},
    }
    assert _observable_hook_from_candidate(fail_closed)["micro_narrative"]["hook"].endswith("?")
    print("ROUTER OBSERVABLE HOOK REGRESSION: PASS")


if __name__ == "__main__":
    main()
