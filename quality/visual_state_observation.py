from __future__ import annotations

from dataclasses import dataclass

from quality.visual_state_registry import SubjectStateRegistry


@dataclass(frozen=True)
class RawVisionObservation:
    subject_visible: bool
    raw_state: str | None
    state_distinguishable: bool
    occluded: bool = False
    sufficient_scale: bool = True


@dataclass(frozen=True)
class CanonicalVisionObservation:
    subject_visible: bool
    observed_state: str | None
    state_distinguishable: bool
    occluded: bool = False
    sufficient_scale: bool = True
    diagnostic: str | None = None


def normalize_vision_observation(
    subject: str,
    raw: RawVisionObservation,
    registry: SubjectStateRegistry,
) -> CanonicalVisionObservation:
    if not raw.subject_visible:
        return CanonicalVisionObservation(
            subject_visible=False,
            observed_state=None,
            state_distinguishable=False,
            occluded=raw.occluded,
            sufficient_scale=raw.sufficient_scale,
        )
    if not raw.state_distinguishable or raw.raw_state is None:
        return CanonicalVisionObservation(
            subject_visible=True,
            observed_state=None,
            state_distinguishable=False,
            occluded=raw.occluded,
            sufficient_scale=raw.sufficient_scale,
        )
    canonical = registry.canonicalize_for_evidence(subject, raw.raw_state)
    if canonical is None:
        return CanonicalVisionObservation(
            subject_visible=True,
            observed_state=None,
            state_distinguishable=False,
            occluded=raw.occluded,
            sufficient_scale=raw.sufficient_scale,
            diagnostic=f"unknown vision state seen: {raw.raw_state}",
        )
    return CanonicalVisionObservation(
        subject_visible=True,
        observed_state=canonical,
        state_distinguishable=True,
        occluded=raw.occluded,
        sufficient_scale=raw.sufficient_scale,
    )
