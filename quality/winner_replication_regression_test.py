from analytics.feedback_contract import make_video_lineage
from content.growth_candidate_ranker import annotate_explorer_output
from content.winner_replication import (
    MIN_PROMOTION_SAMPLE,
    build_replication_specs,
    build_winner_learning,
    classify_history,
    creative_fingerprint,
    mature_snapshot,
)


def candidate(scope="aviation", question="비행기 창문에 작은 구멍이 있는 이유는 무엇인가요?", topic="비행기 창문 작은 구멍"):
    return {
        "candidate_scope": scope,
        "topic": topic,
        "core_question": question,
        "specific_observation": "승객이 실제로 볼 수 있는 구조입니다.",
    }


def lineage(
    ident,
    *,
    views=None,
    engaged=None,
    subscriber=None,
    state72="complete",
    state24="complete",
    scope="aviation",
    question="비행기 창문에 작은 구멍이 있는 이유는 무엇인가요?",
    topic="비행기 창문 작은 구멍",
    runtime="32-42s",
    hook_style="counterintuitive_statement",
    conversion="soft_series_cta",
):
    snap24 = {"state": state24}
    snap72 = {"state": state72}
    if state24 == "complete":
        snap24.update(views=views, engaged_views=engaged, subscriber_gain=subscriber)
    if state72 == "complete":
        snap72.update(views=views, engaged_views=engaged, subscriber_gain=subscriber)
    return make_video_lineage(
        ident,
        candidate=candidate(scope=scope, question=question, topic=topic),
        selected_hook={"style": hook_style, "text": "비행기 창문에는 일부러 구멍을 뚫어둡니다."},
        script={
            "runtime_bucket": runtime,
            "series_identity": "비행기에서 늘 보지만 이유는 몰랐던 설계와 원리" if scope == "aviation" else scope,
            "subscriber_conversion_mode": conversion,
        },
        snapshots={"24h": snap24, "72h": snap72},
    )


def comparator(ident, views, *, high=False):
    return lineage(
        ident,
        views=views,
        engaged=views,
        subscriber=0,
        scope="urban" if not high else "science",
        question="도시 배수구는 왜 이런 모양인가요?" if not high else "금속은 왜 열을 빠르게 전달하나요?",
        topic="도시 배수구" if not high else "금속 열전도",
        runtime="24-30s",
        hook_style="direct_statement",
        conversion="curiosity_bridge",
    )


def pattern_state(history, source):
    result = classify_history(history)
    key = creative_fingerprint(source)["key"]
    return result["patterns"][key]["state"], result["patterns"][key]


def test_pending_72h_blocks_24h_fallback():
    record = lineage("pending-72", views=5000, engaged=4000, subscriber=4, state72="pending")
    window, snap = mature_snapshot(record)
    assert window is None
    assert snap is None
    classified = classify_history([record])
    assert classified["records"][0]["state"] == "exploration"


def test_unavailable_72h_can_use_complete_24h():
    record = lineage("fallback-24", views=5000, engaged=4000, subscriber=2, state72="unavailable")
    window, snap = mature_snapshot(record)
    assert window == "24h"
    assert snap["engaged_views"] == 4000


def test_single_breakout_is_only_challenger():
    breakout = lineage("breakout", views=9000, engaged=8000, subscriber=12)
    history = [breakout, comparator("low-a", 100), comparator("low-b", 120), comparator("low-c", 140)]
    state, summary = pattern_state(history, breakout)
    assert state == "challenger"
    assert summary["strong_observations"] == 1
    assert summary["mature_observations"] == 1


def test_three_strong_comparable_observations_promote_winner():
    winners = [
        lineage("win-1", views=9000, engaged=8000, subscriber=0),
        lineage("win-2", views=8500, engaged=7600, subscriber=0),
        lineage("win-3", views=8200, engaged=7300, subscriber=0),
    ]
    history = winners + [comparator("base-1", 200), comparator("base-2", 300), comparator("base-3", 400)]
    state, summary = pattern_state(history, winners[0])
    assert MIN_PROMOTION_SAMPLE == 3
    assert state == "winner"
    assert summary["strong_observations"] >= 3


def test_positive_subscriber_sample_promotes_series_candidate():
    winners = [
        lineage("series-1", views=9000, engaged=8000, subscriber=5),
        lineage("series-2", views=8500, engaged=7600, subscriber=3),
        lineage("series-3", views=8200, engaged=7300, subscriber=2),
    ]
    history = winners + [comparator("base-s1", 200), comparator("base-s2", 300), comparator("base-s3", 400)]
    state, summary = pattern_state(history, winners[0])
    assert state == "series_candidate"
    assert summary["positive_subscriber_observations"] >= 3


def test_repeated_weak_pattern_can_retire_without_missing_as_zero():
    weak = [
        lineage("weak-1", views=80, engaged=60, subscriber=None),
        lineage("weak-2", views=90, engaged=70, subscriber=None),
        lineage("weak-3", views=100, engaged=80, subscriber=None),
    ]
    strong_comparators = [
        comparator("strong-1", 9000, high=True),
        comparator("strong-2", 8500, high=True),
        comparator("strong-3", 8000, high=True),
    ]
    state, summary = pattern_state(weak + strong_comparators, weak[0])
    assert state == "retired"
    assert summary["subscriber_observations"] == 0
    assert summary["weak_observations"] >= 3


def promoted_history():
    winners = [
        lineage("rep-1", views=9000, engaged=8000, subscriber=2),
        lineage("rep-2", views=8500, engaged=7600, subscriber=2),
        lineage("rep-3", views=8200, engaged=7300, subscriber=1),
    ]
    return winners + [comparator("r-base-1", 100), comparator("r-base-2", 200), comparator("r-base-3", 300)], winners


def test_promoted_pattern_emits_exactly_three_isolated_specs():
    history, winners = promoted_history()
    _, summary = pattern_state(history, winners[0])
    specs = build_replication_specs(summary)
    assert len(specs) == 3
    assert {spec["experiment"] for spec in specs} == {
        "same_question_structure_new_component",
        "same_hook_structure_new_situation",
        "same_topic_cluster_runtime_challenge",
    }
    for spec in specs:
        assert spec["authoritative_selection"] is False
        assert spec["fabricated_topic"] is False
        assert set(spec["supporting_lineage_ids"]) >= {"rep-1", "rep-2", "rep-3"}
        assert "constraint" in spec

    learning = build_winner_learning(history)
    assert learning["production_authoritative"] is True
    assert len(learning["promoted_patterns"]) == 1
    assert len(learning["promoted_patterns"][0]["challenger_specs"]) == 3


def test_growth_shadow_attaches_learning_without_changing_winner():
    history, _ = promoted_history()
    winner = candidate()
    runner = candidate(topic="비행기 좌석 위 작은 표시", question="비행기 좌석 위 표시는 왜 있나요?")
    output = {"winner": winner, "runner_up": runner, "winner_reason": "authoritative existing ranker"}
    annotated = annotate_explorer_output(output, history=history)
    assert annotated["winner"] == winner
    assert annotated["runner_up"] == runner
    assert annotated["winner_reason"] == "authoritative existing ranker"
    learning = annotated["growth_shadow"]["winner_learning"]
    assert learning["mode"] == "bounded_shadow_learning"
    assert learning["production_authoritative"] is True
    assert len(learning["promoted_patterns"]) == 1


def main():
    test_pending_72h_blocks_24h_fallback()
    print("CASE A pending 72h blocks fallback: PASS")
    test_unavailable_72h_can_use_complete_24h()
    print("CASE B unavailable 72h uses 24h: PASS")
    test_single_breakout_is_only_challenger()
    print("CASE C single breakout bounded: PASS")
    test_three_strong_comparable_observations_promote_winner()
    print("CASE D repeated strong winner: PASS")
    test_positive_subscriber_sample_promotes_series_candidate()
    print("CASE E series candidate: PASS")
    test_repeated_weak_pattern_can_retire_without_missing_as_zero()
    print("CASE F repeated weak retired: PASS")
    test_promoted_pattern_emits_exactly_three_isolated_specs()
    print("CASE G three challenger specs: PASS")
    test_growth_shadow_attaches_learning_without_changing_winner()
    print("CASE H growth shadow attachment: PASS")
    print("WINNER REPLICATION REGRESSION: PASS")


if __name__ == "__main__":
    main()
