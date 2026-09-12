import copy

import quality.rewrite_engine as rewrite_engine


def _assert(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def _script(text):
    return {
        "title": "test",
        "scenes": [
            {
                "text": text,
                "visual_goal": "테스트 대상이 화면 중앙에 보이는 장면",
                "keyword": "test visible subject",
            }
        ],
    }


def _consensus():
    return {
        "domain_summaries": {
            "hook": {
                "score": 6.0,
                "confidence": 0.9,
                "critical_risk": False,
                "disagreement": 0.0,
                "issues": ["hook wording"],
            }
        }
    }


def test_rewrite_repairs_safe_formal_ending_without_second_llm_call():
    original = _script("원래 대사는 자연스러운 격식체입니다.")
    output = _script("창문은 둥근 형태로 되어 있는데요.")
    calls = {"count": 0}
    original_call = rewrite_engine._run_rewrite_call

    def fake_call(*args, **kwargs):
        del args, kwargs
        calls["count"] += 1
        return copy.deepcopy(output)

    rewrite_engine._run_rewrite_call = fake_call
    try:
        result = rewrite_engine.rewrite_script(original, _consensus())
    finally:
        rewrite_engine._run_rewrite_call = original_call

    _assert("repairable casual Rewrite uses one LLM call", calls["count"] == 1)
    _assert(
        "safe terminal form is repaired deterministically",
        result["script_data"]["scenes"][0]["text"]
        == "창문은 둥근 형태로 되어 있습니다.",
    )


def test_rewrite_falls_back_without_second_call_when_repair_is_unsafe():
    original = _script("원래 대사는 자연스러운 격식체입니다.")
    calls = {"count": 0}
    original_call = rewrite_engine._run_rewrite_call

    def fake_call(*args, **kwargs):
        del args, kwargs
        calls["count"] += 1
        return _script("이 차이가 정말 중요하네요.")

    rewrite_engine._run_rewrite_call = fake_call
    try:
        result = rewrite_engine.rewrite_script(original, _consensus())
    finally:
        rewrite_engine._run_rewrite_call = original_call

    _assert("unrepairable non-FACT Rewrite stays at one LLM call", calls["count"] == 1)
    _assert(
        "unsafe non-formal Rewrite never replaces the original narration",
        result["script_data"]["scenes"][0]["text"]
        == original["scenes"][0]["text"],
    )


def test_rewrite_prompt_requires_formal_endings():
    prompt = rewrite_engine.build_rewrite_prompt(
        _script("비행기 엔진은 날개 아래에 장착되어 있습니다."),
        _consensus(),
        ["hook"],
    )

    _assert(
        "Rewrite prompt requires formal declarative endings",
        "~습니다/~입니다/~합니다/~됩니다/~있습니다" in prompt,
    )
    _assert(
        "production counterexample is explicitly prohibited",
        "알고 계셨나요?" in prompt and "사용하지 않는다" in prompt,
    )
    _assert(
        "formal source is not needlessly converted to a question",
        "격식체 평서문이면 가능하면 질문형으로 바꾸지 않는다" in prompt,
    )


def main():
    test_rewrite_prompt_requires_formal_endings()
    test_rewrite_repairs_safe_formal_ending_without_second_llm_call()
    test_rewrite_falls_back_without_second_call_when_repair_is_unsafe()
    print("✅ Rewrite formal speech-style regression suite passed")


if __name__ == "__main__":
    main()
