"""Publish a rendered Short only when explicitly enabled and persist lineage."""

import json
import os
import sys

from analytics.youtube_ingestion import load_history, save_history
from analytics.youtube_upload import upload_enabled, upload_video, upsert_lineage


def main():
    if not upload_enabled():
        print("[youtube-upload] skipped: ENABLE_YOUTUBE_UPLOAD != 1")
        return 0

    required = {
        "client_id": os.environ.get("YOUTUBE_ANALYTICS_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("YOUTUBE_ANALYTICS_CLIENT_SECRET", "").strip(),
        "refresh_token": os.environ.get("YOUTUBE_ANALYTICS_REFRESH_TOKEN", "").strip(),
    }
    if not all(required.values()):
        print("[youtube-upload] failed safely: OAuth credentials unavailable")
        return 1

    video_path = os.environ.get("SHORTS_VIDEO_PATH", "final_shorts.mp4")
    title = os.environ.get("SHORTS_YOUTUBE_TITLE", "").strip() or "Shorts"
    description = os.environ.get("SHORTS_YOUTUBE_DESCRIPTION", "").strip()
    privacy = os.environ.get("SHORTS_YOUTUBE_PRIVACY", "private").strip() or "private"
    history_path = os.environ.get("SHORTS_ANALYTICS_HISTORY_PATH", "analytics/performance_history.json")

    try:
        result = upload_video(
            video_path,
            title=title,
            description=description,
            privacy_status=privacy,
            **required,
        )
        history = load_history(history_path) if os.path.exists(history_path) else []
        production = {
            "sha": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        }
        history = upsert_lineage(
            history,
            video_id=result["video_id"],
            published_at=result["published_at"],
            production=production,
            topic=os.environ.get("SHORTS_TOPIC") or None,
            scope=os.environ.get("SHORTS_CANDIDATE_SCOPE") or None,
        )
        save_history(history_path, history)
    except Exception as exc:
        print(f"[youtube-upload] failed safely: {type(exc).__name__}")
        return 1

    print(json.dumps({"uploaded": True, "video_id": result["video_id"], "privacy": result["privacy_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
