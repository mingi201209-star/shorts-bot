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

from quality_core_v2.schemas import SceneV2, Verdict

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


def evaluate_script_plan_v2(scenes: List[SceneV2]) -> Verdict:
    if not scenes:
        return Verdict(False, "empty scene list", "script_plan")

    ordered = sorted(scenes, key=lambda s: s.scene_index)

    # Preserve the original failure-specific checks first so a known duplicate
    # still reports its real cause instead of being masked by a later
    # progression-shape error.
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

    required_roles = [
        "phenomenon",
        "why_question",
        "mechanism_input",
        "mechanism_change",
        "observable_result",
        "payoff",
    ]
    actual_roles = [str(scene.causal_role or "").strip() for scene in ordered]
    if len(ordered) != len(required_roles) or actual_roles != required_roles:
        return Verdict(
            False,
            "causal progression must be exactly "
            f"{required_roles!r}; got {actual_roles!r}",
            "script_plan",
        )

    first = ordered[0].narration.strip()
    if not first or first.endswith("?") or first.endswith("？"):
        return Verdict(
            False,
            "scene 1 must directly state the observable phenomenon, not open with a question",
            "script_plan",
        )

    payoff_text = " ".join(
        [ordered[-1].narration, ordered[-1].new_information]
    ).lower()
    generic_payoff_markers = (
        "안전성과 성능",
        "안전성에 긍정",
        "성능에 긍정",
        "긍정적인 영향",
        "효율을 높",
        "효율 향상",
        "도움이 됩니다",
        "도움을 줍니다",
        "중요한 역할",
        "최적화",
    )
    if any(marker in payoff_text for marker in generic_payoff_markers):
        return Verdict(
            False,
            "payoff collapsed into a generic benefit instead of explaining the mechanism: "
            f"{ordered[-1].narration!r}",
            "script_plan",
        )

    return Verdict(True, f"{len(scenes)} scenes, each owns a distinct claim", "script_plan")
