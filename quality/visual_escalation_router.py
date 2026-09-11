from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, TypedDict


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    """No authority is wired for this gate yet. Fail-closed: never counts toward
    is_hard_pass(), and must never be defaulted to PASS by an adapter that doesn't
    know how to compute it."""


class FailureLayer(str, Enum):
    GROUNDING = "GROUNDING"
    CLAIM = "CLAIM"
    VISUAL_PLANNING = "VISUAL_PLANNING"
    ASSET_ACQUISITION = "ASSET_ACQUISITION"
    RENDER = "RENDER"
    QUALITY = "QUALITY"


class EscalationMethod(str, Enum):
    REUSE_VERIFIED = "REUSE_VERIFIED"
    STOCK_RETRIEVAL = "STOCK_RETRIEVAL"
    DETERMINISTIC_EXPLANATION = "DETERMINISTIC_EXPLANATION"
    AI_EXPLANATORY_IMAGE = "AI_EXPLANATORY_IMAGE"
    SAFE_MINIMAL_PRESENTATION = "SAFE_MINIMAL_PRESENTATION"


class UpstreamTarget(str, Enum):
    GROUNDING = "GROUNDING"
    CLAIM_PLANNING = "CLAIM_PLANNING"
    WRITER = "WRITER"


class UpstreamResult(str, Enum):
    RETURNED_RESOLVED = "RETURNED_RESOLVED"
    RETURNED_UNRESOLVED = "RETURNED_UNRESOLVED"


class TerminalState(str, Enum):
    HUMAN_HOLD = "HUMAN_HOLD"


class RoutingAction(str, Enum):
    PRODUCE = "PRODUCE"
    RETURN_UPSTREAM = "RETURN_UPSTREAM"
    TERMINATE = "TERMINATE"


class RequirementDict(TypedDict):
    id: str
    required: bool
    present: bool


class RequiredClaimStateDict(TypedDict):
    status: GateStatus
    requirements: list[RequirementDict]


class HardGatesDict(TypedDict):
    fact_safety: GateStatus
    subject_identity: GateStatus
    required_claim_state: RequiredClaimStateDict


class SoftGatesDict(TypedDict):
    explanation_match: float
    visual_quality: float
    explanatory_diversity: float


class FailureDict(TypedDict, total=False):
    reason: str
    layer: FailureLayer
    details: list[str]


class AttemptDict(TypedDict, total=False):
    method: EscalationMethod
    param_signature: str
    asset_id: str | None
    provider: str
    cost_usd: float
    result: Literal["PASS", "FAIL"]
    failure_reason: str | None


class BudgetDict(TypedDict):
    attempts_remaining: int
    api_calls_remaining: int
    cost_usd_remaining: float
    upstream_returns_remaining: int


class UpstreamReturnDict(TypedDict):
    target: UpstreamTarget
    reason: str
    return_index: int
    result: UpstreamResult


class SceneEscalationLedgerDict(TypedDict, total=False):
    scene_id: int
    claim_id: str
    attempt_index: int
    hard_gates: HardGatesDict
    soft_gates: SoftGatesDict
    failure: FailureDict | None
    attempts: list[AttemptDict]
    budget: BudgetDict
    upstream_history: list[UpstreamReturnDict]


class RoutingDecisionDict(TypedDict, total=False):
    action: RoutingAction
    method: EscalationMethod
    param_signature: str
    reason: str
    target: UpstreamTarget
    terminal_state: TerminalState
    terminal_reason: str


class RoutingDecisionError(Exception):
    pass


@dataclass
class RoutingValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)


# Fields exclusive to each action branch, mirroring the discriminated union declared
# in visual_escalation_routing_decision.schema.json. "action" itself is excluded —
# every decision has it.
_PRODUCE_FIELDS = frozenset({"method", "param_signature", "reason"})
_RETURN_UPSTREAM_FIELDS = frozenset({"target", "reason"})
_TERMINATE_FIELDS = frozenset({"terminal_state", "terminal_reason"})

_ACTION_FIELDS: dict[RoutingAction, frozenset[str]] = {
    RoutingAction.PRODUCE: _PRODUCE_FIELDS,
    RoutingAction.RETURN_UPSTREAM: _RETURN_UPSTREAM_FIELDS,
    RoutingAction.TERMINATE: _TERMINATE_FIELDS,
}

_ALL_ACTION_FIELDS: frozenset[str] = _PRODUCE_FIELDS | _RETURN_UPSTREAM_FIELDS | _TERMINATE_FIELDS


def semantic_validate_routing_decision(decision: RoutingDecisionDict) -> RoutingValidationResult:
    """Shape validation only (JSON Schema is authority for that). This checks that
    exactly the fields for `action` are present and no fields from another branch
    leaked in — including a bare "reason" leaking into a TERMINATE decision, which
    is legitimate on PRODUCE/RETURN_UPSTREAM but not on TERMINATE (that branch uses
    terminal_reason instead). A plain per-action allowlist, computed fresh from
    _ALL_ACTION_FIELDS minus the current action's own fields, catches this without
    any blanket exemption for fields that happen to be shared by *some* branches.
    """
    result = RoutingValidationResult()
    action = decision.get("action")
    if action not in _ACTION_FIELDS:
        result.add(f"unknown or missing action: {action!r}")
        return result

    required = _ACTION_FIELDS[action]
    missing = sorted(f for f in required if f not in decision)
    if missing:
        result.add(f"action '{action}' missing required fields: {missing}")

    foreign_fields = _ALL_ACTION_FIELDS - required
    leaked = sorted(f for f in foreign_fields if f in decision)
    if leaked:
        result.add(f"action '{action}' contains fields from another branch: {leaked}")

    return result


def is_hard_pass(ledger: SceneEscalationLedgerDict) -> bool:
    """presence/coverage gates only. Never influenced by soft_gates or remaining
    budget — that boundary is the V1 invariant this function exists to enforce
    in code, not just in the schema description. NOT_EVALUATED gates (fact_safety,
    subject_identity in V1) correctly fail this check rather than being treated as
    passing, since they compare unequal to GateStatus.PASS.
    """
    gates = ledger["hard_gates"]
    return (
        gates["fact_safety"] == GateStatus.PASS
        and gates["subject_identity"] == GateStatus.PASS
        and gates["required_claim_state"]["status"] == GateStatus.PASS
    )
