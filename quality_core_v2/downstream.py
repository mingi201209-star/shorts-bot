"""Clean V2 downstream handoff.

Invariant:
    the exact CandidateVisualV2 accepted by V2 Visual QA is the asset rendered.

Unlike the old handoff, this module never calls V1 create_scene(), because that
function performs its own keyword search and can silently replace the asset V2
actually validated.  V1 remains untouched; V2 uses a dedicated exact-asset
renderer that reuses V1's low-level media/TTS/subtitle primitives.
"""

from __future__ import annotations

from typing import Any, Dict, List

from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2
from quality_core_v2.visual_qa import evaluate_scene_visual_qa


def _first_nonempty(*candidates: Any) -> str:
    for candidate in candidates:
        items = candidate if isinstance(candidate, list) else [candidate]
        for item in items:
            text = str(item or "").strip()
            if text:
                return text
    return ""


def scene_v2_to_v1_item(scene: SceneV2, plan: VisualPlanV2) -> Dict[str, Any]:
    """Compatibility/debug projection only. It is no longer used to acquire
    or render V2 visuals, so a keyword can never replace an accepted asset.
    """
    keyword = _first_nonempty(plan.search_queries, plan.subject)
    if not keyword:
        raise ValueError(
            f"VisualPlanV2 for scene {scene.scene_index} has no usable keyword "
            f"(search_queries={plan.search_queries!r}, subject={plan.subject!r})"
        )
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
    selected_visuals: List[CandidateVisualV2],
    *,
    generate_selected_scenes_fn=None,
    render_final_video_fn=None,
):
    """Render only visuals already accepted for the corresponding plan."""
    if not (len(scenes) == len(plans) == len(selected_visuals)):
        raise ValueError(
            "V2 downstream inputs must align: "
            f"{len(scenes)}/{len(plans)}/{len(selected_visuals)}"
        )

    # Recheck the pure semantic contract at the boundary.  No API call and no
    # score relaxation: a malformed/mismatched asset cannot enter rendering.
    for scene, plan, visual in zip(scenes, plans, selected_visuals):
        if not visual.media_url.strip():
            raise RuntimeError(
                f"V2 selected visual for scene {scene.scene_index} has no exact media_url"
            )
        verdict = evaluate_scene_visual_qa(scene, plan, visual)
        if not verdict.passed:
            raise RuntimeError(
                f"V2 selected visual rejected before render for scene "
                f"{scene.scene_index}: {verdict.reason}"
            )

    if generate_selected_scenes_fn is None:
        from quality_core_v2.selected_scene_renderer import (
            generate_selected_scenes as generate_selected_scenes_fn,
        )
    if render_final_video_fn is None:
        from video.renderer import render_final_video as render_final_video_fn

    scene_clips = generate_selected_scenes_fn(scenes, plans, selected_visuals)
    return render_final_video_fn(scene_clips)
