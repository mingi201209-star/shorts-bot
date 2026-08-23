from datetime import datetime, timedelta, timezone

from analytics.feedback_contract import make_video_lineage
from analytics.youtube_ingestion import collect_history, fetch_video_metrics, refresh_access_token


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"http-{self.status}")

    def json(self):
        return self.payload


class FakeTransport:
    def __init__(self, *, fail_token=False, fail_reports=False, no_rows=False):
        self.fail_token = fail_token
        self.fail_reports = fail_reports
        self.no_rows = no_rows
        self.posts = []
        self.gets = []

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, data, timeout))
        if self.fail_token:
            return FakeResponse({"error": "invalid_grant"}, 400)
        return FakeResponse({"access_token": "safe-token"})

    def get(self, url, params=None, headers=None, timeout=None):
        self.gets.append((url, params, headers, timeout))
        if self.fail_reports:
            return FakeResponse({"error": "quota"}, 500)
        headers_payload = [
            {"name": "video"},
            {"name": "views"},
            {"name": "engagedViews"},
            {"name": "averageViewDuration"},
            {"name": "averageViewPercentage"},
            {"name": "likes"},
            {"name": "comments"},
            {"name": "shares"},
            {"name": "subscribersGained"},
        ]
        rows = [] if self.no_rows else [["vid-1", 5000, 3200, 27.5, 78.2, 81, 4, 12, 9]]
        return FakeResponse({"columnHeaders": headers_payload, "rows": rows})


def record(age_hours, *, state24="pending", state72="pending", subscribers=None):
    created = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)
    item = make_video_lineage(
        "lineage-1",
        youtube_video_id="vid-1",
        created_at=created.isoformat(),
    )
    item["performance"]["24h"]["state"] = state24
    item["performance"]["72h"]["state"] = state72
    if subscribers is not None:
        item["performance"]["24h"]["subscriber_gain"] = subscribers
    now = created + timedelta(hours=age_hours)
    return item, now


def test_oauth_refresh_never_requires_google_sdk():
    transport = FakeTransport()
    token = refresh_access_token("id", "secret", "refresh", transport=transport)
    assert token == "safe-token"
    assert transport.posts[0][1]["grant_type"] == "refresh_token"


def test_metric_mapping_preserves_supported_values_and_unknown_fields():
    transport = FakeTransport()
    published = datetime(2026, 8, 20, tzinfo=timezone.utc)
    metrics = fetch_video_metrics("vid-1", published, "token", transport=transport, now=published + timedelta(hours=25))
    assert metrics["views"] == 5000
    assert metrics["engaged_views"] == 3200
    assert metrics["average_view_duration_seconds"] == 27.5
    assert metrics["average_percentage_viewed"] == 78.2
    assert metrics["subscriber_gain"] == 9
    assert "stayed_to_watch" not in metrics
    assert transport.gets[0][2]["Authorization"] == "Bearer token"


def test_immature_windows_remain_pending_without_report_calls():
    item, now = record(23)
    transport = FakeTransport()
    updated, diag = collect_history([item], client_id="id", client_secret="secret", refresh_token="refresh", transport=transport, now=now)
    assert updated[0]["performance"]["24h"]["state"] == "pending"
    assert updated[0]["performance"]["72h"]["state"] == "pending"
    assert diag["snapshots_pending"] == 2
    assert len(transport.gets) == 0


def test_24h_mature_collects_once_and_72h_stays_pending():
    item, now = record(25)
    transport = FakeTransport()
    updated, diag = collect_history([item], client_id="id", client_secret="secret", refresh_token="refresh", transport=transport, now=now)
    perf = updated[0]["performance"]
    assert perf["24h"]["state"] == "complete"
    assert perf["24h"]["views"] == 5000
    assert perf["24h"]["subscriber_gain"] == 9
    assert perf["24h"]["stayed_to_watch"] is None
    assert perf["72h"]["state"] == "pending"
    assert diag["snapshots_collected"] == 1


def test_complete_snapshot_is_never_overwritten():
    item, now = record(80, state24="complete")
    item["performance"]["24h"]["views"] = 123
    transport = FakeTransport()
    updated, diag = collect_history([item], client_id="id", client_secret="secret", refresh_token="refresh", transport=transport, now=now)
    assert updated[0]["performance"]["24h"]["views"] == 123
    assert updated[0]["performance"]["72h"]["state"] == "complete"
    assert diag["snapshots_collected"] == 1
    assert len(transport.gets) == 1


def test_oauth_failure_leaves_history_untouched():
    item, now = record(80)
    transport = FakeTransport(fail_token=True)
    updated, diag = collect_history([item], client_id="id", client_secret="secret", refresh_token="refresh", transport=transport, now=now)
    assert updated[0]["performance"] == item["performance"]
    assert diag["errors"][0]["stage"] == "oauth"


def test_report_failure_and_no_rows_do_not_become_zero():
    item, now = record(25)
    failed, diag = collect_history([item], client_id="id", client_secret="secret", refresh_token="refresh", transport=FakeTransport(fail_reports=True), now=now)
    assert failed[0]["performance"]["24h"]["state"] == "pending"
    assert failed[0]["performance"]["24h"]["views"] is None
    assert diag["errors"][0]["stage"] == "analytics"

    empty, diag2 = collect_history([item], client_id="id", client_secret="secret", refresh_token="refresh", transport=FakeTransport(no_rows=True), now=now)
    assert empty[0]["performance"]["24h"]["state"] == "pending"
    assert empty[0]["performance"]["24h"]["views"] is None
    assert diag2["errors"][0]["error"] == "no_rows"


def main():
    test_oauth_refresh_never_requires_google_sdk()
    print("CASE A OAuth refresh: PASS")
    test_metric_mapping_preserves_supported_values_and_unknown_fields()
    print("CASE B metric mapping: PASS")
    test_immature_windows_remain_pending_without_report_calls()
    print("CASE C maturity gate: PASS")
    test_24h_mature_collects_once_and_72h_stays_pending()
    print("CASE D 24h collection: PASS")
    test_complete_snapshot_is_never_overwritten()
    print("CASE E idempotent complete snapshot: PASS")
    test_oauth_failure_leaves_history_untouched()
    print("CASE F OAuth safe failure: PASS")
    test_report_failure_and_no_rows_do_not_become_zero()
    print("CASE G analytics safe failure: PASS")
    print("YOUTUBE ANALYTICS INGESTION REGRESSION: PASS")


if __name__ == "__main__":
    main()
