"""Strict QA for the exact 9:16 clip Clean V2 will actually render."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
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


def classify_rendered_visual(
    scene: SceneV2,
    plan: VisualPlanV2,
    selected_visual: CandidateVisualV2,
    vertical_video_path: str,
    *,
    client: Any = None,
) -> CandidateVisualV2:
    """Classify visible evidence from the exact rendered clip."""
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage

    frames = _extract_scene_frames(vertical_video_path)
    if not frames:
        raise ValueError("no frames extracted from exact rendered clip")

    requirements = {
        "subject": plan.subject,
        "required_visible_components": list(plan.required_visible_components),
        "required_observable_state": list(plan.required_observable_state),
        "required_relation_or_mechanism": list(plan.required_relation_or_mechanism),
        "forbidden_visuals": list(plan.forbidden_visuals),
    }
    prompt = (
        "Judge only these frames from the exact 9:16 clip that will be rendered. "
        "Do not infer from provider metadata or search terms. Return exact VisualPlan "
        "strings only when visibly confirmed. A static subject does not prove bending, "
        "flexing, deformation, or a mechanism relation. Write description in the same "
        "language as the narration and use a narration term only when that exact "
        "physical evidence is visible. Do not echo narration to manufacture a match. "
        "JSON only with keys description, visible_components, observable_state, "
        "visible_relations_or_mechanisms, forbidden_visuals_present. "
        "forbidden_visuals_present must contain only exact forbidden_visuals strings "
        "that are visibly present.\nNarration: " + scene.narration + "\n"
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

    return CandidateVisualV2.from_dict({
        "source_type": selected_visual.source_type,
        "description": str(data.get("description") or ""),
        "visible_components": data.get("visible_components") or [],
        "observable_state": data.get("observable_state") or [],
        "visible_relations_or_mechanisms": (
            data.get("visible_relations_or_mechanisms") or []
        ),
        "forbidden_visuals_present": (
            data.get("forbidden_visuals_present") or []
        ),
        "tags": list(selected_visual.tags),
        "provider": selected_visual.provider,
        "source_id": selected_visual.source_id,
        "media_url": selected_visual.media_url,
        "thumbnail_url": selected_visual.thumbnail_url,
        "search_query": selected_visual.search_query,
    })


def _extract_scene_frames(video_path: str) -> list[str]:
    """Sample the whole rendered scene, not only hook-time frames.

    Four evenly distributed frames are enough for a bounded semantic check and
    avoid the old mistake of applying the first-2.7-second hook sampler to every
    mechanism/payoff scene.
    """
    with tempfile.TemporaryDirectory(prefix="v2_scene_qa_") as temp_dir:
        pattern = Path(temp_dir) / "frame_%03d.jpg"
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-vf",
                "scale=540:960:force_original_aspect_ratio=increase,"
                + "crop=540:960,setsar=1,fps=1",
                "-q:v",
                "4",
                str(pattern),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "V2 rendered visual frame extraction failed: "
                + result.stderr[-600:]
            )
        frames = sorted(Path(temp_dir).glob("frame_*.jpg"))
        if not frames:
            raise RuntimeError("V2 rendered visual frame extraction produced no frames")

        if len(frames) <= 4:
            selected = frames
        else:
            indexes = [0, len(frames) // 3, (2 * len(frames)) // 3, len(frames) - 1]
            selected = [frames[i] for i in sorted(set(indexes))]
        return [
            base64.b64encode(path.read_bytes()).decode("ascii")
            for path in selected
        ]


def verify_rendered_visual(
    scene: SceneV2,
    plan: VisualPlanV2,
    selected_visual: CandidateVisualV2,
    vertical_video_path: str,
    *,
    client: Any = None,
) -> Verdict:
    """One fail-closed vision call over frames from the exact rendered clip."""
    try:
        actual_visual = classify_rendered_visual(
            scene,
            plan,
            selected_visual,
            vertical_video_path,
            client=client,
        )
    except ValueError as exc:
        return Verdict(False, str(exc), "visual_qa")
    verdict = evaluate_scene_visual_qa(scene, plan, actual_visual)
    print(
        "[V2_RENDERED_VISUAL_QA] "
        f"scene={scene.scene_index} source_id={selected_visual.source_id or 'unknown'} "
        f"status={'PASS' if verdict.passed else 'FAIL'}"
    )
    return verdict
