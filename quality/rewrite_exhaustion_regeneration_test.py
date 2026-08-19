import os

import main as production
import quality.budget_guard as budget_guard


REWRITE_REASON = "Rewrite 최대 횟수 초과"


def _winner(topic):
    return {
        "topic": topic,
        "core_question": f"{topic} question",
    }


def _script(topic):
    return {
        "title": topic,
        "topic": topic,
        "scenes": [
            {
                "text": "테스트 장면입니다.",
                "keyword": "safe visible subject",
                "visual_goal": "테스트 피사체",
                "topic_marker": topic,
            }
        ],
    }


def _rewrite_exhausted(topic):
    return {
        "status": "HOLD",
        "script_data": _script(topic),
        "reason": REWRITE_REASON,
    }


def _pass(topic):
    return {
        "status": "PASS",
        "script_data": _script(topic),
        "reason": "safe",
    }


def _regenerate(topic):
    return {
        "status": "REGENERATE_TOPIC",
        "script_data": _script(topic),
        "reason": "Novelty가 선택 Rewrite 후에도 최소 기준을 충족하지 못했습니다.",
    }


def _configure(sequence, quality_by_topic, *, runner_up=None, fallback_result=None):
    state = {
        "explorer_calls": 0,
        "fallback_calls": 0,
        "rendered_topics": [],
        "generated_topics": [],
    }

    production.validate_environment = lambda: None
    production.choose_topic_direction = lambda: {
        "category": "test",
        "direction": "test",
    }
    production.get_recent_topic_names = lambda: []

    def explore_candidates(*args, **kwargs):
        del args, kwargs
        index = state["explorer_calls"]
        state["explorer_calls"] += 1
        topic = sequence[index]
        return {
            "status": "SELECTED",
            "winner": _winner(topic),
            "runner_up": runner_up if index == 0 else None,
        }

    production.explore_candidates = explore_candidates
    production.evaluate_candidate = lambda *args, **kwargs: {
        "status": "PASS",
        "reason": "fixture candidate gate pass",
    }

    def generate_script(topic_info, candidate):
        del topic_info
        topic = candidate["topic"]
        state["generated_topics"].append(topic)
        return _script(topic)

    production.generate_script = generate_script
    production.enrich_visual_plan = lambda scenes: scenes
    production.validate_visual_plan = lambda scenes: (True, "")
    production.run_quality_process = lambda script: quality_by_topic[script["topic"]]

    def fallback(*args, **kwargs):
        del args, kwargs
        state["fallback_calls"] += 1
        return fallback_result

    if runner_up is None:
        production.try_runner_up_fallback = lambda *args, **kwargs: None
    else:
        production.try_runner_up_fallback = fallback

    def generate_scenes(scenes):
        state["rendered_topics"].append(scenes[0]["topic_marker"])
        return []

    production.generate_scenes = generate_scenes
    production.validate_total_duration = lambda clips: (True, 1.0)
    production.render_final_video = lambda clips: "test.mp4"
    production.send_result_summary = lambda *args, **kwargs: None
    production.send_telegram_video = lambda *args, **kwargs: None
    production.send_telegram_message = lambda *args, **kwargs: None
    production.print_budget_status = lambda: None

    return state


def _assert(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def test_rewrite_exhaustion_regenerates_without_runner_up():
    production.MAX_TOPIC_REGENERATIONS = 1
    state = _configure(
        ["exhausted-topic", "safe-topic"],
        {
            "exhausted-topic": _rewrite_exhausted("exhausted-topic"),
            "safe-topic": _pass("safe-topic"),
        },
    )

    production.main()

    _assert(
        "Rewrite exhaustion consumes one candidate attempt and explores again",
        state["explorer_calls"] == 2,
    )
    _assert(
        "Rewrite-exhausted candidate never reaches render",
        state["rendered_topics"] == ["safe-topic"],
    )


def test_rewrite_exhaustion_failed_runner_up_regenerates():
    production.MAX_TOPIC_REGENERATIONS = 1
    fallback = {
        "status": "HOLD",
        "failure_type": "RUNNER_UP_FAILED",
        "fallback_used": True,
        "fallback_from_topic": "exhausted-winner",
        "fallback_to_topic": "failed-runner",
        "script_data": _script("failed-runner"),
        "reason": "Runner-up failed quality review",
    }
    state = _configure(
        ["exhausted-winner", "safe-after-runner"],
        {
            "exhausted-winner": _rewrite_exhausted("exhausted-winner"),
            "safe-after-runner": _pass("safe-after-runner"),
        },
        runner_up=_winner("failed-runner"),
        fallback_result=fallback,
    )

    production.main()

    _assert("Rewrite exhaustion reviews Runner-up first", state["fallback_calls"] == 1)
    _assert(
        "Failed Runner-up returns to Candidate Explorer",
        state["explorer_calls"] == 2,
    )
    _assert(
        "Neither exhausted Winner nor failed Runner-up renders",
        state["rendered_topics"] == ["safe-after-runner"],
    )


def test_rewrite_exhaustion_runner_up_pass_is_preserved():
    production.MAX_TOPIC_REGENERATIONS = 1
    fallback = {
        "status": "PASS",
        "fallback_used": True,
        "fallback_from_topic": "exhausted-winner",
        "fallback_to_topic": "safe-runner",
        "script_data": _script("safe-runner"),
        "reason": "safe runner",
    }
    state = _configure(
        ["exhausted-winner"],
        {
            "exhausted-winner": _rewrite_exhausted("exhausted-winner"),
        },
        runner_up=_winner("safe-runner"),
        fallback_result=fallback,
    )

    production.main()

    _assert("Safe Runner-up is reviewed once", state["fallback_calls"] == 1)
    _assert("Safe Runner-up keeps existing PASS policy", state["rendered_topics"] == ["safe-runner"])
    _assert("No unnecessary Candidate regeneration after Runner-up PASS", state["explorer_calls"] == 1)


def test_rewrite_exhaustion_holds_when_candidate_budget_exhausted():
    production.MAX_TOPIC_REGENERATIONS = 0
    state = _configure(
        ["exhausted-final-topic"],
        {
            "exhausted-final-topic": _rewrite_exhausted("exhausted-final-topic"),
        },
    )

    try:
        production.main()
    except RuntimeError as exc:
        _assert("Attempt exhaustion preserves final HOLD", REWRITE_REASON in str(exc))
    else:
        raise AssertionError("Rewrite exhaustion unexpectedly passed after attempt exhaustion")

    _assert("Attempt exhaustion does not loop", state["explorer_calls"] == 1)
    _assert("Attempt-exhausted candidate never renders", state["rendered_topics"] == [])


def test_rewrite_exhaustion_holds_when_api_budget_exhausted():
    production.MAX_TOPIC_REGENERATIONS = 1
    state = _configure(
        ["exhausted-budget-topic"],
        {
            "exhausted-budget-topic": _rewrite_exhausted("exhausted-budget-topic"),
        },
    )

    original_status = budget_guard.get_budget_status
    budget_guard.get_budget_status = lambda: {
        "calls": 60,
        "max_calls": 60,
        "cost_usd": 0.01,
        "max_cost_usd": 0.05,
    }
    try:
        try:
            production.main()
        except RuntimeError as exc:
            _assert("API budget exhaustion preserves final HOLD", REWRITE_REASON in str(exc))
        else:
            raise AssertionError("Rewrite exhaustion retried with exhausted API budget")
    finally:
        budget_guard.get_budget_status = original_status

    _assert("API budget exhaustion prevents another candidate", state["explorer_calls"] == 1)
    _assert("API-budget-blocked candidate never renders", state["rendered_topics"] == [])


def test_novelty_regeneration_unchanged():
    production.MAX_TOPIC_REGENERATIONS = 1
    state = _configure(
        ["low-novelty-topic", "novel-topic"],
        {
            "low-novelty-topic": _regenerate("low-novelty-topic"),
            "novel-topic": _pass("novel-topic"),
        },
    )

    production.main()

    _assert("Novelty REGENERATE_TOPIC still explores next candidate", state["explorer_calls"] == 2)
    _assert("Novelty-failed candidate never renders", state["rendered_topics"] == ["novel-topic"])


def test_script_generation_failure_regeneration_unchanged():
    production.MAX_TOPIC_REGENERATIONS = 1
    state = _configure(
        ["script-failure-topic", "safe-script-topic"],
        {
            "safe-script-topic": _pass("safe-script-topic"),
        },
    )

    original_generator = production.generate_script

    def generate_script(topic_info, candidate):
        if candidate["topic"] == "script-failure-topic":
            raise RuntimeError(
                "Script Generator가 유효한 대본 생성에 실패했습니다. last_error=test"
            )
        return original_generator(topic_info, candidate)

    production.generate_script = generate_script
    production.main()

    _assert("Script generation failure still consumes one candidate attempt", state["explorer_calls"] == 2)
    _assert("Script-failed candidate never renders", state["rendered_topics"] == ["safe-script-topic"])


def main():
    os.environ.pop("ENABLE_HOOK_EXPERIMENT", None)
    test_rewrite_exhaustion_regenerates_without_runner_up()
    test_rewrite_exhaustion_failed_runner_up_regenerates()
    test_rewrite_exhaustion_runner_up_pass_is_preserved()
    test_rewrite_exhaustion_holds_when_candidate_budget_exhausted()
    test_rewrite_exhaustion_holds_when_api_budget_exhausted()
    test_novelty_regeneration_unchanged()
    test_script_generation_failure_regeneration_unchanged()
    print("✅ REWRITE EXHAUSTION CANDIDATE REGENERATION TESTS PASS")


if __name__ == "__main__":
    main()
