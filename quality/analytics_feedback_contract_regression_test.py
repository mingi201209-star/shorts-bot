from analytics.feedback_contract import (
    make_performance_snapshot,
    make_video_lineage,
    normalize_video_lineage,
)


def test_zero_is_not_unknown():
    snapshot = make_performance_snapshot(
        "complete", views=0, engaged_views=0, subscriber_gain=0
    )
    assert snapshot["views"] == 0
    assert snapshot["engaged_views"] == 0
    assert snapshot["subscriber_gain"] == 0
    assert snapshot["likes"] is None


def test_24h_and_72h_are_independent():
    record = make_video_lineage(
        "prod-123",
        youtube_video_id="yt-123",
        snapshots={
            "24h": {
                "state": "complete",
                "views": 1200,
                "engaged_views": 700,
                "subscriber_gain": 3,
            }
        },
    )
    assert record["performance"]["24h"]["state"] == "complete"
    assert record["performance"]["72h"]["state"] == "pending"


def test_partial_and_unavailable_are_explicit():
    partial = make_performance_snapshot("partial", views=100)
    unavailable = make_performance_snapshot("unavailable")
    assert partial["views"] == 100
    assert partial["shares"] is None
    assert unavailable["views"] is None


def test_lineage_keeps_creative_production_and_cost_metadata():
    record = make_video_lineage(
        "candidate-7:run-99",
        candidate={"topic": "비행기 창문 작은 구멍"},
        selected_hook={"text": "비행기 창문에는 구멍이 있습니다."},
        script={"runtime_bucket": "24-30s", "scene_count": 8},
        production={"sha": "abc123", "run_id": 99},
        youtube_video_id="video-99",
        cost={"usd": 0.04, "api_calls": 12},
    )
    assert record["candidate"]["topic"] == "비행기 창문 작은 구멍"
    assert record["production"]["sha"] == "abc123"
    assert record["publication"]["video_id"] == "video-99"
    assert record["cost"] == {"usd": 0.04, "api_calls": 12}


def test_legacy_record_is_backward_compatible():
    legacy = {"lineage_id": "old-1", "production": {"run_id": 1}}
    normalized = normalize_video_lineage(legacy)
    assert normalized["lineage_id"] == "old-1"
    assert normalized["production"]["run_id"] == 1
    assert normalized["performance"]["24h"]["state"] == "pending"
    assert normalized["performance"]["72h"]["state"] == "pending"


def main():
    test_zero_is_not_unknown()
    print("CASE A zero vs unknown: PASS")
    test_24h_and_72h_are_independent()
    print("CASE B independent delayed snapshots: PASS")
    test_partial_and_unavailable_are_explicit()
    print("CASE C collection states: PASS")
    test_lineage_keeps_creative_production_and_cost_metadata()
    print("CASE D lineage metadata: PASS")
    test_legacy_record_is_backward_compatible()
    print("CASE E backward compatibility: PASS")
    print("ANALYTICS FEEDBACK CONTRACT REGRESSION: PASS")


if __name__ == "__main__":
    main()
