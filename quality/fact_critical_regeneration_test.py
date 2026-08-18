import os

import main as production
import quality.budget_guard as budget_guard


FACT_REASON = "복수의 독립 Fact Judge가 critical risk를 확인했습니다."


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


def _fact_critical(topic):
    return {
        "status": "HOLD",
        "failure_type": "FACT_CRITICAL",
        "script_data": _script(topic),
        "reason": FACT_REASON,
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


def _configure(sequence, quality_by_topic, runner_up=None, fallback_result=None):
    state = {
        "explorer_calls": 0,
        "rendered_topics": [],
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
    production.generate_script = lambda topic_info, candidate: _script(candidate["topic"])
    production.enrich_visual_plan = lambda scenes: scenes
    production.validate_visual_plan = lambda scenes: (True, "")
    production.run_quality_process = lambda script: quality_by_topic[script["topic"]]

    if fallback_result is None:
        production.try_runner_up_fallback = lambda *args, **kwargs: None
    else:
        production.try_runner_up_fallback = lambda *args, **kwargs: fallback_result

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


def test_fact_critical_regenerates_with_budget():
    production.MAX_TOPIC_REGENERATIONS = 1
    state = _configure(
        ["unsafe-fact-topic", "safe-topic"],
        {
            "unsafe-fact-topic": _fact_critical("unsafe-fact-topic"),
            "safe-topic": _pass("safe-topic"),
        },
    )

    production.main()

    _assert(
        "FACT_CRITICAL consumes one candidate attempt and explores again",
        state["explorer_calls"] == 2,
    )
    _assert(
        "FACT_CRITICAL candidate never reaches render",
        state["rendered_topics"] == ["safe-topic"],
    )


def test_fact_critical_holds_when_candidate_budget_exhausted():
    production.MAX_TOPIC_REGENERATIONS = 0
    state = _configure(
        ["unsafe-final-topic"],
        {
            "unsafe-final-topic": _fact_critical("unsafe-final-topic"),
        },
    )

    try:
        production.main()
    except RuntimeError as exc:
        _assert(
            "Final FACT_CRITICAL remains HOLD after attempt budget exhaustion",
            "Quality Gate HOLD" in str(exc),
        )
    else:
        raise AssertionError("FACT_CRITICAL unexpectedly passed after attempt exhaustion")

    _assert(
        "Exhausted FACT_CRITICAL candidate never reaches render",
        state["rendered_topics"] == [],
    )
    _assert(
        "Exhausted candidate budget does not loop",
        state["explorer_calls"] == 1,
    )


def test_fact_critical_holds_when_api_budget_exhausted():
    production.MAX_TOPIC_REGENERATIONS = 1
    state = _configure(
        ["unsafe-budget-topic"],
        {
            "unsafe-budget-topic": _fact_critical("unsafe-budget-topic"),
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
            _assert(
                "FACT_CRITICAL stays HOLD when API call budget is exhausted",
                "Quality Gate HOLD" in str(exc),
            )
        else:
            raise AssertionError("FACT_CRITICAL retried with exhausted API budget")
    finally:
        budget_guard.get_budget_status = original_status

    _assert(
        "API budget exhaustion prevents another Candidate Explorer attempt",
        state["explorer_calls"] == 1,
    )
    _assert(
        "API-budget-blocked FACT_CRITICAL never reaches render",
        state["rendered_topics"] == [],
    )


def test_runner_up_failure_regenerates_candidate():
    production.MAX_TOPIC_REGENERATIONS = 1
    fallback = {
        "status": "HOLD",
        "failure_type": "RUNNER_UP_FAILED",
        "fallback_used": True,
        "fallback_from_topic": "unsafe-winner",
        "fallback_to_topic": "unsafe-runner",
        "script_data": _script("unsafe-runner"),
        "reason": "Runner-up failed safety review",
    }
    state = _configure(
        ["unsafe-winner", "safe-after-runner"],
        {
            "unsafe-winner": _fact_critical("unsafe-winner"),
            "safe-after-runner": _pass("safe-after-runner"),
        },
        runner_up=_winner("unsafe-runner"),
        fallback_result=fallback,
    )

    production.main()

    _assert(
        "Failed runner-up after FACT_CRITICAL returns to Candidate Explorer",
        state["explorer_calls"] == 2,
    )
    _assert(
        "Neither FACT_CRITICAL winner nor failed runner-up reaches render",
        state["rendered_topics"] == ["safe-after-runner"],
    )


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

    _assert(
        "Existing novelty REGENERATE_TOPIC still explores next candidate",
        state["explorer_calls"] == 2,
    )
    _assert(
        "Low-novelty candidate never reaches render",
        state["rendered_topics"] == ["novel-topic"],
    )


def main():
    os.environ.pop("ENABLE_HOOK_EXPERIMENT", None)
    test_fact_critical_regenerates_with_budget()
    test_fact_critical_holds_when_candidate_budget_exhausted()
    test_fact_critical_holds_when_api_budget_exhausted()
    test_runner_up_failure_regenerates_candidate()
    test_novelty_regeneration_unchanged()
    print("✅ FACT_CRITICAL CANDIDATE REGENERATION TESTS PASS")


if __name__ == "__main__":
    main()
