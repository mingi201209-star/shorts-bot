from quality.korean_speech_style import (
    validate_korean_speech_text,
    validate_scenes_speech_style,
)
from content import hook_experiment


def _assert(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def test_sentence_examples():
    pass_examples = [
        "개미는 태양을 이용해 방향을 찾습니다.",
        "이 구조에는 놀라운 이유가 있습니다.",
        "왜 이런 모양일까요?",
    ]
    fail_examples = [
        "개미는 태양을 이용해 방향을 찾아요.",
        "이 구조는 아주 강해요.",
        "개미는 태양으로 방향 잡는다!",
        "이 구조는 매우 강하다.",
        "태양의 위치를 이용한다.",
        "놀라운 비밀이 있다.",
        "왜 이런 모양일까?",
    ]

    for text in pass_examples:
        valid, reason = validate_korean_speech_text(text)
        _assert(f"formal example accepted: {text} / {reason}", valid)

    for text in fail_examples:
        valid, reason = validate_korean_speech_text(text)
        _assert(f"non-formal example rejected: {text} / {reason}", not valid)


def test_multi_sentence_and_multi_scene():
    valid, _ = validate_korean_speech_text(
        "개미는 태양으로 방향 잡는다! 하지만 마지막에는 둥지를 찾습니다."
    )
    _assert("earlier informal sentence cannot hide behind formal final sentence", not valid)

    valid, _ = validate_korean_speech_text(
        "개미는 태양으로 방향 잡는다!하지만 마지막에는 둥지를 찾습니다."
    )
    _assert("no-space sentence boundary cannot hide informal sentence", not valid)

    scenes = [
        {"text": "첫 장면은 자연스럽게 설명합니다."},
        {"text": "두 번째 장면은 해요체로 끝나요."},
        {"text": "세 번째 장면은 다시 격식체입니다."},
    ]
    valid, _ = validate_scenes_speech_style(scenes)
    _assert("one casual-polite scene fails final speech-style validation", not valid)


def test_nominal_hook_policy():
    valid, _ = validate_korean_speech_text(
        "벌집 육각형의 숨은 비밀",
        allow_nominal=True,
    )
    _assert("natural nominal Hook remains allowed", valid)

    valid, _ = validate_korean_speech_text(
        "개미는 태양으로 방향 잡는다!",
        allow_nominal=True,
    )
    _assert("informal finite Hook remains rejected", not valid)


def _hook_item(index, text, score):
    return {
        "id": f"hook_{index}",
        "text": text,
        "visual_goal": "태양 아래 이동하는 개미를 크게 보여주는 장면",
        "keyword": "ant sunlight walking closeup",
        "stop_power": score,
        "curiosity_gap": score,
        "clarity": score,
        "specificity": score,
        "visual_potential": score,
        "fact_safety": score,
        "reason": "test",
    }


def test_nonformal_hook_cannot_win():
    formal_question = "개미는 왜 태양으로 길을 찾을까요?"
    valid, reason = validate_korean_speech_text(formal_question)
    _assert(
        f"formal ~까요 question remains valid narration: {reason}",
        valid,
    )

    payload = {
        "candidates": [
            _hook_item(1, "개미는 태양으로 방향을 잡는다!", 10.0),
            _hook_item(2, "개미는 태양으로 길을 찾습니다", 9.2),
            _hook_item(3, "개미는 태양을 보고 움직입니다", 9.0),
            _hook_item(4, "개미는 태양으로 방향을 찾습니다", 8.8),
            _hook_item(5, "개미는 태양을 이용해 돌아옵니다", 8.6),
            _hook_item(6, "개미는 태양을 따라 길을 찾습니다", 8.4),
            _hook_item(7, formal_question, 9.8),
        ]
    }

    candidates, diagnostics = hook_experiment._diagnose_candidates(payload)
    texts = [item["text"] for item in candidates]
    _assert(
        "informal Hook is filtered before scoring",
        "개미는 태양으로 방향을 잡는다!" not in texts,
    )
    _assert(
        "formal question is reserved for Scene 2, not Hook",
        formal_question not in texts,
    )
    _assert(
        "question-shaped Hook rejection is observable",
        diagnostics.get("rejected", {}).get("question_hook_not_allowed", 0) == 1,
    )
    _assert("at least five formal declarative Hook candidates remain", len(candidates) >= 5)

    candidates.sort(key=lambda item: item["total_score"], reverse=True)
    winner = hook_experiment._best_passing_candidate(candidates)
    _assert(
        "formal declarative Hook wins",
        winner
        and winner["text"] != "개미는 태양으로 방향을 잡는다!"
        and winner["text"] != formal_question,
    )


def main():
    test_sentence_examples()
    test_multi_sentence_and_multi_scene()
    test_nominal_hook_policy()
    test_nonformal_hook_cannot_win()
    print("✅ Korean formal speech-style regression suite passed")


if __name__ == "__main__":
    main()
