"""Deterministic growth-aware shadow scoring for Candidate Explorer outputs.

The scorer is observational only: it never selects, rejects, reorders, or mutates
Candidate Explorer's authoritative production winner.
"""

from copy import deepcopy
import json
import os
import re

from analytics.feedback_contract import normalize_video_lineage

GROWTH_SHADOW_VERSION = 1
AXES = (
    "audience_continuity",
    "subscriber_potential",
    "series_potential",
    "visual_proof",
)
WEIGHTS = {
    "audience_continuity": 0.30,
    "subscriber_potential": 0.25,
    "series_potential": 0.20,
    "visual_proof": 0.25,
}

_PASSENGER_SIGNALS = {
    "객실", "승객", "창문", "좌석", "벨트", "조명", "산소", "화장실", "비상구",
    "착륙", "이륙", "기내", "날개", "엔진", "소리", "진동", "압력", "난기류",
}
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _clamp(value):
    return round(max(0.0, min(10.0, float(value))), 2)


def _candidate_text(candidate):
    parts = []
    for key in (
        "topic", "angle", "core_question", "specific_observation", "constraint",
        "counterintuitive_result", "tradeoff", "concrete_condition", "selection_reason",
    ):
        value = candidate.get(key)
        if value:
            parts.append(str(value))
    micro = candidate.get("micro_narrative") or {}
    if isinstance(micro, dict):
        parts.extend(str(v) for v in micro.values() if v)
    return " ".join(parts)


def _tokens(candidate):
    return set(_TOKEN_RE.findall(_candidate_text(candidate).lower()))


def _similarity(left, right):
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _recent_candidates(history):
    result = []
    for record in history or []:
        if not isinstance(record, dict):
            continue
        normalized = normalize_video_lineage(record)
        candidate = normalized.get("candidate")
        if isinstance(candidate, dict) and candidate:
            result.append((candidate, normalized))
    return result


def _observed_subscriber_gains(history):
    values = []
    for _, record in _recent_candidates(history):
        for window in ("72h", "24h"):
            snap = (record.get("performance") or {}).get(window) or {}
            gain = snap.get("subscriber_gain")
            if gain is not None:
                values.append(float(gain))
                break
    return values


def load_growth_history(path=None):
    """Load optional normalized lineage history; missing input is safely pending."""
    resolved = (path or os.environ.get("SHORTS_ANALYTICS_HISTORY_PATH", "")).strip()
    if not resolved:
        return []
    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        payload = payload.get("records", [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def score_growth_candidate(candidate, history=None):
    """Return a deterministic 0-10 shadow score with explicit evidence state."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a mapping")

    recent = _recent_candidates(history)
    text = _candidate_text(candidate)

    similarities = [_similarity(candidate, prior) for prior, _ in recent]
    strongest_similarity = max(similarities, default=0.0)
    related_count = sum(1 for value in similarities if 0.08 <= value < 0.42)

    passenger_hits = sum(1 for signal in _PASSENGER_SIGNALS if signal in text)
    continuity_base = 4.0 + min(3.0, passenger_hits * 0.55)
    if recent:
        continuity_base += min(2.0, related_count * 0.65)
    audience_continuity = _clamp(continuity_base)

    # Repetition is deliberately separate from continuity: same audience can be
    # good while near-duplicate questions should still be penalized.
    duplication_penalty = _clamp(max(0.0, (strongest_similarity - 0.28) * 18.0))

    visual_items = candidate.get("visual_proof") or []
    if not isinstance(visual_items, list):
        visual_items = [visual_items] if visual_items else []
    concrete_fields = sum(
        1 for key in (
            "specific_observation", "constraint", "counterintuitive_result",
            "tradeoff", "concrete_condition",
        ) if candidate.get(key)
    )
    visual_proof = _clamp(3.0 + min(4.5, len(visual_items) * 1.5) + min(2.5, concrete_fields * 0.6))

    question = str(candidate.get("core_question") or "")
    micro = candidate.get("micro_narrative") or {}
    reveal = str(micro.get("reveal") or "") if isinstance(micro, dict) else ""
    topic = str(candidate.get("topic") or "")
    series_base = 3.5
    if question:
        series_base += 1.4
    if topic:
        series_base += 1.0
    if passenger_hits:
        series_base += min(2.0, passenger_hits * 0.35)
    if concrete_fields:
        series_base += min(1.5, concrete_fields * 0.3)
    series_potential = _clamp(series_base)

    gains = _observed_subscriber_gains(history)
    structural_subscriber = 4.0
    if question and reveal:
        structural_subscriber += 1.0
    if passenger_hits:
        structural_subscriber += min(2.0, passenger_hits * 0.4)
    if series_potential >= 7.0:
        structural_subscriber += 1.0

    if gains:
        positive = sum(1 for gain in gains if gain > 0)
        zero = sum(1 for gain in gains if gain == 0)
        evidence_adjustment = min(2.0, positive * 0.45) - min(1.0, zero * 0.15)
        subscriber_evidence_state = "observed"
        subscriber_observations = len(gains)
    else:
        evidence_adjustment = 0.0
        subscriber_evidence_state = "pending"
        subscriber_observations = 0
    subscriber_potential = _clamp(structural_subscriber + evidence_adjustment)

    axes = {
        "audience_continuity": audience_continuity,
        "subscriber_potential": subscriber_potential,
        "series_potential": series_potential,
        "visual_proof": visual_proof,
    }
    weighted = sum(axes[name] * WEIGHTS[name] for name in AXES)
    total = _clamp(weighted - duplication_penalty * 0.20)

    evidence_state = "observed" if recent else "pending"
    return {
        "version": GROWTH_SHADOW_VERSION,
        "mode": "shadow",
        "evidence_state": evidence_state,
        "subscriber_evidence_state": subscriber_evidence_state,
        "subscriber_observations": subscriber_observations,
        "axes": axes,
        "duplication_penalty": duplication_penalty,
        "recent_history_count": len(recent),
        "total": total,
        "production_authoritative": True,
    }


def annotate_explorer_output(explorer_output, history=None):
    """Attach shadow evidence without changing authoritative winner/runner-up."""
    if not isinstance(explorer_output, dict):
        raise TypeError("explorer_output must be a mapping")
    annotated = deepcopy(explorer_output)
    shadow = {"version": GROWTH_SHADOW_VERSION, "mode": "shadow", "candidates": {}}
    for key in ("winner", "runner_up"):
        candidate = explorer_output.get(key)
        if isinstance(candidate, dict) and candidate:
            shadow["candidates"][key] = score_growth_candidate(candidate, history=history)
    annotated["growth_shadow"] = shadow
    return annotated
