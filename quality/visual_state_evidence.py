from __future__ import annotations

from enum import Enum

from quality.visual_explanation_contract_v2 import ClaimDict
from quality.visual_state_observation import CanonicalVisionObservation


class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    ABSENT = "ABSENT"
    CONTRADICTED = "CONTRADICTED"


def resolve_claim_evidence(
    claim: ClaimDict,
    observation: CanonicalVisionObservation,
) -> EvidenceState:
    if not observation.subject_visible:
        return EvidenceState.ABSENT

    requirements = claim["visibility"]["requirements"]
    if requirements["not_occluded"] and observation.occluded:
        return EvidenceState.NOT_VERIFIED
    if requirements["sufficient_scale_for_mobile"] and not observation.sufficient_scale:
        return EvidenceState.NOT_VERIFIED
    if not observation.state_distinguishable or observation.observed_state is None:
        return EvidenceState.NOT_VERIFIED
    if observation.observed_state != claim["state"]:
        return EvidenceState.CONTRADICTED
    return EvidenceState.VERIFIED
