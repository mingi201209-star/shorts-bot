"""Downstream handoff: validated V2 objects -> existing V1
create_scene/renderer/TTS/subtitle/export, called as-is (not
copied/rewritten -- see AGENTS.md / execution order section 0).

Known limitation, not hidden: main.py's create_scene() does its OWN
provider search from `keyword` internally (video/video_engine.py); it does
not accept a pre-fetched/pre-classified visual. So the VisualQA V2 pass
that quality_core_v2.visual_qa performs before this handoff is a plan-
quality gate (is the keyword/plan good enough to search with), not a
guarantee that create_scene's own internal search will pick the exact
clip that was classified. Closing that gap (passing a pre-fetched visual
through to create_scene) would mean changing create_scene's interface,
which is explicitly out of scope for this phase.
"""

from __future__ import annotations

from typing import Any, Dict, List

from quality_core_v2.schemas import SceneV2, VisualPlanV2


def scene_v2_to_v1_item(scene: SceneV2, plan: VisualPlanV2) -> Dict[str, Any]:
    """Pure: map a validated (SceneV2, VisualPlanV2) pair to the exact
    dict shape video/video_engine.create_scene expects (text/keyword/
    visual_goal/visual_type). No network, no rendering.
    """
    keyword = (plan.search_queries or [plan.subject])[0]
    visual_goal = ", ".join(plan.required_observable_state) or scene.narration
    visual_type = (
        "ai_generated" if plan.preferred_source_type == "generated" else "real_world_broll"
    )
    return {
        "text": scene.narration,
        "keyword": keyword,
        "visual_goal": visual_goal,
        "visual_type": visual_type,
    }


def render_v2_pipeline(
    scenes: List[SceneV2],
    plans: List[VisualPlanV2],
    *,
    generate_scenes_fn=None,
    render_final_video_fn=None,
    create_voice_fn=None,
):
    """Impure orchestration: maps every (scene, plan) pair, then calls the
    real V1 generate_scenes()/render_final_video() unchanged. Injectable
    for offline testing (see downstream_test.py); defaults to the real
    functions when not injected.
    """
    if generate_scenes_fn is None:
        from main import generate_scenes as generate_scenes_fn
    if render_final_video_fn is None:
        from video.renderer import render_final_video as render_final_video_fn

    items = [scene_v2_to_v1_item(s, p) for s, p in zip(scenes, plans)]
    scene_clips = generate_scenes_fn(items)
    return render_final_video_fn(scene_clips)
