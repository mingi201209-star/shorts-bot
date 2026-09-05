"""Grounding-aware Candidate Explorer supply context.

This module exposes the exact repo-owned trusted grounding capability already
used by host validation.  It adds no model/network call and never grants trust;
it only tells aviation Candidate Explorer which canonical subject space the host
can currently verify.  Host canonical grounding remains authoritative.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Sequence

from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)


NO_GROUNDED_CANDIDATE_SUPPLY = "NO_GROUNDED_CANDIDATE_SUPPLY"


def _text(value: Any) -> str:
    return str(value or "").strip()


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
    not create new subject identities.  A capability exists only when the record
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
