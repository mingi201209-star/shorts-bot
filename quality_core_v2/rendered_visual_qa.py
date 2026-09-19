"""Strict QA for the exact 9:16 clip Clean V2 will actually render."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from quality_core_v2.schemas import CandidateVisualV2, SceneV2, Verdict, VisualPlanV2
from quality_core_v2.visual_qa import evaluate_scene_visual_qa

MODEL = os.environ.get("V3_V2_RENDERED_VISUAL_QA_MODEL", "gpt-4o-mini")


def _parse_json(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(str(raw or "").strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"rendered visual QA returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("rendered visual QA must return a JSON object")
    return data


def verify_rendered_visual(
    scene: SceneV2,
    plan: VisualPlanV2,
    selected_visual: CandidateVisualV2,
    vertical_video_path: str,
    *,
    client: Any = None,
) -> Verdict:
    """One fail-closed vision call over frames from the exact rendered clip."""
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage
    from video.hook_visual_dominance import _extract_vertical_frames

    frames = _extract_vertical_frames(vertical_video_path)
    if not frames:
        return Verdict(False, "no frames extracted from exact rendered clip", "visual_qa")

    requirements = {
        "subject": plan.subject,
        "required_visible_components": list(plan.required_visible_components),
        "required_observable_state": list(plan.required_observable_state),
        "required_relation_or_mechanism": list(plan.required_relation_or_mechanism),
        "forbidden_visuals": list(plan.forbidden_visuals),
    }
    prompt = (
        "Judge only these frames from the exact 9:16 clip that will be rendered. "
        "Do not infer from provider metadata or search terms. "
        "Return exact VisualPlan strings only when visibly confirmed. "
        "A static subject does not prove bending/flexing/deformation. "
        "Write description in the same language as the narration and use a narration "
        "term only when that exact physical evidence is visible. Do not echo narration "
        "to manufacture a match. JSON only with keys description, visible_components, "
        "observable_state.\nNarration: " + scene.narration + "\n"
        + json.dumps(requirements, ensure_ascii=False)
    )
    content = [{"type": "text", "text": prompt}]
    for frame in frames:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{frame}",
                "detail": "low",
            },
        })

    authorize_call(MODEL)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Fail closed. Use only visible evidence in the supplied frames. "
                    "Never promote UNKNOWN to visible."
                ),
            },
            {"role": "user", "content": content},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    record_usage(MODEL, response)
    data = _parse_json(response.choices[0].message.content)

    actual_visual = CandidateVisualV2.from_dict({
        "source_type": selected_visual.source_type,
        "description": str(data.get("description") or ""),
        "visible_components": data.get("visible_components") or [],
        "observable_state": data.get("observable_state") or [],
        "tags": list(selected_visual.tags),
        "provider": selected_visual.provider,
        "source_id": selected_visual.source_id,
        "media_url": selected_visual.media_url,
        "thumbnail_url": selected_visual.thumbnail_url,
        "search_query": selected_visual.search_query,
    })
    verdict = evaluate_scene_visual_qa(scene, plan, actual_visual)
    print(
        "[V2_RENDERED_VISUAL_QA] "
        f"scene={scene.scene_index} source_id={selected_visual.source_id or 'unknown'} "
        f"status={'PASS' if verdict.passed else 'FAIL'}"
    )
    return verdict
