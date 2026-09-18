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


# RUN_35323852030_FIXED_TOPIC_TRUSTED_OPENING_V1
_WEAK_FIXED_TOPIC_OPENING_MARKERS = (
    "관찰됩니다",
    "볼 수 있습니다",
    "볼 수 있습니다.",
    "모습을 볼 수",
    "모습이 보입니다",
    "보이는 모습을",
)


def project_exact_fixed_topic_seed_opening(
    candidate: Dict[str, Any],
    fixed_topic: Any,
    *,
    trusted_records: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    """Replace only a weak descriptive opening with the repo-owned seed opening.

    Run 35323852030 reached the correct NASA-backed wing subject and passed
    FACT/Visual at 8/10, but Script V2 locked an LLM-authored Scene 1 that merely
    said the bending was "observed". The bounded Rewrite repeated the same
    descriptive opening and Hook stayed 6/10.

    This is intentionally narrow:
    * exact pinned topic must resolve to exactly one repo-owned seed;
    * current Hook must contain an observed weak-description marker;
    * replacement Hook + Question come only from that trusted seed;
    * the existing opening-human contract must accept the pair;
    * no fact/reveal/payoff/body text, threshold, retry, API call, or budget changes.
    """

    result = deepcopy(candidate)
    record = exact_fixed_topic_seed_record(
        result,
        fixed_topic,
        trusted_records=trusted_records,
    )
    if record is None:
        return result, None

    micro = result.get("micro_narrative")
    seed = record.get("seed_candidate")
    seed_micro = (seed or {}).get("micro_narrative") if isinstance(seed, dict) else None
    if not isinstance(micro, dict) or not isinstance(seed_micro, dict):
        return result, record

    current_hook = _text(micro.get("hook"))
    if not current_hook:
        return result, record
    if not any(marker in current_hook for marker in _WEAK_FIXED_TOPIC_OPENING_MARKERS):
        return result, record

    trusted_hook = _text(seed_micro.get("hook"))
    trusted_question = _text(seed_micro.get("core_question")) or _text(
        (seed or {}).get("core_question")
    )
    if not trusted_hook or not trusted_question:
        return result, record

    # Reuse the existing deterministic first-5 progression validator rather
    # than inventing a weaker opening rule. The seed's grounded reveal provides
    # the causal-clue probe; no generated text or model call is introduced.
    from content.retention_structure import validate_first5_progression

    trusted_clue = _text(seed_micro.get("reveal"))
    if not trusted_clue:
        return result, record

    first5_ok, _ = validate_first5_progression([
        {
            "retention_role": "phenomenon",
            "text": trusted_hook,
            "visual_goal": "trusted fixed-topic observable subject",
        },
        {
            "retention_role": "question",
            "text": trusted_question,
            "visual_goal": "trusted fixed-topic causal question",
        },
        {
            "retention_role": "causal_clue",
            "text": trusted_clue,
            "visual_goal": "trusted fixed-topic causal clue",
        },
    ])
    if not first5_ok:
        return result, record

    updated_micro = deepcopy(micro)
    updated_micro["hook"] = trusted_hook
    updated_micro["core_question"] = trusted_question
    result["micro_narrative"] = updated_micro
    result["core_question"] = trusted_question
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
