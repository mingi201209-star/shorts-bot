import os

from content import hook_experiment
from video import hook_visual


def assert_true(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def test_flag_defaults_off():
    old = os.environ.pop("ENABLE_HOOK_EXPERIMENT", None)
    try:
        assert_true(
            "Hook feature flag defaults OFF",
            not hook_experiment.hook_experiment_enabled(),
        )
    finally:
        if old is not None:
            os.environ["ENABLE_HOOK_EXPERIMENT"] = old


def test_hook_score_criteria():
    scores, total = hook_experiment._score_hook({
        key: 8 for key in hook_experiment.HOOK_CRITERIA
    })
    assert_true(
        "All six hook criteria preserved",
        set(scores) == set(hook_experiment.HOOK_CRITERIA),
    )
    assert_true(
        "Uniform hook score remains uniform",
        abs(total - 8.0) < 0.001,
    )
    assert_true(
        "Required hook criteria floors pass at eight",
        hook_experiment._criteria_pass(scores),
    )


def test_hook_shape_filter():
    concise = "남향 창문은 왜 더 따뜻할까요?"
    assert_true(
        "Valid 1-3 second hook shape accepted",
        hook_experiment._valid_hook_shape(
            concise,
            "sunlight house window",
        ),
    )
    assert_true(
        "Long hook rejected before TTS",
        not hook_experiment._valid_hook_shape(
            "대부분의 주택은 왜 남쪽을 향한 창문을 가질까요?",
            "sunlight house window",
        ),
    )
    assert_true(
        "Invisible-only visual keyword rejected",
        not hook_experiment._valid_hook_shape(
            concise,
            "house south facing direction",
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
        "keyword": "ancient roman road stone",
        "visual_goal": "로마 석조 도로를 즉시 알아볼 수 있는 클로즈업",
    }
    scores, total = hook_visual._score_candidate(candidate, scene)
    item = {
        "scores": scores,
        "total_score": total,
    }

    assert_true(
        "All six visual criteria preserved",
        set(scores) == set(hook_visual.HOOK_VISUAL_CRITERIA),
    )
    assert_true(
        "Semantic match rewards direct subject overlap",
        scores["semantic_match"] >= 7.0,
    )
    assert_true(
        "Portrait visual passes mobile clarity",
        scores["mobile_clarity"] >= 8.0,
    )
    assert_true(
        "Direct visual passes strict gate",
        hook_visual._passes_strict_gate(item),
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
    print("✅ HOOK EXPERIMENT SELF TEST PASS")


if __name__ == "__main__":
    main()
