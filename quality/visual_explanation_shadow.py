from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from quality.visual_contrast_evaluator import ContrastEvaluation, EvaluationStatus, RelationResult
from quality.visual_explanation_contract_v2 import ValidationResult


class ShadowDecision(str, Enum):
    SHADOW_PASS = "SHADOW_PASS"
    WOULD_HOLD = "WOULD_HOLD"
    CONTRACT_INVALID = "CONTRACT_INVALID"
    EVALUATION_INCOMPLETE = "EVALUATION_INCOMPLETE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class ShadowEvaluation:
    decision: ShadowDecision
    production_decision: str
    reason: str


def aggregate_shadow_decision(
    production_decision: str,
    validation: ValidationResult,
    evaluations: list[ContrastEvaluation],
) -> ShadowEvaluation:
    """Shadow-only aggregation. Never rewrites or substitutes production_decision."""
    if not validation.ok:
        return ShadowEvaluation(ShadowDecision.CONTRACT_INVALID, production_decision, "; ".join(validation.errors))
    if not evaluations:
        return ShadowEvaluation(ShadowDecision.UNSUPPORTED, production_decision, "no V2.1 relation evaluations")
    if any(e.status == EvaluationStatus.INCOMPLETE for e in evaluations):
        return ShadowEvaluation(ShadowDecision.EVALUATION_INCOMPLETE, production_decision, "relation evaluation incomplete")
    if any(e.result == RelationResult.FAIL for e in evaluations):
        return ShadowEvaluation(ShadowDecision.WOULD_HOLD, production_decision, "required V2.1 CONTRAST failed")
    return ShadowEvaluation(ShadowDecision.SHADOW_PASS, production_decision, "all V2.1 shadow relations passed")
