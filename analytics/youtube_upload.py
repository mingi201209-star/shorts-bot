"""Gated YouTube Data API upload and lineage helpers.

Real channel writes are disabled unless ENABLE_YOUTUBE_UPLOAD=1. The adapter
uses OAuth refresh-token credentials from environment/secrets and never logs
credentials or access tokens.
"""

from datetime import datetime, timezone
import json
import os

import requests

from analytics.feedback_contract import make_video_lineage, normalize_video_lineage
from analytics.youtube_ingestion import refresh_access_token

UPLOAD_INIT_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def upload_enabled(value=None):
    raw = os.environ.get("ENABLE_YOUTUBE_UPLOAD", "") if value is None else value
    return str(raw).strip() == "1"


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def upload_video(
    video_path,
    *,
    title,
    description="",
    privacy_status="private",
    client_id,
    client_secret,
    refresh_token,
    transport=requests,
    timeout=120,
):
    if privacy_status not in {"private", "unlisted", "public"}:
        raise ValueError("unsupported privacy_status")
    if not os.path.exists(video_path) or os.path.getsize(video_path) <= 0:
        raise FileNotFoundError(video_path)

    token = refresh_access_token(
        client_id,
        client_secret,
        refresh_token,
        transport=transport,
    )
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    init = transport.post(
        UPLOAD_INIT_URL,
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(os.path.getsize(video_path)),
        },
        data=json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
        timeout=30,
    )
    init.raise_for_status()
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise RuntimeError("YouTube resumable upload did not return Location")

    with open(video_path, "rb") as handle:
        done = transport.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(os.path.getsize(video_path)),
            },
            data=handle,
            timeout=timeout,
        )
    done.raise_for_status()
    payload = done.json()
    video_id = payload.get("id")
    if not video_id:
        raise RuntimeError("YouTube upload response did not include video id")
    return {
        "video_id": str(video_id),
        "published_at": _utc_now_iso(),
        "privacy_status": privacy_status,
    }


def upsert_lineage(history, *, video_id, published_at, production, topic=None, scope=None):
    records = [normalize_video_lineage(item) for item in history if isinstance(item, dict)]
    run_id = str((production or {}).get("run_id") or "unknown")
    lineage_id = f"youtube:{video_id}"
    candidate = {
        "topic": topic or None,
        "scope": scope or None,
    }
    candidate = {k: v for k, v in candidate.items() if v is not None}

    replacement = make_video_lineage(
        lineage_id,
        candidate=candidate or None,
        production=production or {},
        youtube_video_id=video_id,
        created_at=published_at,
    )
    replacement["publication"].update(
        {"provider": "youtube", "video_id": video_id, "published_at": published_at}
    )

    for index, record in enumerate(records):
        pub = record.get("publication") or {}
        if record.get("lineage_id") == lineage_id or pub.get("video_id") == video_id:
            existing = normalize_video_lineage(record)
            existing["candidate"] = existing.get("candidate") or replacement.get("candidate")
            existing["production"] = {**replacement.get("production", {}), **existing.get("production", {})}
            existing["publication"] = {**replacement["publication"], **existing.get("publication", {})}
            records[index] = existing
            return records

    records.append(replacement)
    return records
