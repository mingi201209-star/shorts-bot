import os

from content import hook_experiment
from video import hook_visual


def assert_true(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def test_flag_defaults_off():
    old = os.environ.pop(
        "ENABLE_HOOK_EXPERIMENT",
        None,
    )

    try:
        assert_true(
            "Hook feature flag defaults OFF",
            not hook_experiment
            .hook_experiment_enabled(),
        )
    finally:
        if old is not None:
            os.environ[
                "ENABLE_HOOK_EXPERIMENT"
            ] = old


def test_hook_score_criteria():
    scores, total = (
        hook_experiment._score_hook({
            key: 8
            for key in (
                hook_experiment
                .HOOK_CRITERIA
            )
        })
    )

    assert_true(
        "All six hook criteria preserved",
        set(scores)
        == set(
            hook_experiment
            .HOOK_CRITERIA
        ),
    )

    assert_true(
        "Uniform hook score remains uniform",
        abs(total - 8.0) < 0.001,
    )


def test_hook_shape_filter():
    assert_true(
        "Valid concise hook shape accepted",
        hook_experiment._valid_hook_shape(
            "로마 도로는 왜 돌을 여러 겹 쌓았을까요?",
            "ancient roman stone road",
        ),
    )

    assert_true(
        "Generic one-word visual keyword rejected",
        not hook_experiment._valid_hook_shape(
            "로마 도로는 왜 돌을 여러 겹 쌓았을까요?",
            "technology",
        ),
    )


def test_hook_visual_scores():
    candidate = {
        "id": 1,
        "page_url": (
            "https://www.pexels.com/video/"
            "ancient-roman-road-stone-moving-1/"
        ),
        "width": 1080,
        "height": 1920,
        "duration": 8,
        "search_position": 1,
    }

    scene = {
        "keyword": (
            "ancient roman road stone"
        ),
        "visual_goal": (
            "로마 석조 도로를 모바일에서 "
            "즉시 알아볼 수 있는 클로즈업"
        ),
    }

    scores, total = (
        hook_visual._score_candidate(
            candidate,
            scene,
        )
    )

    assert_true(
        "All six visual criteria preserved",
        set(scores)
        == set(
            hook_visual
            .HOOK_VISUAL_CRITERIA
        ),
    )

    assert_true(
        "Semantic match rewards direct subject overlap",
        scores[
            "semantic_match"
        ] >= 8.0,
    )

    assert_true(
        "Portrait visual passes mobile clarity",
        scores[
            "mobile_clarity"
        ] >= 8.0,
    )

    assert_true(
        "Hook visual aggregate is bounded",
        0.0 <= total <= 10.0,
    )


def main():
    test_flag_defaults_off()
    test_hook_score_criteria()
    test_hook_shape_filter()
    test_hook_visual_scores()
    print(
        "✅ HOOK EXPERIMENT SELF TEST PASS"
    )


if __name__ == "__main__":
    main()
