"""Bounded winner-learning and replication planning from analytics lineage.

The module consumes normalized historical evidence and emits experiment metadata.
It never changes Candidate Explorer's authoritative winner and never invents a
specific factual follow-up topic.
"""

from collections import defaultdict
from copy import deepcopy
import re

from analytics.feedback_contract import normalize_video_lineage

WINNER_REPLICATION_VERSION = 1
MIN_PROMOTION_SAMPLE = 3
STRONG_RELATIVE_SCORE = 0.55
WEAK_RELATIVE_SCORE = 0.45
STATES = frozenset({"exploration", "challenger", "winner", "series_candidate", "retired"})


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _question_structure(candidate):
    question = _clean((candidate or {}).get("core_question"))
    topic = _clean((candidate or {}).get("topic"))
    text = f"{question} {topic}"
    if any(token in text for token in ("왜", "이유", "why")):
        return "why_reason"
    if any(token in text for token in ("어떻게", "원리", "작동", "how", "mechanism")):
        return "how_mechanism"
    if any(token in text for token in ("무엇", "뭐", "what")):
        return "what_identity"
    return "observed_phenomenon" if text else "unknown"


def _hook_structure(selected_hook):
    if not isinstance(selected_hook, dict):
        return "unknown"
    explicit = selected_hook.get("style") or selected_hook.get("type") or selected_hook.get("hook_type")
    if explicit:
        return _clean(explicit)
    text = _clean(selected_hook.get("text"))
    if not text:
        return "unknown"
    if "?" in text or text.endswith("까요"):
        return "question"
    if any(token in text for token in ("사실", "실제로", "일부러", "반대로")):
        return "counterintuitive_statement"
    return "direct_statement"


def creative_fingerprint(record):
    """Build a stable comparable-pattern fingerprint from available metadata."""
    normalized = normalize_video_lineage(record)
    candidate = normalized.get("candidate") or {}
    script = normalized.get("script") or {}
    hook = normalized.get("selected_hook") or {}

    scope = candidate.get("candidate_scope") or candidate.get("scope") or candidate.get("category") or "unknown"
    series_identity = (
        script.get("series_identity")
        or candidate.get("series_identity")
        or candidate.get("candidate_scope")
        or candidate.get("scope")
        or "unknown"
    )
    runtime_bucket = script.get("runtime_bucket") or "unknown"
    conversion_mode = script.get("subscriber_conversion_mode") or "unknown"

    parts = {
        "scope": _clean(scope) or "unknown",
        "series_identity": _clean(series_identity) or "unknown",
        "question_structure": _question_structure(candidate),
        "hook_structure": _hook_structure(hook),
        "runtime_bucket": _clean(runtime_bucket) or "unknown",
        "subscriber_conversion_mode": _clean(conversion_mode) or "unknown",
    }
    key = "|".join(f"{name}={parts[name]}" for name in sorted(parts))
    return {"key": key, "parts": parts}


def mature_snapshot(record):
    """Return the safest mature snapshot, never treating pending 72h as fallback."""
    normalized = normalize_video_lineage(record)
    performance = normalized.get("performance") or {}
    snap72 = performance.get("72h") or {}
    snap24 = performance.get("24h") or {}

    if snap72.get("state") == "complete":
        return "72h", deepcopy(snap72)
    if snap72.get("state") == "unavailable" and snap24.get("state") == "complete":
        return "24h", deepcopy(snap24)
    return None, None


def _primary_metric(snapshot):
    if not isinstance(snapshot, dict):
        return None
    for key in ("engaged_views", "views"):
        value = snapshot.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _percentile_rank(value, population):
    if value is None or not population:
        return None
    less = sum(1 for item in population if item < value)
    equal = sum(1 for item in population if item == value)
    return (less + 0.5 * equal) / len(population)


def _quality_adjustment(snapshot):
    """Small bounded tie-breaker; missing retention evidence remains neutral."""
    if not isinstance(snapshot, dict):
        return 0.0
    adjustment = 0.0
    stayed = snapshot.get("stayed_to_watch")
    avg_pct = snapshot.get("average_percentage_viewed")
    if isinstance(stayed, (int, float)) and not isinstance(stayed, bool):
        stayed = float(stayed)
        if stayed > 1.0:
            stayed /= 100.0
        adjustment += max(-0.08, min(0.08, (stayed - 0.5) * 0.16))
    if isinstance(avg_pct, (int, float)) and not isinstance(avg_pct, bool):
        avg_pct = float(avg_pct)
        if avg_pct > 1.0:
            avg_pct /= 100.0
        adjustment += max(-0.08, min(0.08, (avg_pct - 0.6) * 0.16))
    return adjustment


def _evidence_rows(history):
    rows = []
    for raw in history or []:
        if not isinstance(raw, dict):
            continue
        record = normalize_video_lineage(raw)
        window, snapshot = mature_snapshot(record)
        metric = _primary_metric(snapshot)
        rows.append({
            "record": record,
            "lineage_id": str(record.get("lineage_id") or ""),
            "fingerprint": creative_fingerprint(record),
            "window": window,
            "snapshot": snapshot,
            "metric": metric,
        })
    population = [row["metric"] for row in rows if row["metric"] is not None]
    for row in rows:
        percentile = _percentile_rank(row["metric"], population)
        if percentile is None:
            row["performance_score"] = None
        else:
            row["performance_score"] = max(0.0, min(1.0, percentile + _quality_adjustment(row["snapshot"])))
    return rows


def _group_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["fingerprint"]["key"]].append(row)

    summaries = {}
    for key, group in grouped.items():
        mature = [row for row in group if row["window"] and row["performance_score"] is not None]
        strong = [row for row in mature if row["performance_score"] >= STRONG_RELATIVE_SCORE]
        weak = [row for row in mature if row["performance_score"] <= WEAK_RELATIVE_SCORE]
        subscriber_known = [
            row for row in mature
            if isinstance((row["snapshot"] or {}).get("subscriber_gain"), (int, float))
            and not isinstance((row["snapshot"] or {}).get("subscriber_gain"), bool)
        ]
        positive_subscriber = [row for row in subscriber_known if row["snapshot"].get("subscriber_gain", 0) > 0]

        if len(mature) >= MIN_PROMOTION_SAMPLE and len(weak) >= MIN_PROMOTION_SAMPLE and len(strong) == 0:
            state = "retired"
        elif len(strong) >= MIN_PROMOTION_SAMPLE:
            qualifying = sorted(strong, key=lambda row: (row["performance_score"], row["metric"] or 0), reverse=True)[:MIN_PROMOTION_SAMPLE]
            if all(
                isinstance((row["snapshot"] or {}).get("subscriber_gain"), (int, float))
                and not isinstance((row["snapshot"] or {}).get("subscriber_gain"), bool)
                and row["snapshot"].get("subscriber_gain") > 0
                for row in qualifying
            ):
                state = "series_candidate"
            else:
                state = "winner"
        elif strong:
            state = "challenger"
        else:
            state = "exploration"

        summaries[key] = {
            "state": state,
            "mature_observations": len(mature),
            "strong_observations": len(strong),
            "weak_observations": len(weak),
            "subscriber_observations": len(subscriber_known),
            "positive_subscriber_observations": len(positive_subscriber),
            "supporting_lineage_ids": [row["lineage_id"] for row in mature if row["lineage_id"]],
            "fingerprint": deepcopy(group[0]["fingerprint"]),
        }
    return summaries


def classify_history(history):
    """Classify each lineage and summarize comparable creative patterns."""
    rows = _evidence_rows(history)
    summaries = _group_summary(rows)
    records = []
    for row in rows:
        group = summaries[row["fingerprint"]["key"]]
        if row["window"] is None or row["performance_score"] is None:
            state = "exploration"
        elif group["state"] in ("winner", "series_candidate", "retired"):
            state = group["state"]
        elif row["performance_score"] >= STRONG_RELATIVE_SCORE:
            state = "challenger"
        else:
            state = "exploration"
        records.append({
            "lineage_id": row["lineage_id"],
            "state": state,
            "evidence_window": row["window"],
            "performance_score": None if row["performance_score"] is None else round(row["performance_score"], 4),
            "fingerprint_key": row["fingerprint"]["key"],
        })
    return {
        "version": WINNER_REPLICATION_VERSION,
        "minimum_promotion_sample": MIN_PROMOTION_SAMPLE,
        "relative_score_bands": {"strong_min": STRONG_RELATIVE_SCORE, "weak_max": WEAK_RELATIVE_SCORE},
        "records": records,
        "patterns": summaries,
    }


def _runtime_challenge(current):
    buckets = ("24-30s", "32-42s", "45-55s")
    current = _clean(current)
    if current in buckets:
        index = buckets.index(current)
        return buckets[(index + 1) % len(buckets)]
    return "adjacent_runtime_bucket"


def build_replication_specs(pattern_summary):
    """Emit exactly three isolated challenger specs for a promoted pattern."""
    if not isinstance(pattern_summary, dict):
        raise TypeError("pattern_summary must be a mapping")
    if pattern_summary.get("state") not in ("winner", "series_candidate"):
        return []

    fingerprint = deepcopy((pattern_summary.get("fingerprint") or {}).get("parts") or {})
    provenance = list(pattern_summary.get("supporting_lineage_ids") or [])
    base = {
        "source_state": pattern_summary.get("state"),
        "source_fingerprint": fingerprint,
        "supporting_lineage_ids": provenance,
        "authoritative_selection": False,
        "fabricated_topic": False,
        "experiment_status": "challenger",
    }
    return [
        {
            **deepcopy(base),
            "experiment": "same_question_structure_new_component",
            "preserve": ["question_structure", "series_identity"],
            "change": ["concrete_subject_or_component"],
            "constraint": "Use a different concrete subject/component and re-run normal fact/media gates; do not copy the source topic verbatim.",
        },
        {
            **deepcopy(base),
            "experiment": "same_hook_structure_new_situation",
            "preserve": ["hook_structure", "series_identity"],
            "change": ["situation_or_context"],
            "constraint": "Use a different grounded situation/context while preserving only the hook form; normal Candidate gates remain authoritative.",
        },
        {
            **deepcopy(base),
            "experiment": "same_topic_cluster_runtime_challenge",
            "preserve": ["scope", "series_identity"],
            "change": ["runtime_bucket"],
            "target_runtime_bucket": _runtime_challenge(fingerprint.get("runtime_bucket")),
            "constraint": "Keep the topic/series cluster but challenge runtime only when the selected question complexity supports the target bucket.",
        },
    ]


def build_winner_learning(history):
    """Return bounded learning metadata beside growth shadow scoring."""
    classified = classify_history(history)
    promoted = []
    retired = []
    for key, summary in sorted(classified["patterns"].items()):
        if summary["state"] in ("winner", "series_candidate"):
            promoted.append({
                "fingerprint_key": key,
                "state": summary["state"],
                "supporting_lineage_ids": list(summary["supporting_lineage_ids"]),
                "challenger_specs": build_replication_specs(summary),
            })
        elif summary["state"] == "retired":
            retired.append({
                "fingerprint_key": key,
                "state": "retired",
                "supporting_lineage_ids": list(summary["supporting_lineage_ids"]),
            })
    return {
        "version": WINNER_REPLICATION_VERSION,
        "mode": "bounded_shadow_learning",
        "production_authoritative": True,
        "minimum_promotion_sample": MIN_PROMOTION_SAMPLE,
        "promoted_patterns": promoted,
        "retired_patterns": retired,
        "record_states": classified["records"],
    }
