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

import json
from dataclasses import asdict
from pathlib import Path

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


TRACE_PATH = Path("v2_pipeline_trace.json")


def _write_pipeline_trace(candidate=None, scenes=None, plans=None, failure=None):
    payload = {
        "candidate": asdict(candidate) if candidate is not None else None,
        "scenes": [asdict(scene) for scene in (scenes or [])],
        "plans": [asdict(plan) for plan in (plans or [])],
        "failure": failure,
    }
    TRACE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_v2_pipeline(topic_direction: str = "", recent_topics=None):
    candidate = None
    scenes = []
    plans = []
    try:
        candidate, verdict = propose_candidate_with_bounded_rewrite(
            topic_direction, recent_topics or []
        )
        _write_pipeline_trace(candidate=candidate, scenes=scenes, plans=plans)
        if candidate is None:
            raise RuntimeError(
                f"V2 Candidate Loop: no Candidate passed the gate ({verdict.reason})"
            )

        scenes = parse_writer_response(call_writer(candidate))
        _write_pipeline_trace(candidate=candidate, scenes=scenes, plans=plans)
        script_verdict = evaluate_script_plan_v2(scenes, candidate=candidate)
        if not script_verdict.passed:
            raise RuntimeError(f"V2 ScriptPlan rejected: {script_verdict.reason}")

        for scene in scenes:
            plan = parse_visual_plan_response(
                call_visual_planner(scene, candidate=candidate),
                scene.scene_index,
            )
            plans.append(plan)
            _write_pipeline_trace(candidate=candidate, scenes=scenes, plans=plans)
            plan_verdict = evaluate_visual_plan_v2(plan, candidate=candidate)
            if not plan_verdict.passed:
                raise RuntimeError(
                    f"V2 VisualPlan rejected for scene {scene.scene_index}: "
                    f"{plan_verdict.reason}"
                )

        return render_v2_pipeline(scenes, plans)
    except Exception as exc:
        _write_pipeline_trace(
            candidate=candidate,
            scenes=scenes,
            plans=plans,
            failure={
                "type": type(exc).__name__,
                "message": str(exc),
            },
        )
        raise
