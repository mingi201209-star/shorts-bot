"""Canonical Subject Grounding Gate V1.

This module owns one narrow invariant:
A physical subject must have a resolved identity before any Writer or FACT
mechanism reasoning is allowed to proceed.

It deliberately does not identify objects itself. Identity must arrive as
structured Candidate grounding metadata; otherwise the contract fails closed.
A model-authored source string is not trusted provenance.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List


IDENTITY_CONFIDENCE_MIN = 0.80

_PHYSICAL_KIND = "physical_entity"
_NON_PHYSICAL_KIND = "non_physical_concept"
_UNKNOWN_SUBJECTS = {"", "unknown", "unresolved", "none", "null", "n/a"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_subject(value: Any) -> str:
    return " ".join(_text(value).lower().split())


def _confidence(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(result, 1.0))


def _candidate_text(candidate: Dict[str, Any]) -> str:
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}
    values: Iterable[Any] = (
        candidate.get("topic"),
        candidate.get("angle"),
        candidate.get("core_question"),
        micro.get("hook"),
        micro.get("core_question"),
        micro.get("reveal"),
        micro.get("payoff"),
    )
    return " ".join(_text(value) for value in values if _text(value)).lower()


def _normalize_evidence(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record = {
            "evidence_type": _text(item.get("evidence_type")).lower(),
            "supports_subject": _text(item.get("supports_subject")),
            "source": _text(item.get("source")),
            "detail": _text(item.get("detail")),
        }
        if any(record.values()):
            normalized.append(record)
    return normalized


def _explicit_evidence_supports_subject(
    evidence: Dict[str, str],
    *,
    canonical_subject: str,
    candidate_text: str,
) -> bool:
    if _text(evidence.get("evidence_type")).lower() != "explicit_candidate_identity":
        return False
    supports = _normalized_subject(evidence.get("supports_subject"))
    canonical = _normalized_subject(canonical_subject)
    if not canonical or supports != canonical:
        return False
    # The model cannot relabel an ambiguous surface description merely by
    # asserting a technical name in metadata. The name must exist in the
    # Candidate's actual story text.
    return canonical in candidate_text


def _trusted_source_evidence_supports_subject(
    evidence: Dict[str, str],
    *,
    canonical_subject: str,
) -> bool:
    if _text(evidence.get("evidence_type")).lower() != "source_backed_identity":
        return False
    supports = _normalized_subject(evidence.get("supports_subject"))
    canonical = _normalized_subject(canonical_subject)
    return bool(
        canonical
        and supports == canonical
        and _text(evidence.get("source"))
        and _text(evidence.get("detail"))
    )


def normalize_candidate_subject_metadata(candidate: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    return {
        "subject_kind": _text(candidate.get("subject_kind")).lower(),
        "canonical_subject": _text(candidate.get("canonical_subject")),
        "subject_identity_confidence": _confidence(
            candidate.get("subject_identity_confidence")
        ),
        "grounding_evidence": _normalize_evidence(
            candidate.get("grounding_evidence")
        ),
    }


def _blocked(reason: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "BLOCK",
        "failure_type": "SUBJECT_IDENTITY_UNRESOLVED",
        "reason": reason,
        "mechanism_inference_allowed": False,
        "subject_grounding": deepcopy(metadata),
    }


def evaluate_candidate_subject_grounding(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate identity only; never infer or repair a subject identity.

    ``grounding_evidence`` is model-visible metadata. It can prove an explicit
    identity only when the canonical name is literally present in Candidate
    text. Source-backed identity for an otherwise ambiguous object must arrive
    through the private ``_trusted_grounding_evidence`` channel, populated by
    trusted pipeline code rather than Candidate model output.
    """

    metadata = normalize_candidate_subject_metadata(candidate)
    subject_kind = metadata["subject_kind"]

    if subject_kind == _NON_PHYSICAL_KIND:
        return {
            "status": "PASS",
            "failure_type": None,
            "reason": "non-physical concept: physical identity gate not applicable",
            "mechanism_inference_allowed": True,
            "subject_grounding": deepcopy(metadata),
        }

    if subject_kind != _PHYSICAL_KIND:
        return _blocked(
            "physical/non-physical subject kind is unresolved",
            metadata,
        )

    canonical_subject = metadata["canonical_subject"]
    canonical_key = _normalized_subject(canonical_subject)
    if canonical_key in _UNKNOWN_SUBJECTS:
        return _blocked(
            "canonical physical subject is UNKNOWN",
            metadata,
        )

    if metadata["subject_identity_confidence"] < IDENTITY_CONFIDENCE_MIN:
        return _blocked(
            "subject identity confidence is below the grounding floor",
            metadata,
        )

    candidate_text = _candidate_text(candidate)
    explicit_evidence = [
        item
        for item in metadata["grounding_evidence"]
        if _explicit_evidence_supports_subject(
            item,
            canonical_subject=canonical_subject,
            candidate_text=candidate_text,
        )
    ]

    # Never trust a source/citation string authored inside Candidate output as
    # provenance. A future grounding retriever may attach evidence here after
    # independently verifying it; current production simply rejects ambiguous
    # identities when that trusted channel is absent.
    trusted_evidence = _normalize_evidence(candidate.get("_trusted_grounding_evidence"))
    trusted_source_evidence = [
        item
        for item in trusted_evidence
        if _trusted_source_evidence_supports_subject(
            item,
            canonical_subject=canonical_subject,
        )
    ]

    valid_evidence = explicit_evidence + trusted_source_evidence
    if not valid_evidence:
        return _blocked(
            "no trusted evidence supports the canonical physical subject identity",
            metadata,
        )

    metadata["grounding_evidence"] = valid_evidence
    return {
        "status": "PASS",
        "failure_type": None,
        "reason": "canonical physical subject identity is grounded",
        "mechanism_inference_allowed": True,
        "subject_grounding": deepcopy(metadata),
    }


def fact_identity_precheck(script_data: Dict[str, Any]):
    """Return a deterministic FACT critical result when identity is unresolved.

    ``None`` means FACT may proceed to its normal mechanism/factual review.
    This check intentionally executes before any FACT API call. Evidence inside
    ``subject_grounding`` was already validated by the pre-Writer trust boundary.
    """

    if not isinstance(script_data, dict):
        raise TypeError("script_data must be a dict")

    grounding = script_data.get("subject_grounding")
    if not isinstance(grounding, dict):
        grounding = {}

    subject_kind = _text(grounding.get("subject_kind")).lower()
    if subject_kind == _NON_PHYSICAL_KIND:
        return None

    metadata = {
        "subject_kind": subject_kind,
        "canonical_subject": _text(grounding.get("canonical_subject")),
        "subject_identity_confidence": _confidence(
            grounding.get("subject_identity_confidence")
        ),
        "grounding_evidence": _normalize_evidence(
            grounding.get("grounding_evidence")
        ),
    }
    canonical = _normalized_subject(metadata["canonical_subject"])
    evidence = metadata["grounding_evidence"]

    identity_ok = (
        subject_kind == _PHYSICAL_KIND
        and canonical not in _UNKNOWN_SUBJECTS
        and metadata["subject_identity_confidence"] >= IDENTITY_CONFIDENCE_MIN
        and bool(evidence)
    )

    if identity_ok:
        return None

    return {
        "judge_type": "fact",
        "score": 0.0,
        "confidence": 1.0,
        "reason": (
            "Canonical Subject Grounding Gate V1: 물체 정체성이 확정되지 않아 "
            "기능/원리의 일반적 plausibility만으로 FACT를 통과시킬 수 없습니다."
        ),
        "issues": [
            "먼저 물체가 무엇인지 canonical identity와 evidence로 확정해야 합니다."
        ],
        "critical_risk": True,
        "failure_type": "SUBJECT_IDENTITY_UNRESOLVED",
    }
