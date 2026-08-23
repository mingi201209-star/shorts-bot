"""Read-only YouTube Analytics ingestion for delayed Shorts performance.

The collector only enriches lineage evidence. It never uploads, edits YouTube
content, or changes Candidate Explorer's authoritative selection.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import os

import requests

from analytics.feedback_contract import make_performance_snapshot, normalize_video_lineage

TOKEN_URL = "https://oauth2.googleapis.com/token"
REPORTS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
WINDOW_HOURS = {"24h": 24, "72h": 72}
REPORT_METRICS = (
    "views",
    "engagedViews",
    "averageViewDuration",
    "averageViewPercentage",
    "likes",
    "comments",
    "shares",
    "subscribersGained",
)
METRIC_MAP = {
    "views": "views",
    "engagedViews": "engaged_views",
    "averageViewDuration": "average_view_duration_seconds",
    "averageViewPercentage": "average_percentage_viewed",
    "likes": "likes",
    "comments": "comments",
    "shares": "shares",
    "subscribersGained": "subscriber_gain",
}


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_time(value):
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _publication_time(record):
    publication = record.get("publication") or {}
    production = record.get("production") or {}
    for value in (
        publication.get("published_at"),
        production.get("published_at"),
        record.get("created_at"),
    ):
        parsed = _parse_time(value)
        if parsed is not None:
            return parsed
    return None


def _is_mature(record, window, now):
    published_at = _publication_time(record)
    if published_at is None:
        return False
    return (now - published_at).total_seconds() >= WINDOW_HOURS[window] * 3600


def refresh_access_token(client_id, client_secret, refresh_token, *, transport=requests, timeout=20):
    response = transport.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("OAuth refresh response did not include access_token")
    return token


def fetch_video_metrics(video_id, published_at, access_token, *, transport=requests, now=None, timeout=20):
    """Fetch cumulative metrics through the collection date for one video."""
    now = now or _utc_now()
    response = transport.get(
        REPORTS_URL,
        params={
            "ids": "channel==MINE",
            "startDate": published_at.date().isoformat(),
            "endDate": now.date().isoformat(),
            "metrics": ",".join(REPORT_METRICS),
            "dimensions": "video",
            "filters": f"video=={video_id}",
        },
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    columns = [item.get("name") for item in payload.get("columnHeaders", [])]
    rows = payload.get("rows") or []
    if not rows:
        return None

    values = dict(zip(columns, rows[0]))
    result = {}
    for api_name, contract_name in METRIC_MAP.items():
        value = values.get(api_name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[contract_name] = value
        else:
            result[contract_name] = None
    return result


def collect_history(history, *, client_id, client_secret, refresh_token, transport=requests, now=None):
    """Return enriched history and diagnostics without mutating the input list."""
    now = now or _utc_now()
    records = [normalize_video_lineage(item) for item in history if isinstance(item, dict)]
    diagnostics = {
        "records_seen": len(records),
        "snapshots_collected": 0,
        "snapshots_pending": 0,
        "records_skipped": 0,
        "errors": [],
    }

    try:
        access_token = refresh_access_token(
            client_id, client_secret, refresh_token, transport=transport
        )
    except Exception as exc:
        diagnostics["errors"].append({"stage": "oauth", "error": type(exc).__name__})
        return deepcopy(records), diagnostics

    output = []
    for record in records:
        updated = deepcopy(record)
        publication = updated.get("publication") or {}
        video_id = publication.get("video_id")
        published_at = _publication_time(updated)
        if not video_id or published_at is None:
            diagnostics["records_skipped"] += 1
            output.append(updated)
            continue

        for window in ("24h", "72h"):
            current = (updated.get("performance") or {}).get(window) or {}
            if current.get("state") == "complete":
                continue
            if not _is_mature(updated, window, now):
                diagnostics["snapshots_pending"] += 1
                continue

            try:
                metrics = fetch_video_metrics(
                    str(video_id), published_at, access_token, transport=transport, now=now
                )
            except Exception as exc:
                diagnostics["errors"].append(
                    {
                        "stage": "analytics",
                        "lineage_id": updated.get("lineage_id"),
                        "window": window,
                        "error": type(exc).__name__,
                    }
                )
                continue

            if metrics is None:
                # No row is not proof of zero performance. Keep the existing state.
                diagnostics["errors"].append(
                    {
                        "stage": "analytics",
                        "lineage_id": updated.get("lineage_id"),
                        "window": window,
                        "error": "no_rows",
                    }
                )
                continue

            updated["performance"][window] = make_performance_snapshot(
                "complete",
                collected_at=now.isoformat(),
                **metrics,
            )
            diagnostics["snapshots_collected"] += 1
        output.append(updated)

    return output, diagnostics


def load_history(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        records = payload.get("records", [])
    else:
        records = payload
    if not isinstance(records, list):
        raise ValueError("analytics history must be a list or {'records': [...]} object")
    return records


def save_history(path, records):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump({"records": records}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp_path, path)
