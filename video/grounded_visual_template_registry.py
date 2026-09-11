"""Registry: existing grounding state -> exact supported renderer capability.

This is a pure lookup. It never decides whether a scene should PRODUCE with a
given template -- that decision belongs to the eligibility adapter
(video/aircraft_window_stress_grounding.py, which decides WHAT may be drawn)
and ultimately the Bounded Visual Escalation router (which decides whether
NOW is the right attempt given failure state / ledger / budget). This module
only answers: "given eligibility params claiming template X, what does the
renderer for X actually provide and require?"

V1 registers exactly one template. No other template's migration, no stub or
TODO entries for future templates.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundedVisualTemplateCapability:
    template_id: str
    # Escalation-level relation shape this template always produces.
    presentation: str
    # The existing V2.1 ComparisonSegmentDict.presentation this template's
    # renderer always emits -- reusing that contract unchanged (task
    # section 6), never inventing a new comparison shape.
    comparison_presentation: str
    # A CONTRAST relation always has exactly two members (V2.1 authority).
    required_claim_count: int
    # Field names (on the eligibility params dict) that feed
    # param_signature construction -- documents the stable identity inputs
    # without embedding the signature logic itself here (that is Phase 4).
    signature_inputs: tuple[str, ...]


_REGISTRY: dict[str, GroundedVisualTemplateCapability] = {
    "AIRCRAFT_WINDOW_STRESS_V1": GroundedVisualTemplateCapability(
        template_id="AIRCRAFT_WINDOW_STRESS_V1",
        presentation="CONTRAST",
        comparison_presentation="SPLIT_SCREEN",
        required_claim_count=2,
        signature_inputs=(
            "template_id",
            "canonical_subject_id",
            "owned_claim_id",
            "presentation",
            "grounding_fingerprint",
        ),
    ),
}


def find_grounded_visual_template(eligibility_params):
    """eligibility_params is the dict returned by an eligibility adapter such
    as supports_aircraft_window_stress_from_grounding(), or None/falsy.
    Returns the matching GroundedVisualTemplateCapability, or None.
    """
    if not eligibility_params:
        return None
    template_id = str((eligibility_params or {}).get("template_id") or "")
    return _REGISTRY.get(template_id)


def known_template_ids():
    return frozenset(_REGISTRY)
