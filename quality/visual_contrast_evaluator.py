from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from quality.visual_explanation_contract_v2 import ContractDict, RelationDict
from quality.visual_state_evidence import EvidenceState


class RelationResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class EvaluationStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class ContrastEvaluation:
    relation_id: str
    status: EvaluationStatus
    result: RelationResult
    member_evidence: dict[str, EvidenceState]
    reason: str
    diagnostic: str | None = None


def evaluate_contrast(
    contract: ContractDict,
    relation: RelationDict,
    claim_evidence: dict[str, EvidenceState],
) -> ContrastEvaluation:
    members = relation["members"]
    missing = [m for m in members if m not in claim_evidence]
    if missing:
        return ContrastEvaluation(
            relation["id"], EvaluationStatus.INCOMPLETE, RelationResult.FAIL,
            {m: claim_evidence[m] for m in members if m in claim_evidence},
            "relation evaluation incomplete",
            diagnostic=f"EVIDENCE_MISSING: {missing}",
        )

    evidence_by_member = {m: claim_evidence[m] for m in members}
    contradicted = [m for m, e in evidence_by_member.items() if e == EvidenceState.CONTRADICTED]
    if contradicted:
        return ContrastEvaluation(
            relation["id"], EvaluationStatus.COMPLETE, RelationResult.FAIL,
            evidence_by_member, f"member(s) CONTRADICTED: {contradicted}",
        )

    unverified = [m for m, e in evidence_by_member.items() if e in {EvidenceState.ABSENT, EvidenceState.NOT_VERIFIED}]
    if unverified:
        return ContrastEvaluation(
            relation["id"], EvaluationStatus.COMPLETE, RelationResult.FAIL,
            evidence_by_member, f"member(s) not VERIFIED: {unverified}",
        )

    segment_by_id = {s["id"]: s for s in contract["comparison_segments"]}
    segment = segment_by_id.get(relation["comparison_segment_id"])
    if segment is None:
        return ContrastEvaluation(
            relation["id"], EvaluationStatus.INCOMPLETE, RelationResult.FAIL,
            evidence_by_member, "relation evaluation incomplete",
            diagnostic=f"SEGMENT_MISSING: {relation['comparison_segment_id']}",
        )
    binding_ids = {b["claim_id"] for b in segment["bindings"]}
    if binding_ids != set(members):
        return ContrastEvaluation(
            relation["id"], EvaluationStatus.INCOMPLETE, RelationResult.FAIL,
            evidence_by_member, "relation evaluation incomplete",
            diagnostic="SEGMENT_BINDING_MISMATCH",
        )
    if segment["presentation"] not in {"SPLIT_SCREEN", "SEQUENTIAL"}:
        return ContrastEvaluation(
            relation["id"], EvaluationStatus.INCOMPLETE, RelationResult.FAIL,
            evidence_by_member, "relation evaluation incomplete",
            diagnostic=f"UNSUPPORTED_PRESENTATION: {segment['presentation']}",
        )

    return ContrastEvaluation(
        relation["id"], EvaluationStatus.COMPLETE, RelationResult.PASS,
        evidence_by_member,
        f"all members VERIFIED within segment '{segment['id']}' ({segment['presentation']})",
    )
