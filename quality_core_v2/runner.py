"""Clean V2 pipeline entry point.

Candidate -> ScriptPlan -> VisualPlan -> exact visual acquisition/QA -> render.

The accepted visual identity is carried all the way into rendering.  V2 never
hands a keyword to V1 create_scene() for a second independent search.
"""

from __future__ import annotations

from quality_core_v2.adapters.explorer_adapter import propose_candidate_with_bounded_rewrite
from quality_core_v2.adapters.retrieval_adapter import select_visual_for_scene
from quality_core_v2.adapters.writer_adapter import (
    call_visual_planner,
    call_writer,
    parse_visual_plan_response,
    parse_writer_response,
)
from quality_core_v2.downstream import render_v2_pipeline
from quality_core_v2.script_plan import evaluate_script_plan_v2
from quality_core_v2.visual_plan import evaluate_visual_plan_v2


def run_v2_pipeline(topic_direction: str = "", recent_topics=None):
    candidate, verdict = propose_candidate_with_bounded_rewrite(
        topic_direction,
        recent_topics or [],
    )
    if candidate is None:
        raise RuntimeError(
            f"V2 Candidate Loop: no Candidate passed the gate ({verdict.reason})"
        )

    scenes = parse_writer_response(call_writer(candidate))
    script_verdict = evaluate_script_plan_v2(scenes)
    if not script_verdict.passed:
        raise RuntimeError(f"V2 ScriptPlan rejected: {script_verdict.reason}")

    plans = []
    selected_visuals = []

    for scene in scenes:
        plan = parse_visual_plan_response(
            call_visual_planner(scene),
            scene.scene_index,
        )
        plan_verdict = evaluate_visual_plan_v2(plan)
        if not plan_verdict.passed:
            raise RuntimeError(
                f"V2 VisualPlan rejected for scene {scene.scene_index}: "
                f"{plan_verdict.reason}"
            )

        visual, visual_verdict = select_visual_for_scene(scene, plan)
        if visual is None:
            raise RuntimeError(
                f"V2 visual acquisition rejected for scene {scene.scene_index}: "
                f"{visual_verdict.reason}"
            )

        plans.append(plan)
        selected_visuals.append(visual)

    return render_v2_pipeline(scenes, plans, selected_visuals)
