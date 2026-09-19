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

import json
from typing import Any, Dict, List

from quality_core_v2.schemas import SceneV2, VisualPlanV2


def _first_nonempty(*candidates: Any) -> str:
    """Deterministic: first non-blank string across search_queries (in
    order) then subject. Never a generic placeholder -- an empty result
    means the plan itself carried no usable keyword, which is a
    fail-closed error, not something to paper over.
    """
    for candidate in candidates:
        items = candidate if isinstance(candidate, list) else [candidate]
        for item in items:
            text = str(item or "").strip()
            if text:
                return text
    return ""


def _augment_query_with_observable_state(base_query: str, states: List[str]) -> str:
    """Preserve observable-state meaning in the provider search query.

    Locked contract:
    - tokenize by whitespace only
    - exact case-insensitive token dedupe across base query + all states
    - no stemming/plural/synonym normalization
    - skip additional non-ASCII state tokens instead of leaking them into
      the provider query
    - preserve first-seen order and apply no added-token cap
    """
    base_tokens = base_query.split()
    seen = {token.lower() for token in base_tokens}
    added_tokens: List[str] = []
    skipped_non_ascii_token: List[str] = []

    for phrase in states:
        for raw_token in str(phrase or "").split():
            token = raw_token.strip()
            if not token:
                continue
            token_key = token.lower()
            if token_key in seen:
                continue
            seen.add(token_key)
            if not token.isascii():
                skipped_non_ascii_token.append(token)
                continue
            added_tokens.append(token)

    augmented_query = " ".join(base_tokens + added_tokens)
    print(
        "[V2_QUERY_AUGMENT] "
        + json.dumps(
            {
                "original_query": base_query,
                "augmented_query": augmented_query,
                "added_token_count": len(added_tokens),
                "skipped_non_ascii_token": skipped_non_ascii_token,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return augmented_query


def scene_v2_to_v1_item(scene: SceneV2, plan: VisualPlanV2) -> Dict[str, Any]:
    """Pure: map a validated (SceneV2, VisualPlanV2) pair to the exact
    dict shape video/video_engine.create_scene expects (text/keyword/
    visual_goal/visual_type). No network, no rendering.

    create_scene requires a non-empty `keyword`
    (video/video_engine.py:create_scene). Run 35430296847 (Golden E2E #2)
    crashed on scene 2 with an empty keyword because search_queries[0] can
    itself be a blank string even when the list is non-empty -- picking
    index 0 blindly let that through. Fixed here by taking the first
    genuinely non-blank entry across search_queries then subject, and
    failing closed (not a generic fallback string) if none exists.
    """
    keyword = _first_nonempty(plan.search_queries, plan.subject)
    if not keyword:
        raise ValueError(
            f"VisualPlanV2 for scene {scene.scene_index} has no usable keyword "
            f"(search_queries={plan.search_queries!r}, subject={plan.subject!r})"
        )
    keyword = _augment_query_with_observable_state(
        keyword, plan.required_observable_state
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
    *,
    generate_scenes_fn=None,
    render_final_video_fn=None,
    create_voice_fn=None,
    reset_final_visual_semantic_report_fn=None,
    validate_final_visual_semantic_qa_fn=None,
):
    """Impure orchestration: maps every (scene, plan) pair, then calls the
    real V1 generate_scenes()/render_final_video() unchanged. Injectable
    for offline testing (see downstream_test.py); defaults to the real
    functions when not injected.

    Reuses V1's existing quality.final_visual_semantic_qa as-is (no new QA
    implementation): reset before generate_scenes() runs (create_scene's
    own production hotfix lineage calls record_final_visual_scene() per
    scene as it goes), then validate right after. validate raises
    RuntimeError on FAIL, so render_final_video_fn is only ever reached on
    PASS -- no separate if/else needed.
    """
    if generate_scenes_fn is None:
        from main import generate_scenes as generate_scenes_fn
    if render_final_video_fn is None:
        from video.renderer import render_final_video as render_final_video_fn
    if reset_final_visual_semantic_report_fn is None:
        from quality.final_visual_semantic_qa import (
            reset_final_visual_semantic_report as reset_final_visual_semantic_report_fn,
        )
    if validate_final_visual_semantic_qa_fn is None:
        from quality.final_visual_semantic_qa import (
            validate_final_visual_semantic_qa as validate_final_visual_semantic_qa_fn,
        )

    items = [scene_v2_to_v1_item(s, p) for s, p in zip(scenes, plans)]
    reset_final_visual_semantic_report_fn()
    scene_clips = generate_scenes_fn(items)
    validate_final_visual_semantic_qa_fn(scenes)
    return render_final_video_fn(scene_clips)
