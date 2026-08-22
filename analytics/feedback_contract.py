"""Provider-agnostic contract linking a produced Short to delayed performance.

This module is intentionally observational. It stores evidence for later growth
ranking but never changes production or candidate-selection policy itself.
"""

from copy import deepcopy
from datetime import datetime, timezone

SCHEMA_VERSION = 1
COLLECTION_STATES = frozenset({"pending", "partial", "complete", "unavailable"})
SNAPSHOT_WINDOWS = ("24h", "72h")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _optional_number(value, field):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric or None")
    return value


def make_performance_snapshot(state="pending", *, collected_at=None, **metrics):
    """Build one delayed snapshot while preserving zero-vs-unknown semantics."""
    if state not in COLLECTION_STATES:
        raise ValueError(f"unsupported collection state: {state}")

    supported = {
        "views",
        "engaged_views",
        "stayed_to_watch",
        "average_view_duration_seconds",
        "average_percentage_viewed",
        "likes",
        "comments",
        "shares",
        "subscriber_gain",
    }
    unknown = set(metrics) - supported - {"retention"}
    if unknown:
        raise ValueError(f"unsupported performance metrics: {sorted(unknown)}")

    snapshot = {
        "state": state,
        "collected_at": collected_at,
        "views": None,
        "engaged_views": None,
        "stayed_to_watch": None,
        "average_view_duration_seconds": None,
        "average_percentage_viewed": None,
        "retention": {},
        "likes": None,
        "comments": None,
        "shares": None,
        "subscriber_gain": None,
    }
    for field in supported:
        if field in metrics:
            snapshot[field] = _optional_number(metrics[field], field)

    retention = metrics.get("retention") or {}
    if not isinstance(retention, dict):
        raise TypeError("retention must be a mapping")
    snapshot["retention"] = {
        str(checkpoint): _optional_number(value, f"retention.{checkpoint}")
        for checkpoint, value in retention.items()
    }
    return snapshot


def make_video_lineage(
    lineage_id,
    *,
    candidate=None,
    selected_hook=None,
    script=None,
    production=None,
    youtube_video_id=None,
    cost=None,
    snapshots=None,
    created_at=None,
):
    """Create a stable lineage record without requiring analytics to exist yet."""
    if not lineage_id:
        raise ValueError("lineage_id is required")

    record = {
        "schema_version": SCHEMA_VERSION,
        "lineage_id": str(lineage_id),
        "created_at": created_at or _utc_now(),
        "candidate": deepcopy(candidate) if candidate is not None else None,
        "selected_hook": deepcopy(selected_hook) if selected_hook is not None else None,
        "script": deepcopy(script) if script is not None else None,
        "production": deepcopy(production) if production is not None else {},
        "publication": {"provider": "youtube", "video_id": youtube_video_id},
        "cost": {
            "usd": None,
            "api_calls": None,
        },
        "performance": {
            window: make_performance_snapshot("pending") for window in SNAPSHOT_WINDOWS
        },
    }

    if cost:
        record["cost"]["usd"] = _optional_number(cost.get("usd"), "cost.usd")
        record["cost"]["api_calls"] = _optional_number(
            cost.get("api_calls"), "cost.api_calls"
        )

    for window, snapshot in (snapshots or {}).items():
        if window not in SNAPSHOT_WINDOWS:
            raise ValueError(f"unsupported snapshot window: {window}")
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a mapping")
        payload = dict(snapshot)
        state = payload.pop("state", "pending")
        collected_at = payload.pop("collected_at", None)
        record["performance"][window] = make_performance_snapshot(
            state, collected_at=collected_at, **payload
        )

    return record


def normalize_video_lineage(record):
    """Upgrade legacy/minimal records into the current additive contract."""
    if not isinstance(record, dict):
        raise TypeError("record must be a mapping")

    normalized = deepcopy(record)
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("candidate", None)
    normalized.setdefault("selected_hook", None)
    normalized.setdefault("script", None)
    normalized.setdefault("production", {})
    normalized.setdefault("publication", {"provider": "youtube", "video_id": None})
    normalized.setdefault("cost", {"usd": None, "api_calls": None})
    normalized.setdefault("performance", {})
    for window in SNAPSHOT_WINDOWS:
        normalized["performance"].setdefault(window, make_performance_snapshot("pending"))
    return normalized
