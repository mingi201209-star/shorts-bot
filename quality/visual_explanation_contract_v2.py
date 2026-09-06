from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal, TypedDict

from quality.visual_state_registry import SubjectStateRegistry


class VisibilityRequirementDict(TypedDict):
    level: Literal["CLEAR"]
    requirements: dict


class ClaimDict(TypedDict):
    id: str
    subject: str
    context: str
    state: str
    required: bool
    visibility: VisibilityRequirementDict


class SplitBindingDict(TypedDict):
    claim_id: str
    slot: Literal["LEFT", "RIGHT"]


class SequentialBindingDict(TypedDict):
    claim_id: str
    sequence_index: int
    start_sec: float
    end_sec: float


class ComparisonSegmentDict(TypedDict):
    id: str
    presentation: Literal["SPLIT_SCREEN", "SEQUENTIAL"]
    start_sec: float
    end_sec: float
    bindings: list[dict]


class RelationDict(TypedDict):
    id: str
    type: Literal["CONTRAST"]
    members: list[str]
    comparison_segment_id: str
    required: bool


class ContractDict(TypedDict):
    version: Literal["visual_explanation_contract_v2.1"]
    scene_id: int
    mode: Literal["shadow"]
    claims: list[ClaimDict]
    comparison_segments: list[ComparisonSegmentDict]
    relations: list[RelationDict]


class ContractValidationError(Exception):
    pass


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)


def _duplicates(values: list[str]) -> list[str]:
    return sorted({v for v in values if values.count(v) > 1})


def semantic_validate(contract: ContractDict, registry: SubjectStateRegistry) -> ValidationResult:
    result = ValidationResult()
    claims = contract["claims"]
    segments = contract["comparison_segments"]
    relations = contract["relations"]

    claim_ids = [c["id"] for c in claims]
    relation_ids = [r["id"] for r in relations]
    segment_ids = [s["id"] for s in segments]
    if _duplicates(claim_ids):
        result.add(f"duplicate claim.id: {_duplicates(claim_ids)}")
    if _duplicates(relation_ids):
        result.add(f"duplicate relation.id: {_duplicates(relation_ids)}")
    if _duplicates(segment_ids):
        result.add(f"duplicate comparison_segment.id: {_duplicates(segment_ids)}")

    claim_by_id = {c["id"]: c for c in claims}
    segment_by_id = {s["id"]: s for s in segments}

    for claim in claims:
        if not registry.is_valid(claim["subject"], claim["state"]):
            result.add(
                f"claim '{claim['id']}' invalid subject/state: "
                f"{claim['subject']!r}/{claim['state']!r}"
            )

    for seg in segments:
        if not seg["start_sec"] < seg["end_sec"]:
            result.add(f"comparison_segment '{seg['id']}' requires start_sec < end_sec")
        bindings = seg["bindings"]
        binding_ids = [b["claim_id"] for b in bindings]
        if len(set(binding_ids)) != len(binding_ids):
            result.add(f"comparison_segment '{seg['id']}' has duplicate claim bindings")
        missing = [cid for cid in binding_ids if cid not in claim_by_id]
        if missing:
            result.add(f"comparison_segment '{seg['id']}' references unknown claims: {missing}")

        if seg["presentation"] == "SPLIT_SCREEN":
            slots = [b.get("slot") for b in bindings]
            if set(slots) != {"LEFT", "RIGHT"} or len(slots) != 2:
                result.add(f"comparison_segment '{seg['id']}' requires exactly LEFT and RIGHT")
            for b in bindings:
                if any(k in b for k in ("sequence_index", "start_sec", "end_sec")):
                    result.add(f"comparison_segment '{seg['id']}' split binding contains sequential fields")
        elif seg["presentation"] == "SEQUENTIAL":
            for b in bindings:
                if "slot" in b:
                    result.add(f"comparison_segment '{seg['id']}' sequential binding contains slot")
            indexes = [b.get("sequence_index") for b in bindings]
            if set(indexes) != {0, 1} or len(indexes) != 2:
                result.add(f"comparison_segment '{seg['id']}' requires sequence_index {{0,1}}")
            else:
                ordered = sorted(bindings, key=lambda b: b["sequence_index"])
                for b in ordered:
                    start, end = b.get("start_sec"), b.get("end_sec")
                    if start is None or end is None or not start < end:
                        result.add(f"comparison_segment '{seg['id']}' invalid sequential interval")
                        continue
                    if start < seg["start_sec"] or end > seg["end_sec"]:
                        result.add(f"comparison_segment '{seg['id']}' binding interval outside segment")
                if all(k in ordered[0] and k in ordered[1] for k in ("start_sec", "end_sec")):
                    if ordered[0]["start_sec"] > ordered[1]["start_sec"]:
                        result.add(f"comparison_segment '{seg['id']}' sequence/time order mismatch")
                    if ordered[0]["end_sec"] > ordered[1]["start_sec"]:
                        result.add(f"comparison_segment '{seg['id']}' sequential intervals overlap")

    for rel in relations:
        if rel["type"] != "CONTRAST" or len(rel["members"]) != 2:
            result.add(f"relation '{rel['id']}' V2.1 CONTRAST requires exactly 2 members")
        missing = [cid for cid in rel["members"] if cid not in claim_by_id]
        if missing:
            result.add(f"relation '{rel['id']}' references unknown claims: {missing}")
        seg = segment_by_id.get(rel["comparison_segment_id"])
        if seg is None:
            result.add(f"relation '{rel['id']}' references unknown segment '{rel['comparison_segment_id']}'")
        else:
            binding_ids = {b["claim_id"] for b in seg["bindings"]}
            if binding_ids != set(rel["members"]):
                result.add(f"relation '{rel['id']}' members do not match segment bindings")
    return result


def assert_bounded_repair(before: ContractDict, after: ContractDict) -> None:
    """Only claim.state may change, and only via an explicit registry alias at the caller."""
    before_copy = deepcopy(before)
    after_copy = deepcopy(after)
    if len(before_copy["claims"]) != len(after_copy["claims"]):
        raise ContractValidationError("bounded repair changed claim count")
    for b, a in zip(before_copy["claims"], after_copy["claims"]):
        b.pop("state", None)
        a.pop("state", None)
    if before_copy != after_copy:
        raise ContractValidationError("bounded repair mutated structural identity outside claim.state")
