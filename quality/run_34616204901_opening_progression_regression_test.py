from content.script_engine_v2_validation import _opening_repeat_issue


def test_reasked_opening_is_rejected():
    scenes = [
        {"text": "비행기 창문 모서리는 둥글게 되어 있습니다."},
        {"text": "비행기 창문 모서리는 왜 둥글게 되어 있을까요?"},
    ]
    issue = _opening_repeat_issue(scenes)
    assert issue and "opening progression" in issue.lower(), issue


def test_new_physical_clue_is_not_rejected():
    scenes = [
        {"text": "비행기 창문 모서리는 둥글게 되어 있습니다."},
        {"text": "비행 중에는 객실 안팎의 압력 차이가 동체에 반복해서 걸립니다."},
    ]
    assert _opening_repeat_issue(scenes) is None


def test_static_identity_question_does_not_false_positive_without_overlap():
    scenes = [
        {"text": "스포일러는 날개 윗면에 설치된 판입니다."},
        {"text": "그런데 비행기는 왜 착륙 뒤 속도를 줄여야 할까요?"},
    ]
    assert _opening_repeat_issue(scenes) is None


if __name__ == "__main__":
    test_reasked_opening_is_rejected()
    test_new_physical_clue_is_not_rejected()
    test_static_identity_question_does_not_false_positive_without_overlap()
    print("PASS: Run 34616204901 opening progression regression")
