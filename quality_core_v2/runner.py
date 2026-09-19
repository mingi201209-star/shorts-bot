"""V2 pipeline entry point, called from main.py only when
ENABLE_QUALITY_CORE_V2=1. Does not touch any V1 code path.

Scope of this phase: Candidate -> Grounding -> ScriptPlan -> VisualPlan,
each validated by the deterministic gates the replay suite already
regresses. Downstream integration with the existing create_scene/
renderer/TTS/subtitle/export pipeline is the next phase (not done here,
per the usage fuse: adapters + flag wiring + replay + one Golden E2E is
the current scope, and real rendering needs the adapters proven first).
"""

from __future__ import annotations

from quality_core_v2.adapters.explorer_adapter import propose_candidate_with_bounded_rewrite
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
    candidate, verdict = propose_candidate_with_bounded_rewrite(topic_direction, recent_topics or [])
    if candidate is None:
        raise RuntimeError(f"V2 Candidate Loop: no Candidate passed the gate ({verdict.reason})")

    scenes = parse_writer_response(call_writer(candidate))
    script_verdict = evaluate_script_plan_v2(scenes)
    if not script_verdict.passed:
        raise RuntimeError(f"V2 ScriptPlan rejected: {script_verdict.reason}")

    plans = []
    for scene in scenes:
        plan = parse_visual_plan_response(call_visual_planner(scene), scene.scene_index)
        plan_verdict = evaluate_visual_plan_v2(plan)
        if not plan_verdict.passed:
            raise RuntimeError(f"V2 VisualPlan rejected for scene {scene.scene_index}: {plan_verdict.reason}")
        plans.append(plan)

    # Retrieval/classification against each plan (visual_qa gate) is not
    # re-run here: create_scene() below does its own provider search from
    # the mapped keyword. See quality_core_v2/downstream.py's module
    # docstring for the known gap this leaves (plan-quality gate, not a
    # guarantee of the exact clip create_scene's own search will pick).
    return render_v2_pipeline(scenes, plans)
