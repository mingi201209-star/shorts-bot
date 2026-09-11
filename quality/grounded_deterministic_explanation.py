"""Grounded Deterministic Explanation V1 -- shape schema + parser for the
PRODUCE/DETERMINISTIC_EXPLANATION params attached to a Bounded Visual
Escalation RoutingDecision (quality/visual_escalation_router.py), scoped to
exactly one template: AIRCRAFT_WINDOW_STRESS_V1.

This module is PHASE 1 (schema/parser baseline) only:
  - shape validation: is the params object well-formed (required fields,
    types, supported enum values, no additional properties)?
  - structural-semantic validation: are the params internally consistent
    (template_id matches its own required companion fields, no cross-field
    contradiction)?

It does NOT decide whether a given Scene/candidate is actually eligible to
use this template -- that is Phase 2's grounding adapter
(video/aircraft_window_stress_grounding.py), which reads existing trusted
grounding/claim registry authority only, never Vision EvidenceState.

Role separation (binding, restated here because this module is the schema
boundary between the two):
  INPUT AUTHORITY  -- trusted grounding / claim registry: decides WHAT may be
                      drawn. Never Vision EvidenceState.
  OUTPUT AUTHORITY -- existing Visual Semantic QA / Visual Diversity /
                      Director / Final Render Content Integrity: decides
                      whether the actual render is correct. Unchanged, never
                      bypassed by this module.

Shape-invalid and semantic-invalid params are both non-selection: this
module never raises to fail the whole pipeline, and it never itself picks
RETURN_UPSTREAM/TERMINATE -- that stays the router's decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# V1 supports exactly one template. No stub/TODO entries for future templates.
TEMPLATE_AIRCRAFT_WINDOW_STRESS_V1 = "AIRCRAFT_WINDOW_STRESS_V1"
SUPPORTED_TEMPLATE_IDS = frozenset({TEMPLATE_AIRCRAFT_WINDOW_STRESS_V1})

# V1 permits exactly one evidence source. Deliberately not widened for future
# extensibility -- that is out of V1 scope (task section 4).
EVIDENCE_SOURCE_TRUSTED_GROUNDING = "TRUSTED_GROUNDING"
SUPPORTED_EVIDENCE_SOURCES = frozenset({EVIDENCE_SOURCE_TRUSTED_GROUNDING})

# Escalation-level relation shape. Distinct from ComparisonSegmentDict's own
# "presentation" field (SPLIT_SCREEN/SEQUENTIAL) in the existing V2.1
# contract, which this template reuses unchanged via comparison_segment_id.
PRESENTATION_CONTRAST = "CONTRAST"
SUPPORTED_PRESENTATIONS = frozenset({PRESENTATION_CONTRAST})

_REQUIRED_FIELDS = (
    "template_id",
    "presentation",
    "canonical_subject_id",
    "owned_claim_id",
    "evidence_source",
    "grounding_provenance_ref",
    "grounding_fingerprint",
    "comparison_segment_id",
    "param_signature",
)
_REQUIRED_FIELD_SET = frozenset(_REQUIRED_FIELDS)


@dataclass
class ShapeValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)


def validate_deterministic_explanation_params_shape(params: Any) -> ShapeValidationResult:
    """Shape only: required fields present, correct type, supported enum
    values, no additional/leaked properties. Mirrors
    quality/aircraft_window_stress_v1.schema.json exactly (kept in sync
    deliberately -- the JSON file is the readable reference; this function
    is the enforced authority, consistent with how
    quality/visual_escalation_router.py's semantic_validate_routing_decision
    already relates to visual_escalation_routing_decision.schema.json).

    A malformed action-branch field leakage (e.g. a stray "reason" that
    belongs to the outer RoutingDecision, not these params) is deliberately
    NOT this function's concern -- that stays
    quality.visual_escalation_router.semantic_validate_routing_decision's
    job on the outer decision dict. This function only looks inside the
    params object itself.
    """
    result = ShapeValidationResult()
    if not isinstance(params, dict):
        result.add(f"params must be an object, got {type(params).__name__}")
        return result

    missing = sorted(_REQUIRED_FIELD_SET - set(params))
    if missing:
        result.add(f"missing required fields: {missing}")

    leaked = sorted(set(params) - _REQUIRED_FIELD_SET)
    if leaked:
        result.add(f"params contains unsupported fields: {leaked}")

    for name in _REQUIRED_FIELDS:
        if name not in params:
            continue
        value = params[name]
        if not isinstance(value, str) or not value.strip():
            result.add(f"field '{name}' must be a non-empty string")

    if "template_id" in params and params["template_id"] not in SUPPORTED_TEMPLATE_IDS:
        result.add(
            f"unsupported template_id {params['template_id']!r}; "
            f"V1 supports only {sorted(SUPPORTED_TEMPLATE_IDS)}"
        )
    if "presentation" in params and params["presentation"] not in SUPPORTED_PRESENTATIONS:
        result.add(
            f"unsupported presentation {params['presentation']!r}; "
            f"V1 supports only {sorted(SUPPORTED_PRESENTATIONS)}"
        )
    if "evidence_source" in params and params["evidence_source"] not in SUPPORTED_EVIDENCE_SOURCES:
        result.add(
            f"unsupported evidence_source {params['evidence_source']!r}; "
            f"V1 supports only {sorted(SUPPORTED_EVIDENCE_SOURCES)}"
        )

    return result


def is_shape_valid(params: Any) -> bool:
    return validate_deterministic_explanation_params_shape(params).ok
