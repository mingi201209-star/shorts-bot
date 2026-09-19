"""VisualPlanV2 gate + VisualPlan-vs-CandidateVisual matching.

Two responsibilities, kept separate:

1. evaluate_visual_plan_v2: is the PLAN itself well-formed (narration was
   decomposed into required components/state, not skipped straight to a
   search query)?
2. match_visual_to_plan: given what retrieval/generation actually returned
   (a CandidateVisualV2), does it satisfy the plan? This is where generic
   B-roll, cross-domain contamination, and "subject right but mechanism
   invisible" all get caught -- subject match alone is never sufficient.
"""

from __future__ import annotations

from typing import List

from quality_core_v2.schemas import CandidateVisualV2, VisualPlanV2, Verdict


def evaluate_visual_plan_v2(plan: VisualPlanV2) -> Verdict:
    if not plan.subject.strip():
        return Verdict(False, "VisualPlan has no subject", "visual_plan")
    if not plan.required_visible_components:
        return Verdict(
            False,
            "no required_visible_components -- narration was not decomposed "
            "into a VisualPlan, likely went straight to a search query",
            "visual_plan",
        )
    if not plan.required_observable_state:
        return Verdict(
            False,
            "no required_observable_state -- plan does not specify what "
            "observable phenomenon the visual must show",
            "visual_plan",
        )
    return Verdict(True, "plan has subject, required components, and observable state", "visual_plan")


def _contains_any(haystack_items: List[str], needle: str) -> bool:
    needle_l = needle.lower().strip()
    return any(needle_l in item.lower() or item.lower() in needle_l for item in haystack_items)


def match_visual_to_plan(plan: VisualPlanV2, visual: CandidateVisualV2) -> Verdict:
    """FAIL is the default. A visual must affirmatively satisfy the plan."""

    # 1. Forbidden visuals -- checked first and unconditionally. A subject
    #    match never overrides this (this is the exact "subject right but
    #    stock is a forbidden generic shot" case from the execution order).
    for forbidden in plan.forbidden_visuals:
        forbidden_l = forbidden.lower().strip()
        haystack = " ".join([visual.description] + visual.tags).lower()
        if forbidden_l and forbidden_l in haystack:
            return Verdict(
                False,
                f"visual matches a forbidden pattern: {forbidden!r} "
                f"(description={visual.description!r})",
                "visual_qa",
            )

    # 2. Cross-domain contamination: visible_components must not be empty,
    #    and every required component must appear among what the visual
    #    actually shows (subject-only match is not enough).
    missing_components = [
        c for c in plan.required_visible_components
        if not _contains_any(visual.visible_components, c)
    ]
    if missing_components:
        return Verdict(
            False,
            f"visual is missing required visible component(s): {missing_components} "
            f"(visual shows {visual.visible_components})",
            "visual_qa",
        )

    # 3. Observable phenomenon presence / mechanism visibility: the state
    #    the plan asked for must be present, not just the static subject.
    missing_states = [
        s for s in plan.required_observable_state
        if not _contains_any(visual.observable_state, s)
    ]
    if missing_states:
        return Verdict(
            False,
            f"visual does not show required observable state: {missing_states} "
            f"(subject present but phenomenon/mechanism is not visible)",
            "visual_qa",
        )

    # 4. Generic stock fallback used to paper over a real gap: a "stock"
    #    source with no observable_state at all is never an acceptable
    #    fallback, even if it happens to pass 2/3 above on an empty plan.
    if visual.source_type == "stock" and not visual.observable_state:
        return Verdict(
            False,
            "generic stock visual with no observable_state cannot satisfy "
            "a phenomenon requirement; fallback must prove the same "
            "meaning a different way (verified generated or grounded "
            "explanatory visual), not substitute a generic shot",
            "visual_qa",
        )

    return Verdict(
        True,
        f"visual satisfies required components {plan.required_visible_components} "
        f"and observable state {plan.required_observable_state}",
        "visual_qa",
    )
