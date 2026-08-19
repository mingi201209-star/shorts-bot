from video.hook_visual_dominance import (
    HOOK_ACTION_MATCH_MIN,
    HOOK_MAX_COMPETING_SUBJECT_RISK,
    HOOK_SUBJECT_DOMINANCE_MIN,
    normalize_dominance_result,
    passes_dominance_gate,
    requires_observable_action,
)


def make_result(
    *,
    dominance,
    action,
    competing,
    visible=True,
    action_required=True,
    target_is_person=False,
):
    return normalize_dominance_result(
        {
            "target_subject": "person" if target_is_person else "snake",
            "target_is_person": target_is_person,
            "subject_dominance": dominance,
            "action_match": action,
            "competing_subject_risk": competing,
            "vertical_crop_subject_visible": visible,
            "reason": "fixture",
        },
        action_required=action_required,
    )


def main():
    assert HOOK_SUBJECT_DOMINANCE_MIN == 8.0
    assert HOOK_ACTION_MATCH_MIN == 7.0
    assert HOOK_MAX_COMPETING_SUBJECT_RISK == 4.0

    rotating_snake = {
        "text": "바람개비처럼 회전하는 뱀을 보세요",
        "keyword": "rotating snake close up",
        "visual_goal": "회전하는 뱀이 화면 중심에 크게 보이는 장면",
    }
    assert requires_observable_action(rotating_snake) is True

    # A. Snake close-up + clearly visible rotation -> PASS.
    assert passes_dominance_gate(make_result(
        dominance=9.3,
        action=8.8,
        competing=1.0,
    ))

    # B. Large human + small snake -> FAIL on dominance/competition.
    assert not passes_dominance_gate(make_result(
        dominance=4.5,
        action=7.8,
        competing=9.0,
    ))

    # C. Large snake but no visible rotation -> FAIL on action match.
    assert not passes_dominance_gate(make_result(
        dominance=9.2,
        action=3.0,
        competing=1.0,
    ))

    # D. When the Hook target is a person, that person is not a competing subject.
    person_hook = {
        "text": "사람은 왜 하품할까요?",
        "keyword": "person yawning face close up",
        "visual_goal": "하품하는 사람 얼굴 클로즈업",
    }
    assert requires_observable_action(person_hook) is True
    assert passes_dominance_gate(make_result(
        dominance=9.4,
        action=8.7,
        competing=0.5,
        action_required=True,
        target_is_person=True,
    ))

    # E. Subject becomes small/cropped after 9:16 production crop -> FAIL.
    assert not passes_dominance_gate(make_result(
        dominance=8.9,
        action=8.0,
        competing=1.5,
        visible=False,
    ))

    print("✅ Hook visual subject-dominance regression PASS")


if __name__ == "__main__":
    main()
