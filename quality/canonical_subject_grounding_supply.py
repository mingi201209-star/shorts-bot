"""Canonical Subject Grounding Supply V1.

This module supplies identity metadata; it does NOT change the Canonical Subject
Grounding Gate V1. The trust boundary is deliberately asymmetric:

* Candidate-model fields are untrusted hints.
* Only repo-owned or caller-injected trusted identity records may populate the
  private ``_trusted_grounding_evidence`` channel.
* Optional repo-owned ``supported_claims`` travel through a separate private
  ``_trusted_grounded_claims`` channel for downstream Writer claim planning.
* A record is usable only when its documented physical-feature observation and
  context jointly match the Candidate text. The resolver never maps one
  appearance word directly to a technical entity.

No network/API call, retry, or model call is performed here.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, List, Sequence


_TRUSTED_RECORD_TYPE = "trusted_subject_identity"
_PHYSICAL_KIND = "physical_entity"
_NON_PHYSICAL_KIND = "non_physical_concept"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = _text(value).lower()
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return " ".join(text.split())


def _candidate_text(candidate: Dict[str, Any]) -> str:
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}
    values = (
        candidate.get("topic"),
        candidate.get("angle"),
        candidate.get("core_question"),
        candidate.get("specific_observation"),
        micro.get("hook"),
        micro.get("core_question"),
        micro.get("reveal"),
        micro.get("payoff"),
    )
    return _normalize(" ".join(_text(value) for value in values if _text(value)))


def _confidence(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(result, 1.0))


def _phrase_tokens(value: Any) -> set[str]:
    return {token for token in _normalize(value).split() if len(token) >= 2}


def _overlap_ratio(left: str, right: str) -> float:
    a = _phrase_tokens(left)
    b = _phrase_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / float(min(len(a), len(b)))


def _record_matches_candidate(candidate_text: str, record: Dict[str, Any]) -> bool:
    """Require both a visible-feature observation and physical context match.

    Records may include multiple evidence-owned descriptions, including a
    faithful Korean description alongside the source-language description.
    This is not a word->entity map: the canonical entity is released only when
    one complete feature description AND one complete context description are
    supported by the Candidate text.
    """

    feature_descriptions = record.get("feature_descriptions")
    if not isinstance(feature_descriptions, list):
        feature_descriptions = [record.get("feature_description")]
    context_descriptions = record.get("context_descriptions")
    if not isinstance(context_descriptions, list):
        context_descriptions = [record.get("context_description")]

    feature_match = any(
        _overlap_ratio(candidate_text, _text(description)) >= 0.60
        for description in feature_descriptions
        if _text(description)
    )
    context_match = any(
        _overlap_ratio(candidate_text, _text(description)) >= 0.60
        for description in context_descriptions
        if _text(description)
    )
    return feature_match and context_match


def _valid_trusted_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    if _text(record.get("record_type")).lower() != _TRUSTED_RECORD_TYPE:
        return False
    if _text(record.get("subject_kind")).lower() != _PHYSICAL_KIND:
        return False
    if not _text(record.get("canonical_subject")):
        return False
    if _confidence(record.get("identity_confidence")) < 0.80:
        return False
    if not _text(record.get("source")) or not _text(record.get("detail")):
        return False
    feature = record.get("feature_descriptions") or record.get("feature_description")
    context = record.get("context_descriptions") or record.get("context_description")
    return bool(feature and context)


def _trusted_gate_evidence(record: Dict[str, Any]) -> Dict[str, str]:
    canonical = _text(record.get("canonical_subject"))
    return {
        "evidence_type": "source_backed_identity",
        "supports_subject": canonical,
        "source": _text(record.get("source")),
        "detail": _text(record.get("detail")),
    }


def _trusted_grounded_claims(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project optional source-backed factual claims into a private channel.

    The supplier does not infer claims from Candidate prose. Claims must already
    exist on the trusted record with provenance and explicit paraphrase scope.
    """
    result: List[Dict[str, Any]] = []
    seen = set()
    for raw in record.get("supported_claims") or []:
        if not isinstance(raw, dict):
            continue
        claim_id = _text(raw.get("claim_id"))
        claim_type = _text(raw.get("claim_type"))
        summary = _text(raw.get("evidence_summary"))
        source = _text(raw.get("source")) or _text(record.get("source"))
        detail = _text(raw.get("detail")) or _text(record.get("detail"))
        scope = [
            _text(value)
            for value in raw.get("allowed_paraphrase_scope") or []
            if _text(value)
        ]
        if not claim_id or claim_id in seen or not claim_type or not summary:
            continue
        if not source or not detail or not scope:
            continue
        seen.add(claim_id)
        result.append({
            "claim_id": claim_id,
            "claim_type": claim_type,
            "evidence_summary": summary,
            "source": source,
            "detail": detail,
            "allowed_paraphrase_scope": scope,
        })
    return result


def supply_trusted_subject_grounding(
    candidate: Dict[str, Any],
    *,
    trusted_records: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Attach trusted identity metadata when evidence explicitly matches.

    Ambiguous or unrelated evidence leaves the Candidate unchanged/fail-closed.
    Candidate-authored ``grounding_evidence`` is never promoted to the private
    trusted channel.
    """

    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    result = deepcopy(candidate)
    if _text(result.get("subject_kind")).lower() == _NON_PHYSICAL_KIND:
        return result

    text = _candidate_text(result)
    matches: List[Dict[str, Any]] = []
    for record in trusted_records or ():
        if _valid_trusted_record(record) and _record_matches_candidate(text, record):
            matches.append(record)

    # Fail closed on no match OR competing identities. The supplier never
    # chooses between multiple plausible physical identities.
    canonicals = {_normalize(record.get("canonical_subject")) for record in matches}
    if len(matches) != 1 or len(canonicals) != 1:
        return result

    record = matches[0]
    canonical = _text(record.get("canonical_subject"))
    confidence = _confidence(record.get("identity_confidence"))
    evidence = _trusted_gate_evidence(record)
    claims = _trusted_grounded_claims(record)

    result["subject_kind"] = _PHYSICAL_KIND
    result["canonical_subject"] = canonical
    result["subject_identity_confidence"] = confidence
    # Public/model-authored evidence is deliberately not used as trust input.
    # Keep only a display copy of the independently supplied record here; the
    # Gate validates the private channel below.
    result["grounding_evidence"] = [deepcopy(evidence)]
    result["_trusted_grounding_evidence"] = [deepcopy(evidence)]
    if claims:
        result["_trusted_grounded_claims"] = deepcopy(claims)
    return result


# Repo-owned authoritative identity provenance. These are evidence records,
# not surface-word mappings. Each record binds official source statements to
# complete physical observation/context descriptions. Optional supported_claims
# are factual evidence records consumed only after identity grounding succeeds.
PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS: tuple[Dict[str, Any], ...] = (
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "feature_descriptions": [
            "sawtooth or serrated trailing edges on a jet engine nacelle or nozzle",
            "비행기 엔진 뒤는 톱니처럼 생긴 가장자리",
            "비행기 엔진 뒤쪽의 톱니 모양 가장자리",
        ],
        "context_descriptions": [
            "jet engine nacelle or nozzle on an aircraft",
            "비행기 제트 엔진 나셀 또는 노즐 뒤쪽",
            "비행기 엔진 뒤는",
            "비행기 엔진 뒤쪽",
        ],
        "source": "https://www.nasa.gov/image-article/nasa-contribution-chevrons/",
        "detail": (
            "NASA identifies chevrons as sawtooth patterns on jet-engine nacelle/nozzle "
            "trailing edges and describes their noise-reduction function by changing how "
            "the exhaust and surrounding flow mix."
        ),
        "supported_claims": [
            {
                "claim_id": "flow_interface",
                "claim_type": "mechanism_input",
                "evidence_summary": (
                    "엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다."
                ),
                "allowed_paraphrase_scope": [
                    "뜨거운 배기 흐름과 차가운 바깥 흐름이 만납니다.",
                    "엔진 배기와 주변의 더 차가운 흐름이 만나는 경계입니다.",
                    "hot exhaust flow meets the cooler surrounding flow",
                ],
            },
            {
                "claim_id": "chevron_flow_mixing",
                "claim_type": "mechanism_change",
                "evidence_summary": (
                    "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다."
                ),
                "allowed_paraphrase_scope": [
                    "톱니 가장자리는 두 흐름이 섞이는 방식을 바꿉니다.",
                    "셰브론은 배기와 주변 공기의 혼합을 바꿉니다.",
                    "chevrons change how the exhaust and surrounding flow mix",
                ],
            },
            {
                "claim_id": "mixing_transition",
                "claim_type": "mechanism_effect",
                "evidence_summary": (
                    "셰브론 때문에 두 흐름의 경계가 더 점진적으로 섞이도록 전환됩니다."
                ),
                "allowed_paraphrase_scope": [
                    "두 흐름의 경계가 더 점진적으로 섞입니다.",
                    "배기와 주변 흐름이 한꺼번에 끊기지 않고 점진적으로 혼합됩니다.",
                    "the two flows mix more gradually across the boundary",
                ],
            },
            {
                "claim_id": "noise_reduction",
                "claim_type": "primary_result",
                "evidence_summary": "이 혼합 변화의 대표적인 결과는 제트 엔진 소음 감소입니다.",
                "allowed_paraphrase_scope": [
                    "제트 소음을 줄입니다.",
                    "엔진에서 나는 소음을 낮춥니다.",
                    "the primary result is reduced jet-engine noise",
                ],
            },
        ],
    },
)
