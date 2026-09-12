"""Grounding-aware Candidate Explorer supply context.

This module exposes the exact repo-owned trusted grounding capability already
used by host validation. It adds no model/network call and never grants trust;
it only tells aviation Candidate Explorer which canonical subject space the host
can currently verify. Host canonical grounding remains authoritative.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, Sequence

from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)


NO_GROUNDED_CANDIDATE_SUPPLY = "NO_GROUNDED_CANDIDATE_SUPPLY"
NO_GROUNDED_SEED_SUPPLY = "NO_GROUNDED_SEED_SUPPLY"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_topic(value: Any) -> str:
    text = _text(value).lower()
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return " ".join(text.split())


def _preferred_grounding_phrase(values: Any) -> str:
    """Prefer a Korean evidence-owned phrase, falling back to the first phrase."""

    phrases = [_text(item) for item in (values or []) if _text(item)]
    if not phrases:
        return ""
    for phrase in phrases:
        if re.search(r"[가-힣]", phrase):
            return phrase
    return phrases[0]


def all_trusted_candidate_records(
    *,
    production_records: Sequence[Dict[str, Any]] | None = None,
    pool_records: Sequence[Dict[str, Any]] | None = None,
) -> tuple[Dict[str, Any], ...]:
    """Return the same two trusted registries consumed by Candidate Pool Handoff."""

    production = (
        PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS
        if production_records is None
        else tuple(production_records)
    )
    pool = (
        CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
        if pool_records is None
        else tuple(pool_records)
    )
    return tuple(production) + tuple(pool)


def grounding_candidate_capabilities(
    *,
    production_records: Sequence[Dict[str, Any]] | None = None,
    pool_records: Sequence[Dict[str, Any]] | None = None,
) -> tuple[Dict[str, Any], ...]:
    """Project compact, evidence-owned generation capability from trusted records.

    The projection deliberately excludes model-authored aliases/evidence and does
    not create new subject identities. A capability exists only when the record
    itself is sufficiently complete to be useful to the existing host supplier.
    """

    capabilities = []
    seen = set()
    for record in all_trusted_candidate_records(
        production_records=production_records,
        pool_records=pool_records,
    ):
        if not isinstance(record, dict):
            continue
        if _text(record.get("record_type")).lower() != "trusted_subject_identity":
            continue
        canonical = _text(record.get("canonical_subject"))
        kind = _text(record.get("subject_kind"))
        source = _text(record.get("source"))
        detail = _text(record.get("detail"))
        features = [
            _text(item)
            for item in (record.get("feature_descriptions") or [])
            if _text(item)
        ]
        contexts = [
            _text(item)
            for item in (record.get("context_descriptions") or [])
            if _text(item)
        ]
        if not canonical or not kind or not source or not detail or not features or not contexts:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        claim_types = []
        for claim in record.get("supported_claims") or []:
            claim_type = _text((claim or {}).get("claim_type")) if isinstance(claim, dict) else ""
            if claim_type and claim_type not in claim_types:
                claim_types.append(claim_type)
        capabilities.append(
            {
                "canonical_subject": canonical,
                "subject_kind": kind,
                "feature_hints": tuple(features[:3]),
                "context_hints": tuple(contexts[:3]),
                "supported_claim_types": tuple(claim_types),
            }
        )
    return tuple(capabilities)


def grounding_capability_context(
    *,
    production_records: Sequence[Dict[str, Any]] | None = None,
    pool_records: Sequence[Dict[str, Any]] | None = None,
) -> str:
    """Render a compact constraint for the existing Explorer call."""

    capabilities = grounding_candidate_capabilities(
        production_records=production_records,
        pool_records=pool_records,
    )
    if not capabilities:
        return (
            "[GROUNDING-AWARE CANDIDATE SUPPLY]\n"
            f"{NO_GROUNDED_CANDIDATE_SUPPLY}: no trusted aviation grounding capability is registered.\n"
            "Do not invent a substitute subject outside trusted capability."
        )

    lines = [
        "[GROUNDING-AWARE CANDIDATE SUPPLY — RUN 33960845940]",
        "The host can currently verify only the evidence-supported subject space below.",
        "Treat these as capability constraints, not copyable topic titles or required winners.",
        "Explore a concrete, interesting aviation question only inside this subject space.",
        "Vary phenomenon/mechanism/question when evidence permits and avoid recent/rejected topics.",
        "Never leave this capability space merely to increase novelty or diversity.",
    ]
    for index, capability in enumerate(capabilities, start=1):
        features = " | ".join(capability["feature_hints"])
        contexts = " | ".join(capability["context_hints"])
        claim_types = ", ".join(capability["supported_claim_types"]) or "identity-only"
        lines.extend(
            [
                f"CAPABILITY {index}:",
                f"- canonical_subject: {capability['canonical_subject']}",
                f"- subject_kind: {capability['subject_kind']}",
                f"- observable feature hints: {features}",
                f"- aviation context hints: {contexts}",
                f"- evidence-supported semantic roles: {claim_types}",
            ]
        )
    lines.extend(
        [
            "Generate 1..3 reviewable candidates from compatible capabilities only.",
            "Do not fabricate provenance, aliases, mechanisms, or a new canonical subject.",
            "The unchanged host grounding validator will verify every candidate again.",
        ]
    )
    return "\n".join(lines)


def _topic_is_blocked(topic: str, blocked_topics: Sequence[Any]) -> bool:
    """Avoid replaying an exact/near-identical seed already seen this run/history."""

    key = _normalize_topic(topic)
    if not key:
        return True
    for item in blocked_topics or ():
        blocked = _normalize_topic(item)
        if not blocked:
            continue
        if key == blocked:
            return True
        # Only use substring equivalence for reasonably specific strings so broad
        # words like "비행기" cannot suppress unrelated trusted capabilities.
        if min(len(key), len(blocked)) >= 12 and (key in blocked or blocked in key):
            return True
    return False


def grounded_seed_candidate_pool(
    *,
    recent_topics: Sequence[Any] | None = None,
    rejected_topics: Sequence[Any] | None = None,
    production_records: Sequence[Dict[str, Any]] | None = None,
    pool_records: Sequence[Dict[str, Any]] | None = None,
    max_candidates: int = 3,
) -> Dict[str, Any]:
    """Return a bounded repo-owned aviation seed pool with zero model calls.

    Seeds are optional fields on trusted identity records. They do not bypass any
    authority: callers must still send this CANDIDATE_POOL through the unchanged
    Candidate Pool Handoff, canonical grounding, Candidate Gate, FACT, and all
    downstream quality gates. The seed itself carries no private trust channel.

    To make the existing text-based trusted supplier deterministic for repo-owned
    seeds, ``specific_observation`` is rebuilt from the record's own evidence-owned
    feature + context descriptions. This adds no new identity or provenance; it
    simply prevents wording drift between a trusted record and its own seed.
    """

    try:
        limit = max(1, min(int(max_candidates), 3))
    except (TypeError, ValueError):
        limit = 3

    blocked = tuple(recent_topics or ()) + tuple(rejected_topics or ())
    ranked = []
    for record in all_trusted_candidate_records(
        production_records=production_records,
        pool_records=pool_records,
    ):
        if not isinstance(record, dict):
            continue
        if _text(record.get("record_type")).lower() != "trusted_subject_identity":
            continue
        seed = record.get("seed_candidate")
        if not isinstance(seed, dict):
            continue
        topic = _text(seed.get("topic"))
        if not topic or _topic_is_blocked(topic, blocked):
            continue
        required_record_fields = (
            _text(record.get("canonical_subject")),
            _text(record.get("subject_kind")),
            _text(record.get("source")),
            _text(record.get("detail")),
        )
        if not all(required_record_fields):
            continue
        feature_values = record.get("feature_descriptions") or [
            record.get("feature_description")
        ]
        context_values = record.get("context_descriptions") or [
            record.get("context_description")
        ]
        feature_phrase = _preferred_grounding_phrase(feature_values)
        context_phrase = _preferred_grounding_phrase(context_values)
        if not feature_phrase or not context_phrase:
            continue

        grounded_seed = deepcopy(seed)
        grounded_seed["specific_observation"] = (
            f"{feature_phrase}. {context_phrase}."
        )
        try:
            priority = float(record.get("seed_priority", 0))
        except (TypeError, ValueError):
            priority = 0.0
        ranked.append(
            (
                -priority,
                _text(record.get("canonical_subject")).lower(),
                grounded_seed,
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1]))
    candidates = [item[2] for item in ranked[:limit]]
    if not candidates:
        return {
            "status": "REGENERATE",
            "reason": (
                f"{NO_GROUNDED_SEED_SUPPLY}: "
                "no unused repo-owned grounded aviation seed is available"
            ),
        }
    return {
        "status": "CANDIDATE_POOL",
        "candidates": candidates,
    }


def no_grounded_candidate_supply_result(
    *,
    production_records: Sequence[Dict[str, Any]] | None = None,
    pool_records: Sequence[Dict[str, Any]] | None = None,
) -> Dict[str, Any] | None:
    """Fail closed before generation when trusted aviation capability is empty."""

    if grounding_candidate_capabilities(
        production_records=production_records,
        pool_records=pool_records,
    ):
        return None
    return {
        "status": "REGENERATE",
        "reason": (
            f"{NO_GROUNDED_CANDIDATE_SUPPLY}: "
            "no trusted aviation grounding capability is registered"
        ),
    }
