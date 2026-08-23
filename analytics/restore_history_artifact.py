"""Restore the newest non-expired analytics-history artifact for scheduled ingestion."""

from io import BytesIO
import json
import os
import sys
from zipfile import ZipFile

import requests


def restore_latest_history(*, repository, token, destination, transport=requests):
    if not repository or not token:
        return {"restored": False, "reason": "missing_context"}
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repository}/actions/artifacts?per_page=100"
    response = transport.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    artifacts = [
        item for item in payload.get("artifacts", [])
        if str(item.get("name", "")).startswith("analytics-history-") and not item.get("expired", False)
    ]
    if not artifacts:
        return {"restored": False, "reason": "no_history_artifact"}
    artifacts.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    artifact = artifacts[0]
    archive_url = artifact.get("archive_download_url")
    if not archive_url:
        return {"restored": False, "reason": "artifact_without_download_url"}
    archive = transport.get(archive_url, headers=headers, timeout=60)
    archive.raise_for_status()
    with ZipFile(BytesIO(archive.content)) as zf:
        candidates = [name for name in zf.namelist() if name.endswith("performance_history.json")]
        if not candidates:
            return {"restored": False, "reason": "history_file_missing_in_artifact"}
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        with zf.open(candidates[0]) as src, open(destination, "wb") as dst:
            dst.write(src.read())
    return {"restored": True, "artifact_id": artifact.get("id"), "artifact_name": artifact.get("name")}


def main():
    result = restore_latest_history(
        repository=os.environ.get("GITHUB_REPOSITORY", ""),
        token=os.environ.get("GITHUB_TOKEN", ""),
        destination=os.environ.get("SHORTS_ANALYTICS_HISTORY_PATH", "analytics/performance_history.json"),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
