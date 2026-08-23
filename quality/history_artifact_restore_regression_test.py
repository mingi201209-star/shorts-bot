import json
import os
import tempfile
from io import BytesIO
from zipfile import ZipFile

from analytics.restore_history_artifact import restore_latest_history


class FakeResponse:
    def __init__(self, *, payload=None, content=b""):
        self._payload = payload
        self.content = content
    def raise_for_status(self):
        return None
    def json(self):
        return self._payload


class FakeTransport:
    def __init__(self, archive):
        self.archive = archive
    def get(self, url, **kwargs):
        if url.endswith("actions/artifacts?per_page=100"):
            return FakeResponse(payload={"artifacts": [
                {"id": 1, "name": "other", "expired": False, "created_at": "2026-08-23T00:00:00Z", "archive_download_url": "x"},
                {"id": 2, "name": "analytics-history-2", "expired": False, "created_at": "2026-08-23T02:00:00Z", "archive_download_url": "https://archive/2"},
                {"id": 3, "name": "analytics-history-old", "expired": True, "created_at": "2026-08-23T03:00:00Z", "archive_download_url": "https://archive/3"},
            ]})
        if url == "https://archive/2":
            return FakeResponse(content=self.archive)
        raise AssertionError(url)


def main():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        zf.writestr("analytics/performance_history.json", json.dumps({"records": [{"lineage_id": "x"}]}))
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "analytics", "performance_history.json")
        result = restore_latest_history(
            repository="owner/repo", token="token", destination=dest,
            transport=FakeTransport(buffer.getvalue()),
        )
        assert result["restored"] is True
        assert result["artifact_id"] == 2
        with open(dest, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["records"][0]["lineage_id"] == "x"
    print("HISTORY ARTIFACT RESTORE REGRESSION: PASS")


if __name__ == "__main__":
    main()
