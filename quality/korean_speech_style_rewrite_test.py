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


def test_rewrite_retries_then_accepts_polite():
    original = _script("원래 대사는 자연스러운 존댓말이에요.")
    outputs = [
        _script("첫 Rewrite는 반말로 끝난다."),
        _script("두 번째 Rewrite는 존댓말로 끝나요."),
    ]
    calls = {"count": 0}
    original_call = rewrite_engine._run_rewrite_call

    def fake_call(*args, **kwargs):
        del args, kwargs
        result = copy.deepcopy(outputs[calls["count"]])
        calls["count"] += 1
        return result

    rewrite_engine._run_rewrite_call = fake_call
    try:
        result = rewrite_engine.rewrite_script(original, _consensus())
    finally:
        rewrite_engine._run_rewrite_call = original_call

    _assert("informal Rewrite triggers one bounded retry", calls["count"] == 2)
    _assert(
        "second polite Rewrite is accepted",
        result["script_data"]["scenes"][0]["text"].endswith("끝나요."),
    )


def test_rewrite_falls_back_after_retry_limit():
    original = _script("원래 대사는 자연스러운 존댓말이에요.")
    calls = {"count": 0}
    original_call = rewrite_engine._run_rewrite_call

    def fake_call(*args, **kwargs):
        del args, kwargs
        calls["count"] += 1
        return _script("계속 반말로 끝난다.")

    rewrite_engine._run_rewrite_call = fake_call
    try:
        result = rewrite_engine.rewrite_script(original, _consensus())
    finally:
        rewrite_engine._run_rewrite_call = original_call

    _assert("Rewrite retry remains bounded at two attempts", calls["count"] == 2)
    _assert(
        "informal Rewrite never replaces the original narration",
        result["script_data"]["scenes"][0]["text"]
        == original["scenes"][0]["text"],
    )


def main():
    test_rewrite_retries_then_accepts_polite()
    test_rewrite_falls_back_after_retry_limit()
    print("✅ Rewrite speech-style regression suite passed")


if __name__ == "__main__":
    main()
