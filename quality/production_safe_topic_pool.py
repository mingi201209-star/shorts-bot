"""Deterministic production-safe topic eligibility.

This does not bypass any production quality gate. It only identifies fixed topics
whose repo-owned trusted grounding already supplies enough factual coverage to
enter the existing Writer/FACT/Visual pipeline safely.
"""
from __future__ import annotations

from typing import Any, Dict, List

from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from content.grounded_claim_plan import build_grounded_claim_plan

MIN_SUPPORTED_CLAIMS = 3

SAFE_TOPIC_SPECS = (
    {
        "topic": "비행기 창문 모서리는 왜 둥글게 만들어졌을까",
        "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
        "candidate_scope": "aviation",
    },
)


def _record_for_subject(canonical_subject: str) -> Dict[str, Any] | None:
    for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS:
        if str(record.get("canonical_subject") or "").strip() == canonical_subject:
            return record
    return None


def inspect_safe_topic(topic: str) -> Dict[str, Any]:
    spec = next((item for item in SAFE_TOPIC_SPECS if item["topic"] == topic), None)
    if spec is None:
        return {"eligible": False, "reason": "topic is not in repo-owned production-safe registry"}
    record = _record_for_subject(spec["canonical_subject"])
    if record is None:
        return {"eligible": False, "reason": "trusted canonical subject record is missing"}
    if record.get("subject_kind") != "physical_entity":
        return {"eligible": False, "reason": "canonical subject kind is not physical_entity"}
    if float(record.get("identity_confidence") or 0.0) <= 0.0:
        return {"eligible": False, "reason": "canonical identity confidence is unresolved"}
    source = str(record.get("source") or "").strip()
    if not source:
        return {"eligible": False, "reason": "trusted evidence source is missing"}

    candidate = {"_trusted_grounded_claims": list(record.get("supported_claims") or [])}
    plan = build_grounded_claim_plan(candidate)
    claim_ids = [str(item.get("claim_id") or "").strip() for item in plan]
    if len(plan) < MIN_SUPPORTED_CLAIMS:
        return {"eligible": False, "reason": "fewer than 3 supported grounded claims"}
    if len(claim_ids) != len(set(claim_ids)):
        return {"eligible": False, "reason": "grounded claim ids are not distinct"}
    owner_scenes = [int(item["owner_scene"]) for item in plan]
    if len(owner_scenes) != len(set(owner_scenes)):
        return {"eligible": False, "reason": "grounded claims do not have unique owners"}

    return {
        "eligible": True,
        "topic": topic,
        "candidate_scope": spec["candidate_scope"],
        "canonical_subject": spec["canonical_subject"],
        "source": source,
        "claim_ids": claim_ids,
        "owner_scenes": owner_scenes,
        "record": record,
        "grounded_claim_plan": plan,
    }


def eligible_safe_topics() -> List[str]:
    return [spec["topic"] for spec in SAFE_TOPIC_SPECS if inspect_safe_topic(spec["topic"])["eligible"]]
