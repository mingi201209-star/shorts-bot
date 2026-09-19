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

import re
from typing import List

from quality_core_v2.schemas import CandidateV2, CandidateVisualV2, VisualPlanV2, Verdict


_QUERY_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STATE_STOPWORDS = {
    "visible", "visibly", "clear", "clearly", "actual", "state", "show",
    "showing", "shown", "in", "on", "of", "the", "a", "an", "during",
    "under", "with", "and", "aircraft", "airplane", "wing", "main",
    "flight", "view", "close", "closeup",
}


_IDENTITY_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
_IDENTITY_GENERIC_TERMS = {
    "aircraft", "airplane", "plane", "aviation", "vehicle", "main",
    "system", "structure", "component", "part", "object", "subject",
    "flight", "flying", "scene", "view", "detail", "closeup",
    "비행기", "항공기", "구조", "시스템", "부품", "대상", "장면",
}
_IDENTITY_STATE_TERMS = {
    "visible", "upward", "elastic", "flex", "flexing", "bend", "bending",
    "deform", "deformation", "deflection", "load", "loaded", "aerodynamic",
    "force", "forces", "lift", "drag", "airflow", "pressure", "during",
    "under", "with", "and", "of", "the",
    "보이는", "위로", "탄성", "변형", "하중", "양력", "항력", "공기",
}


def _identity_tokens(text: str) -> set:
    return {
        token.lower()
        for token in _IDENTITY_TOKEN_RE.findall(str(text or ""))
        if token.lower() not in _IDENTITY_GENERIC_TERMS
        and token.lower() not in _IDENTITY_STATE_TERMS
        and len(token) >= 2
    }


def _candidate_identity_tokens(candidate: CandidateV2) -> set:
    canonical = _identity_tokens(candidate.canonical_subject)
    concrete = _identity_tokens(candidate.concrete_subject)
    # Intersection is too brittle when one field is more specific than the
    # other. Union is safe because the gate only requires one concrete identity
    # token to survive into the plan.
    return canonical | concrete


def _plan_identity_tokens(plan: VisualPlanV2) -> set:
    values = [
        plan.subject,
        *plan.required_visible_components,
        *plan.search_queries,
    ]
    tokens = set()
    for value in values:
        tokens |= _identity_tokens(value)
    return tokens


def _candidate_identity_bound(plan: VisualPlanV2, candidate: CandidateV2) -> bool:
    required = _candidate_identity_tokens(candidate)
    if not required:
        return True
    return bool(required & _plan_identity_tokens(plan))


def _semantic_query_terms(text: str) -> set:
    terms = set()
    for token in _QUERY_TOKEN_RE.findall(str(text or "").lower()):
        if token in _STATE_STOPWORDS:
            continue
        if token.startswith(("bend", "flex", "deform", "deflect")):
            terms.add("flex_bend")
        elif token.startswith(("twist", "torsion")):
            terms.add("twist_torsion")
        elif token.startswith(("vibr", "flutter")):
            terms.add("vibration_flutter")
        elif token.startswith(("deploy", "extend", "retract")):
            terms.add("deployment")
        else:
            terms.add(token)
    return terms


def _state_bearing_query_exists(plan: VisualPlanV2) -> bool:
    state_terms = set()
    for state in plan.required_observable_state:
        state_terms |= _semantic_query_terms(state)
    if not state_terms:
        return False
    for query in plan.search_queries:
        query_terms = _semantic_query_terms(query)
        if query_terms & state_terms:
            return True
    return False


def evaluate_visual_plan_v2(
    plan: VisualPlanV2,
    candidate: CandidateV2 | None = None,
) -> Verdict:
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
    if not plan.search_queries:
        return Verdict(
            False,
            "no search_queries -- the observable state cannot survive into retrieval",
            "visual_plan",
        )
    if candidate is not None and not _candidate_identity_bound(plan, candidate):
        return Verdict(
            False,
            "VisualPlan drifted away from Candidate canonical subject; "
            f"canonical_subject={candidate.canonical_subject!r} "
            f"concrete_subject={candidate.concrete_subject!r} "
            f"plan_subject={plan.subject!r} components={plan.required_visible_components!r} "
            f"queries={plan.search_queries!r}",
            "visual_plan",
        )
    if not _state_bearing_query_exists(plan):
        return Verdict(
            False,
            "search_queries lost the required observable phenomenon; "
            f"states={plan.required_observable_state!r} queries={plan.search_queries!r}",
            "visual_plan",
        )
    return Verdict(
        True,
        "plan has subject, required components, observable state, and a state-bearing search query",
        "visual_plan",
    )


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
