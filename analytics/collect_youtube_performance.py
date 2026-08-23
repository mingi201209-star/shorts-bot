"""CLI entry point for read-only YouTube performance collection."""

import json
import os
import sys

from analytics.youtube_ingestion import collect_history, load_history, save_history


def _required_credentials():
    values = {
        "client_id": os.environ.get("YOUTUBE_ANALYTICS_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("YOUTUBE_ANALYTICS_CLIENT_SECRET", "").strip(),
        "refresh_token": os.environ.get("YOUTUBE_ANALYTICS_REFRESH_TOKEN", "").strip(),
    }
    return values if all(values.values()) else None


def main():
    path = os.environ.get("SHORTS_ANALYTICS_HISTORY_PATH", "").strip()
    if not path or not os.path.exists(path):
        print("[analytics] skipped: history path unavailable")
        return 0

    credentials = _required_credentials()
    if credentials is None:
        print("[analytics] skipped: OAuth credentials unavailable")
        return 0

    try:
        history = load_history(path)
        updated, diagnostics = collect_history(history, **credentials)
    except Exception as exc:
        print(f"[analytics] failed safely: {type(exc).__name__}")
        return 1

    if diagnostics.get("errors") and diagnostics.get("snapshots_collected", 0) == 0:
        print("[analytics] collection produced no new complete snapshots")
        print(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True))
        return 0

    save_history(path, updated)
    print(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
