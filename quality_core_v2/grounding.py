"""GroundingV2 gate: canonical subject identity, fail-closed.

Mirrors the one narrow invariant quality/canonical_subject_grounding.py
(V1) owns -- a physical subject must have a resolved identity before
downstream reasoning proceeds -- but as a clean, independent V2
implementation with no import from the V1 module or the hotfix chain.
"""

from __future__ import annotations

from quality_core_v2.schemas import GroundingV2, Verdict

IDENTITY_CONFIDENCE_MIN = 0.80

_RESOLVED_KINDS = {"physical_entity", "non_physical_concept"}


def evaluate_grounding_v2(grounding: GroundingV2) -> Verdict:
    if grounding.subject_kind not in _RESOLVED_KINDS:
        return Verdict(
            False,
            f"subject_kind is unresolved ({grounding.subject_kind!r}); "
            "fail-closed rather than guessing physical vs non-physical",
            "grounding",
        )

    if grounding.identity_confidence < IDENTITY_CONFIDENCE_MIN:
        return Verdict(
            False,
            f"identity_confidence {grounding.identity_confidence:.2f} below "
            f"minimum {IDENTITY_CONFIDENCE_MIN:.2f}",
            "grounding",
        )

    if not grounding.evidence_refs:
        return Verdict(False, "no evidence_refs; identity is not grounded", "grounding")

    return Verdict(True, f"subject_kind={grounding.subject_kind}, grounded", "grounding")
