import os
import tempfile

from analytics.youtube_upload import upload_enabled, upload_video, upsert_lineage


class FakeResponse:
    def __init__(self, payload=None, headers=None):
        self._payload = payload or {}
        self.headers = headers or {}
    def raise_for_status(self):
        return None
    def json(self):
        return self._payload


class FakeTransport:
    def __init__(self):
        self.posts = []
        self.puts = []
    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if "oauth2.googleapis.com" in url:
            return FakeResponse({"access_token": "test-token"})
        return FakeResponse({}, {"Location": "https://upload.example/session"})
    def put(self, url, **kwargs):
        self.puts.append((url, kwargs))
        return FakeResponse({"id": "video-123"})


def main():
    assert upload_enabled("1") is True
    assert upload_enabled("true") is False
    assert upload_enabled("") is False
    print("CASE A disabled by default: PASS")

    transport = FakeTransport()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
        handle.write(b"fake-video")
        path = handle.name
    try:
        result = upload_video(
            path,
            title="테스트",
            privacy_status="private",
            client_id="id",
            client_secret="secret",
            refresh_token="refresh",
            transport=transport,
        )
    finally:
        os.unlink(path)
    assert result["video_id"] == "video-123"
    assert result["privacy_status"] == "private"
    assert len(transport.puts) == 1
    print("CASE B resumable upload and id extraction: PASS")

    history = upsert_lineage(
        [], video_id="video-123", published_at="2026-08-23T00:00:00+00:00",
        production={"sha": "abc", "run_id": "99"}, topic="창문 구멍", scope="aviation"
    )
    assert len(history) == 1
    assert history[0]["publication"]["video_id"] == "video-123"
    assert history[0]["performance"]["24h"]["state"] == "pending"
    history2 = upsert_lineage(
        history, video_id="video-123", published_at="2026-08-23T00:00:00+00:00",
        production={"sha": "abc", "run_id": "99"}, topic="창문 구멍", scope="aviation"
    )
    assert len(history2) == 1
    print("CASE C lineage upsert idempotency: PASS")
    print("YOUTUBE UPLOAD LINEAGE REGRESSION: PASS")


if __name__ == "__main__":
    main()
