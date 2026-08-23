"""Bounded Script Engine V2 orchestration.

One full writer call, deterministic repair, then at most two scene-local LLM
repair calls. There is intentionally no whole-script regeneration loop.
"""
import json
import os
import re
from copy import deepcopy
from typing import Any, Callable, Dict

import openai

from config import OPENAI_KEY
from quality.budget_guard import authorize_call, record_usage
from content.script_engine_v2 import (
    MAX_LOCAL_REPAIR_CALLS,
    MAX_SCRIPT_API_CALLS,
    apply_locked_scenes,
    build_narrative_plan,
    local_repair_payload,
    repair_failed_scenes,
    writer_payload,
)
from content.script_engine_v2_validation import validate_script_v2

MODEL = os.environ.get("V3_SCRIPT_MODEL", "gpt-4o-mini")
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


def _extract_json(text: Any) -> Dict[str, Any]:
    value = str(text or "").strip()
    value = re.sub(r"```json|```", "", value, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start, end = value.find("{"), value.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(value[start:end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Script Engine V2 response did not contain a JSON object")


def _default_call(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    authorize_call(MODEL)
    if mode == "writer":
        instruction = (
            "Return JSON only. Write exactly target_scene_count Shorts scenes. "
            "Each scene must contain text, visual_goal, and an English 2-7 word keyword. "
            "Keep locked_text exact. Use formal Korean narration (~습니다/~합니다; questions only ~까요?). "
            "Use easy language. Do not reveal the final answer before reveal/payoff."
        )
    else:
        instruction = (
            "Return JSON only as {\"repairs\":[...]}. Repair ONLY the listed target scenes. "
            "Each repair must include scene_index and only fields that need changing. "
            "Use formal Korean and preserve all factual scope."
        )
    response = openai.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    record_usage(MODEL, response)
    return _extract_json(response.choices[0].message.content)


def _apply_local_repairs(script: Dict[str, Any], response: Dict[str, Any], allowed_indexes: set[int]) -> Dict[str, Any]:
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    repairs = response.get("repairs") or []
    if not isinstance(repairs, list):
        raise ValueError("local repair response repairs must be a list")
    for item in repairs:
        if not isinstance(item, dict):
            continue
        try:
            scene_index = int(item.get("scene_index"))
        except Exception:
            continue
        if scene_index not in allowed_indexes:
            continue
        index = scene_index - 1
        if index < 0 or index >= len(scenes) or not isinstance(scenes[index], dict):
            continue
        for field in ("text", "visual_goal", "keyword"):
            value = item.get(field)
            if isinstance(value, str) and value.strip():
                scenes[index][field] = value.strip()
    result["scenes"] = scenes
    return result


def _question_hook_to_observation(text: Any) -> str:
    """Convert only simple Korean why-questions into a fact-neutral observation.

    This is a zero-API boundary repair for Candidate micro_narrative hooks. It
    intentionally supports a small, deterministic set of endings; anything
    outside that set is left unchanged so build_narrative_plan can fail closed.
    """
    value = str(text or "").strip()
    if not value:
        return value
    if "?" not in value and not value.startswith(("왜 ", "그런데 왜 ")):
        return value

    value = re.sub(r"^그런데\s+", "", value)
    value = re.sub(r"^왜\s+", "", value)
    value = value.rstrip().rstrip("?").strip()

    replacements = (
        (r"있을까요$", "있습니다"),
        (r"있을까$", "있습니다"),
        (r"일까요$", "입니다"),
        (r"일까$", "입니다"),
        (r"될까요$", "됩니다"),
        (r"될까$", "됩니다"),
        (r"할까요$", "합니다"),
        (r"할까$", "합니다"),
    )
    for pattern, replacement in replacements:
        converted, count = re.subn(pattern, replacement, value)
        if count:
            return converted.rstrip(".") + "."
    return str(text or "").strip()


def _normalize_candidate_opening(candidate: Dict[str, Any], approved_hook: str) -> tuple[Dict[str, Any], str]:
    """Normalize a Candidate-supplied question Hook without mutating caller data."""
    result = deepcopy(candidate)
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result, approved_hook

    if approved_hook:
        normalized = _question_hook_to_observation(approved_hook)
        return result, normalized

    original = micro.get("hook")
    normalized = _question_hook_to_observation(original)
    if normalized != str(original or "").strip():
        micro["hook"] = normalized
        result["micro_narrative"] = micro
        print(f"🧩 V2 opening normalized without API: {normalized}")
    return result, approved_hook


def generate_script_v2(
    candidate: Dict[str, Any],
    approved_hook: str = "",
    *,
    call_fn: Callable[..., Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Generate one Script with a hard V2-local call ceiling of three."""
    caller = call_fn or _default_call
    candidate, approved_hook = _normalize_candidate_opening(candidate, approved_hook)
    plan = build_narrative_plan(candidate, approved_hook=approved_hook)
    call_count = 0

    generated = caller(writer_payload(candidate, plan), mode="writer")
    call_count += 1
    if call_count > MAX_SCRIPT_API_CALLS:
        raise RuntimeError("Script Engine V2 call budget exceeded")

    script = apply_locked_scenes(generated, plan)
    validation = validate_script_v2(script, plan)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    script = repair_failed_scenes(script, plan, validation["failed_scene_indexes"])
    validation = validate_script_v2(script, plan)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    for _ in range(MAX_LOCAL_REPAIR_CALLS):
        indexes = validation["failed_scene_indexes"]
        payload = local_repair_payload(script, plan, indexes, validation["reasons"])
        allowed = {int(item["scene_index"]) for item in payload["targets"]}
        if not allowed:
            break
        response = caller(payload, mode="local_repair")
        call_count += 1
        if call_count > MAX_SCRIPT_API_CALLS:
            raise RuntimeError("Script Engine V2 call budget exceeded")
        script = _apply_local_repairs(script, response, allowed)
        script = apply_locked_scenes(script, plan)
        script = repair_failed_scenes(script, plan, list(allowed))
        validation = validate_script_v2(script, plan)
        if validation["valid"]:
            script["script_engine_v2_calls"] = call_count
            return script

    raise RuntimeError(
        "Script Engine V2 validation failed within 3 calls: "
        + " | ".join(validation["reasons"])
    )
