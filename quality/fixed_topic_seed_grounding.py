"""Exact repo-owned seed grounding for explicitly pinned production topics.

This module does not broaden Candidate matching. It only reuses an existing
trusted record when all of the following are true:

* production has an explicit fixed topic;
* the selected Candidate topic is exactly that fixed topic after outer trim;
* exactly one active trusted record owns a seed_candidate with that exact topic;
* that record still passes the existing canonical grounding supplier when fed
  only its own evidence-owned seed plus record-owned feature/context evidence.

Unknown, altered, ambiguous, or duplicate seed topics return ``None`` and keep
the existing fail-closed path authoritative.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Sequence, Tuple

from quality.canonical_subject_grounding_supply import (
    supply_trusted_subject_grounding,
)


_TRUST_FIELDS = (
    "subject_kind",
    "canonical_subject",
    "subject_identity_confidence",
    "grounding_evidence",
    "_trusted_grounding_evidence",
    "_trusted_grounded_claims",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def exact_fixed_topic_seed_record(
    candidate: Dict[str, Any],
    fixed_topic: Any,
    *,
    trusted_records: Sequence[Dict[str, Any]],
) -> Dict[str, Any] | None:
    """Resolve one record only by exact host-pinned topic + repo seed ownership."""

    if not isinstance(candidate, dict):
        return None

    fixed = _text(fixed_topic)
    if not fixed or _text(candidate.get("topic")) != fixed:
        return None

    matches = []
    for record in trusted_records or ():
        if not isinstance(record, dict):
            continue
        seed = record.get("seed_candidate")
        if not isinstance(seed, dict):
            continue
        if _text(seed.get("topic")) == fixed:
            matches.append(record)

    # Never choose between duplicate/competing host records.
    if len(matches) != 1:
        return None
    return matches[0]


def supply_exact_fixed_topic_seed_grounding(
    candidate: Dict[str, Any],
    fixed_topic: Any,
    *,
    trusted_records: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]] | None:
    """Attach only supplier-validated metadata from one exact repo-owned seed.

    The temporary supplier input is built from the trusted record's own seed and
    evidence-owned feature/context descriptions. Only the supplier's trusted
    identity/claim fields are copied onto the selected model Candidate; model
    prose is preserved and all downstream FACT/quality gates remain unchanged.
    """

    record = exact_fixed_topic_seed_record(
        candidate,
        fixed_topic,
        trusted_records=trusted_records,
    )
    if record is None:
        return None

    seed = record.get("seed_candidate")
    if not isinstance(seed, dict):
        return None

    seed_for_supply = deepcopy(seed)
    evidence_phrases = []
    for key in ("feature_descriptions", "context_descriptions"):
        values = record.get(key) or []
        if not isinstance(values, (list, tuple)):
            values = [values]
        evidence_phrases.extend(_text(value) for value in values if _text(value))
    if evidence_phrases:
        seed_for_supply["specific_observation"] = ". ".join(evidence_phrases)

    verified_seed = supply_trusted_subject_grounding(
        seed_for_supply,
        trusted_records=(record,),
    )
    if not verified_seed.get("_trusted_grounding_evidence"):
        return None

    result = deepcopy(candidate)
    for field in _TRUST_FIELDS:
        if field in verified_seed:
            result[field] = deepcopy(verified_seed[field])

    if not result.get("_trusted_grounding_evidence"):
        return None
    return result, record


# RUN_35320620429_FIXED_TOPIC_GROUNDING_SCOPE_V1
_TRUSTED_GROUNDING_FIELDS = (
    "grounding_evidence",
    "_trusted_grounding_evidence",
    "_trusted_grounded_claims",
    "_subject_grounding",
    "_repo_owned_seed_record_ref",
)


def supply_fixed_topic_scoped_trusted_grounding(
    candidate: Dict[str, Any],
    fixed_topic: Any,
    *,
    trusted_records: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Re-supply trust only from records the pinned topic itself can support.

    A Candidate can contain downstream details that accidentally resemble a
    different trusted component. Fixed-topic production must not let those
    details redefine the subject selected by the operator. Existing trusted
    metadata is stripped before resupply so a prior false match cannot survive.
    """

    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    fixed = _text(fixed_topic)
    result = deepcopy(candidate)
    if not fixed or _text(result.get("topic")) != fixed:
        return supply_trusted_subject_grounding(
            result,
            trusted_records=trusted_records,
        )

    for field in _TRUSTED_GROUNDING_FIELDS:
        result.pop(field, None)

    scoped_records = []
    for record in trusted_records or ():
        if not isinstance(record, dict):
            continue
        topic_probe = supply_trusted_subject_grounding(
            {"topic": fixed},
            trusted_records=(record,),
        )
        if topic_probe.get("_trusted_grounding_evidence"):
            scoped_records.append(record)

    if not scoped_records:
        return result

    return supply_trusted_subject_grounding(
        result,
        trusted_records=tuple(scoped_records),
    )
