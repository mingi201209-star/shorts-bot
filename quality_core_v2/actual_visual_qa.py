"""Actual rendered-scene semantic QA for Clean V2.

This is the bridge that closes the known plan->create_scene gap without
changing create_scene's public interface.  It inspects the exact 9:16
vertical clip produced for each scene and checks it against that scene's
VisualPlanV2.  One bounded vision call per scene, no retries, no fallback
relaxation.  A failure blocks final rendering.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from quality_core_v2.schemas import SceneV2, VisualPlanV2

REPORT_PATH = Path("v2_actual_visual_qa.json")
MODEL = os.environ.get("V3_ACTUAL_VISUAL_QA_MODEL", "gpt-4o-mini")


def _parse_json(text: str) -> Dict[str, Any]:
    text = str(text or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("V2 actual visual QA response did not contain JSON")
        payload = json.loads(text[start:end + 1])
    if not isinstance(payload, dict):
        raise ValueError("V2 actual visual QA response must be an object")
    return payload


def _call_scene_vision(
    scene: SceneV2,
    plan: VisualPlanV2,
    vertical_video_path: str,
    *,
    client: Any = None,
) -> Dict[str, Any]:
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage
    from video.hook_visual_dominance import _extract_vertical_frames

    frames = _extract_vertical_frames(vertical_video_path)
    requirements = {
        "subject": plan.subject,
        "required_visible_components": list(plan.required_visible_components),
        "required_observable_state": list(plan.required_observable_state),
        "required_relation_or_mechanism": list(plan.required_relation_or_mechanism),
        "forbidden_visuals": list(plan.forbidden_visuals),
    }
    prompt = f"""
You are the final semantic visual inspector for a mobile YouTube Short.
Judge ONLY the supplied frames from the exact rendered 9:16 scene.
Do not infer anything from the search query, filename, metadata, or narration
that is not visibly evidenced in the frames.

Scene narration:
{scene.narration}

Required VisualPlan:
{json.dumps(requirements, ensure_ascii=False)}

Rules:
- Subject presence alone is NOT enough.
- required_visible_components must actually be visible and identifiable.
- required_observable_state must visibly occur. If the plan requires bending,
  flexing, twisting, deployment, vibration, motion, deformation, or another
  physical state/change, a normal static shot of the subject FAILS.
- required_relation_or_mechanism must be visually supported. Generic contextual
  B-roll of the same domain FAILS when it does not show that relation/mechanism.
- Any forbidden visual that is visibly present FAILS.
- For a requirement that cannot be established from these frames, answer false.
- Never give credit because the narration says something should be happening.

Return JSON only:
{{
  "visible_components": ["..."],
  "observable_states": ["..."],
  "visible_relations_or_mechanisms": ["..."],
  "forbidden_visuals_present": ["..."],
  "components_satisfied": false,
  "observable_state_satisfied": false,
  "relation_or_mechanism_satisfied": false,
  "reason": "short concrete visual explanation"
}}
"""
    content = [{"type": "text", "text": prompt}]
    for encoded in frames:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encoded}",
                "detail": "low",
            },
        })

    call_number = authorize_call(MODEL)
    print(f"[V2_ACTUAL_VISUAL_QA] call_authorized={call_number} scene={scene.scene_index}")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Fail closed. Judge the exact rendered frames, not metadata. "
                    "Static subject-only matches do not prove a requested physical phenomenon."
                ),
            },
            {"role": "user", "content": content},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    usage = record_usage(MODEL, response)
    print(
        f"[V2_ACTUAL_VISUAL_QA] scene={scene.scene_index} "
        f"cost_usd={usage['cost_usd']:.6f}"
    )
    return _parse_json(response.choices[0].message.content)


def _payload_passes_plan(payload: Dict[str, Any], plan: VisualPlanV2) -> bool:
    forbidden_present = [
        str(value).strip()
        for value in (payload.get("forbidden_visuals_present") or [])
        if str(value).strip()
    ]
    components_ok = bool(payload.get("components_satisfied", False))
    state_ok = bool(payload.get("observable_state_satisfied", False))
    relation_ok = (
        bool(payload.get("relation_or_mechanism_satisfied", False))
        if plan.required_relation_or_mechanism
        else True
    )
    return components_ok and state_ok and relation_ok and not forbidden_present


def inspect_v2_item_clip(
    item: Dict[str, Any],
    vertical_video_path: str,
    *,
    inspect_fn=None,
) -> Dict[str, Any]:
    """Verify one V2 fallback asset before it can enter the verified cache.

    This uses the same strict final inspector as the post-render gate.  It is
    only activated for items carrying Clean V2 private requirements, so the
    V1 path remains unchanged.
    """
    required_states = list(item.get("_v2_required_observable_state") or [])
    required_components = list(item.get("_v2_required_visible_components") or [])
    if not required_states and not required_components:
        return {"passed": True, "reason": "no V2 semantic requirements"}

    scene_index = int(item.get("_v2_scene_index", 0) or 0)
    scene = SceneV2(
        scene_index=scene_index,
        narration=str(item.get("text") or ""),
        causal_role="v2_asset_check",
        owned_claim_id=f"v2_asset_{scene_index}",
        new_information=str(item.get("text") or ""),
        visual_requirement=str(item.get("visual_goal") or ""),
    )
    plan = VisualPlanV2(
        scene_index=scene_index,
        subject=str(item.get("_v2_subject") or item.get("keyword") or ""),
        required_visible_components=required_components,
        required_observable_state=required_states,
        required_relation_or_mechanism=list(
            item.get("_v2_required_relation_or_mechanism") or []
        ),
        forbidden_visuals=list(item.get("_v2_forbidden_visuals") or []),
        preferred_source_type=str(item.get("_v2_preferred_source_type") or ""),
        search_queries=[str(item.get("keyword") or "")],
        generation_prompt_constraints=list(
            item.get("_v2_generation_prompt_constraints") or []
        ),
    )
    payload = (
        inspect_fn(scene, plan, vertical_video_path)
        if inspect_fn is not None
        else _call_scene_vision(scene, plan, vertical_video_path)
    )
    passed = _payload_passes_plan(payload, plan)
    result = {
        "passed": passed,
        "scene_index": scene_index,
        "reason": str(payload.get("reason") or "")[:800],
        "payload": payload,
    }
    print(
        "[V2_ASSET_PREFLIGHT] "
        f"scene={scene_index} status={'PASS' if passed else 'FAIL'} "
        f"reason={result['reason']}"
    )
    return result


def validate_actual_v2_visuals(
    scenes: List[SceneV2],
    plans: List[VisualPlanV2],
    items: List[Dict[str, Any]],
    *,
    get_scene_paths_fn=None,
    inspect_fn=None,
) -> Dict[str, Any]:
    """Inspect every actual rendered scene once and fail closed on mismatch."""
    if len(scenes) != len(plans) or len(scenes) != len(items):
        raise ValueError(
            "V2 actual visual QA requires aligned scenes/plans/items "
            f"({len(scenes)}/{len(plans)}/{len(items)})"
        )

    if get_scene_paths_fn is None:
        from video.video_engine import get_scene_paths as get_scene_paths_fn

    results = []
    failures = []

    for idx, (scene, plan, item) in enumerate(zip(scenes, plans, items)):
        path = str(get_scene_paths_fn(idx)["vertical_video"])
        if not Path(path).is_file():
            entry = {
                "scene_index": int(scene.scene_index),
                "clip_index": idx,
                "status": "FAIL",
                "reason": f"rendered vertical scene clip missing: {path}",
                "plan": {
                    "subject": plan.subject,
                    "required_visible_components": list(plan.required_visible_components),
                    "required_observable_state": list(plan.required_observable_state),
                    "required_relation_or_mechanism": list(plan.required_relation_or_mechanism),
                    "forbidden_visuals": list(plan.forbidden_visuals),
                },
            }
            results.append(entry)
            failures.append(entry)
            continue

        payload = (
            inspect_fn(scene, plan, path)
            if inspect_fn is not None
            else _call_scene_vision(scene, plan, path)
        )
        forbidden_present = [
            str(value).strip()
            for value in (payload.get("forbidden_visuals_present") or [])
            if str(value).strip()
        ]
        components_ok = bool(payload.get("components_satisfied", False))
        state_ok = bool(payload.get("observable_state_satisfied", False))
        relation_ok = (
            bool(payload.get("relation_or_mechanism_satisfied", False))
            if plan.required_relation_or_mechanism
            else True
        )
        passed = _payload_passes_plan(payload, plan)

        entry = {
            "scene_index": int(scene.scene_index),
            "clip_index": idx,
            "status": "PASS" if passed else "FAIL",
            "path": path,
            "query": str(item.get("keyword") or ""),
            "plan": {
                "subject": plan.subject,
                "required_visible_components": list(plan.required_visible_components),
                "required_observable_state": list(plan.required_observable_state),
                "required_relation_or_mechanism": list(plan.required_relation_or_mechanism),
                "forbidden_visuals": list(plan.forbidden_visuals),
            },
            "visible_components": list(payload.get("visible_components") or []),
            "observable_states": list(payload.get("observable_states") or []),
            "visible_relations_or_mechanisms": list(
                payload.get("visible_relations_or_mechanisms") or []
            ),
            "forbidden_visuals_present": forbidden_present,
            "components_satisfied": components_ok,
            "observable_state_satisfied": state_ok,
            "relation_or_mechanism_satisfied": relation_ok,
            "reason": str(payload.get("reason") or "")[:800],
        }
        results.append(entry)
        if not passed:
            failures.append(entry)

    report = {
        "status": "PASS" if not failures else "FAIL",
        "scene_count": len(scenes),
        "checked_scene_count": len(results),
        "failed_scene_indexes": [entry["scene_index"] for entry in failures],
        "scenes": results,
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[V2_ACTUAL_VISUAL_QA] status={report['status']} "
        f"failed={report['failed_scene_indexes']} report={REPORT_PATH}"
    )
    if failures:
        raise RuntimeError(
            "V2_ACTUAL_VISUAL_QA_FAILED "
            f"scenes={report['failed_scene_indexes']}"
        )
    return report
