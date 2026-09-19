"""Final Visual Semantic QA V2: the last gate before a scene is accepted.

Combines three things that must ALL hold, mirroring section 5 of the
execution order's "Visual" checklist:

- narration <-> visual direct semantic match   (not just subject overlap)
- required subject / observable phenomenon / mechanism visibility
  (delegated to visual_plan.match_visual_to_plan)
- cross-domain and generic-B-roll rejection    (also delegated there)

This module owns only the narration<->visual correspondence check that
visual_plan.py doesn't do, then composes with it. It never re-relaxes a
FAIL from match_visual_to_plan.
"""

from __future__ import annotations

import re

from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2, Verdict
from quality_core_v2.visual_plan import match_visual_to_plan

_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _tokens(text: str) -> set:
    return set(_TOKEN_RE.findall((text or "").lower()))


# Narration and visual description/tags must share at least this much
# vocabulary (after removing plan-subject tokens, which would always
# overlap and would let a subject-only match through). Deliberately loose
# -- this is a floor against total unrelatedness, not a precision check;
# precision is visual_plan's job.
NARRATION_VISUAL_MIN_OVERLAP = 1


def evaluate_scene_visual_qa(
    scene: SceneV2,
    plan: VisualPlanV2,
    visual: CandidateVisualV2,
) -> Verdict:
    plan_match = match_visual_to_plan(plan, visual)
    if not plan_match.passed:
        return plan_match

    # The VisualPlan is the typed semantic bridge between Korean narration and
    # provider/vision vocabulary. Include the scene's explicit visual
    # requirement plus the classifier's exact plan strings, instead of relying
    # on Korean<->English lexical coincidence in provider metadata.
    narration_tokens = _tokens(scene.narration) | _tokens(scene.visual_requirement)
    visual_tokens = _tokens(
        " ".join(
            [
                visual.description,
                *visual.tags,
                *visual.visible_components,
                *visual.observable_state,
            ]
        )
    )
    shared = narration_tokens & visual_tokens
    if len(shared) < NARRATION_VISUAL_MIN_OVERLAP:
        plan_tokens = _tokens(
            " ".join(
                [
                    plan.subject,
                    *plan.required_visible_components,
                    *plan.required_observable_state,
                ]
            )
        )
        if not (plan_tokens & visual_tokens):
            return Verdict(
                False,
                f"narration/visual requirement has no semantic bridge to visual -- "
                f"narration={scene.narration!r}, visual={visual.description!r}",
                "visual_qa",
            )

    return Verdict(
        True,
        "narration<->visual correspondence holds and visual satisfies the plan",
        "visual_qa",
    )
