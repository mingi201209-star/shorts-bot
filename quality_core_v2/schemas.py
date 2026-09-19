"""Typed contracts for the Clean V2 quality core.

Plain dataclasses with a `from_dict`/`validate_shape` pair each, instead of
pydantic/etc., to keep this package dependency-free (it must be importable
and runnable with zero network access, per the replay harness contract).

These are the SAME field names used in the fixtures under
quality_core_v2/fixtures/*.json -- the fixtures are the executable spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ShapeError(ValueError):
    """A required field was missing or the wrong type."""


def _require(d: Dict[str, Any], key: str, kind, ctx: str) -> Any:
    if key not in d:
        raise ShapeError(f"{ctx}: missing required field '{key}'")
    value = d[key]
    if not isinstance(value, kind):
        raise ShapeError(
            f"{ctx}: field '{key}' must be {kind}, got {type(value).__name__}"
        )
    return value


# ============================================================
# CandidateV2
# ============================================================

@dataclass
class CandidateV2:
    topic: str
    concrete_subject: str
    observable_phenomenon: str
    core_question: str
    mechanism: str
    reveal: str
    canonical_subject: str
    evidence_refs: List[str] = field(default_factory=list)
    visual_proof: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CandidateV2":
        ctx = "CandidateV2"
        return CandidateV2(
            topic=_require(d, "topic", str, ctx),
            concrete_subject=_require(d, "concrete_subject", str, ctx),
            observable_phenomenon=_require(d, "observable_phenomenon", str, ctx),
            core_question=_require(d, "core_question", str, ctx),
            mechanism=_require(d, "mechanism", str, ctx),
            reveal=_require(d, "reveal", str, ctx),
            canonical_subject=_require(d, "canonical_subject", str, ctx),
            evidence_refs=list(d.get("evidence_refs") or []),
            visual_proof=list(d.get("visual_proof") or []),
        )


# ============================================================
# GroundingV2
# ============================================================

@dataclass
class GroundingV2:
    subject_kind: str  # "physical_entity" | "non_physical_concept" | "unresolved"
    identity_confidence: float
    evidence_refs: List[str] = field(default_factory=list)
    provenance: str = ""

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GroundingV2":
        ctx = "GroundingV2"
        return GroundingV2(
            subject_kind=_require(d, "subject_kind", str, ctx),
            identity_confidence=float(d.get("identity_confidence", 0.0)),
            evidence_refs=list(d.get("evidence_refs") or []),
            provenance=str(d.get("provenance", "")),
        )


# ============================================================
# ScriptPlanV2 (a list of SceneV2)
# ============================================================

@dataclass
class SceneV2:
    scene_index: int
    narration: str
    causal_role: str
    owned_claim_id: str
    new_information: str
    visual_requirement: str
    evidence_refs: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SceneV2":
        ctx = "SceneV2"
        return SceneV2(
            scene_index=int(_require(d, "scene_index", int, ctx)),
            narration=_require(d, "narration", str, ctx),
            causal_role=_require(d, "causal_role", str, ctx),
            owned_claim_id=_require(d, "owned_claim_id", str, ctx),
            new_information=_require(d, "new_information", str, ctx),
            visual_requirement=_require(d, "visual_requirement", str, ctx),
            evidence_refs=list(d.get("evidence_refs") or []),
        )


# ============================================================
# VisualPlanV2
# ============================================================

@dataclass
class VisualPlanV2:
    scene_index: int
    subject: str
    required_visible_components: List[str] = field(default_factory=list)
    required_observable_state: List[str] = field(default_factory=list)
    required_relation_or_mechanism: List[str] = field(default_factory=list)
    forbidden_visuals: List[str] = field(default_factory=list)
    preferred_source_type: str = ""
    search_queries: List[str] = field(default_factory=list)
    generation_prompt_constraints: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "VisualPlanV2":
        ctx = "VisualPlanV2"
        return VisualPlanV2(
            scene_index=int(_require(d, "scene_index", int, ctx)),
            subject=_require(d, "subject", str, ctx),
            required_visible_components=list(d.get("required_visible_components") or []),
            required_observable_state=list(d.get("required_observable_state") or []),
            required_relation_or_mechanism=list(d.get("required_relation_or_mechanism") or []),
            forbidden_visuals=list(d.get("forbidden_visuals") or []),
            preferred_source_type=str(d.get("preferred_source_type", "")),
            search_queries=list(d.get("search_queries") or []),
            generation_prompt_constraints=list(d.get("generation_prompt_constraints") or []),
            evidence_refs=list(d.get("evidence_refs") or []),
        )


# ============================================================
# CandidateVisualV2 -- what retrieval/generation actually produced,
# checked against a VisualPlanV2 by visual_qa.py
# ============================================================

@dataclass
class CandidateVisualV2:
    source_type: str  # "stock" | "generated" | "grounded_explanatory"
    description: str
    visible_components: List[str] = field(default_factory=list)
    observable_state: List[str] = field(default_factory=list)
    visible_relations_or_mechanisms: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Exact asset identity.  V2 must render this exact accepted asset; these
    # fields are intentionally part of the typed contract so a later stage
    # cannot silently search again from a keyword and pick something else.
    provider: str = ""
    source_id: str = ""
    media_url: str = ""
    thumbnail_url: str = ""
    search_query: str = ""

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CandidateVisualV2":
        ctx = "CandidateVisualV2"
        return CandidateVisualV2(
            source_type=_require(d, "source_type", str, ctx),
            description=_require(d, "description", str, ctx),
            visible_components=list(d.get("visible_components") or []),
            observable_state=list(d.get("observable_state") or []),
            visible_relations_or_mechanisms=list(
                d.get("visible_relations_or_mechanisms") or []
            ),
            tags=list(d.get("tags") or []),
            provider=str(d.get("provider", "")),
            source_id=str(d.get("source_id", "")),
            media_url=str(d.get("media_url", "")),
            thumbnail_url=str(d.get("thumbnail_url", "")),
            search_query=str(d.get("search_query", "")),
        )


@dataclass
class Verdict:
    passed: bool
    reason: str
    stage: str

    def to_dict(self) -> Dict[str, Any]:
        return {"passed": self.passed, "reason": self.reason, "stage": self.stage}
