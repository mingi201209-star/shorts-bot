"""ScriptPlanV2 gate: claim ownership + no adjacent semantic duplication.

Each Scene owns exactly one piece of information (owned_claim_id). Two
checks, both deterministic:

1. No two scenes share the same owned_claim_id (claim ownership).
2. No two ADJACENT scenes carry the same new_information content (adjacent
   semantic duplication) -- this is the run 612/613 class of bug: Scene 1
   silently restates the payoff's claim, so retention_structure's V1
   duplicate check crashes the run with no recovery. V2 catches it here,
   before a Writer ever produces prose, as a plan-level structural check.
"""

from __future__ import annotations

import re
from typing import List

from quality_core_v2.schemas import CandidateV2, SceneV2, Verdict

_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _tokens(text: str) -> set:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)

# Two scenes' new_information are considered duplicates above this overlap.
ADJACENT_DUPLICATE_THRESHOLD = 0.6

_REQUIRED_CAUSAL_ROLES = [
    "phenomenon",
    "why_question",
    "mechanism_input",
    "mechanism_change",
    "observable_result",
    "payoff",
]

_GENERIC_PAYOFF_RE = re.compile(
    r"(안전성과?\s*성능|긍정적(?:인)?\s*영향|중요한\s*역할|"
    r"효율\s*(?:향상|개선)|기동성|안정성).*"
    r"(높|향상|개선|긍정|도움|역할)|"
    r"(improve|benefit|important\s+role|performance|comfort)",
    re.IGNORECASE,
)

_OUT_OF_CANDIDATE_TERMS = {
    "승객", "객실", "편안", "passenger", "passengers", "cabin", "comfort",
}


def _candidate_text(candidate: CandidateV2) -> str:
    return " ".join([
        candidate.topic,
        candidate.concrete_subject,
        candidate.observable_phenomenon,
        candidate.core_question,
        candidate.mechanism,
        candidate.reveal,
        candidate.canonical_subject,
        *candidate.visual_proof,
    ]).lower()


def evaluate_script_plan_v2(
    scenes: List[SceneV2],
    candidate: CandidateV2 | None = None,
) -> Verdict:
    if not scenes:
        return Verdict(False, "empty scene list", "script_plan")

    seen_claims = {}
    for scene in scenes:
        if scene.owned_claim_id in seen_claims:
            other = seen_claims[scene.owned_claim_id]
            return Verdict(
                False,
                f"scene {scene.scene_index} and scene {other} share "
                f"owned_claim_id {scene.owned_claim_id!r}",
                "script_plan",
            )
        seen_claims[scene.owned_claim_id] = scene.scene_index

    ordered = sorted(scenes, key=lambda s: s.scene_index)

    if candidate is not None:
        roles = [str(scene.causal_role or "").strip() for scene in ordered]
        if len(ordered) != 6 or roles != _REQUIRED_CAUSAL_ROLES:
            return Verdict(
                False,
                "Candidate-bound ScriptPlan must use exactly six causal roles "
                f"{_REQUIRED_CAUSAL_ROLES!r}; got {roles!r}",
                "script_plan",
            )
        first = ordered[0].narration.strip()
        if not first or first.endswith("?") or first.endswith("？"):
            return Verdict(
                False,
                "Scene 1 must state the observable phenomenon directly, not open with a question",
                "script_plan",
            )

        candidate_text = _candidate_text(candidate)
        for scene in ordered:
            scene_text = " ".join([
                scene.narration,
                scene.new_information,
                scene.visual_requirement,
            ]).lower()
            novel_drift = sorted(
                term
                for term in _OUT_OF_CANDIDATE_TERMS
                if term in scene_text and term not in candidate_text
            )
            if novel_drift:
                return Verdict(
                    False,
                    "out-of-Candidate concept introduced by ScriptPlan: "
                    f"{novel_drift}",
                    "script_plan",
                )

    payoff_scenes = [scene for scene in ordered if scene.causal_role == "payoff"]
    if payoff_scenes:
        payoff = payoff_scenes[-1]
        payoff_text = f"{payoff.narration} {payoff.new_information}"
        if _GENERIC_PAYOFF_RE.search(payoff_text):
            return Verdict(
                False,
                f"generic benefit payoff instead of concrete mechanism: {payoff.narration!r}",
                "script_plan",
            )

    for prev, curr in zip(ordered, ordered[1:]):
        overlap = _jaccard(_tokens(prev.new_information), _tokens(curr.new_information))
        if overlap >= ADJACENT_DUPLICATE_THRESHOLD:
            return Verdict(
                False,
                f"scene {curr.scene_index} repeats scene {prev.scene_index}'s "
                f"new_information (token overlap {overlap:.2f} >= "
                f"{ADJACENT_DUPLICATE_THRESHOLD:.2f}): {curr.new_information!r}",
                "script_plan",
            )

    return Verdict(True, f"{len(scenes)} scenes, each owns a distinct claim", "script_plan")
