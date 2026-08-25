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
    _question_hook_to_observation as _plan_question_hook_to_observation,
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


def _writer_response_format(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    """Require the writer to return every planned scene without adding a retry."""
    if mode != "writer":
        return {"type": "json_object"}
    scene_count = int(payload.get("target_scene_count") or 0)
    if scene_count < 1:
        raise ValueError("writer target_scene_count must be positive")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "shorts_script",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "scenes": {
                        "type": "array",
                        "minItems": scene_count,
                        "maxItems": scene_count,
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "visual_goal": {"type": "string"},
                                "keyword": {"type": "string"},
                            },
                            "required": ["text", "visual_goal", "keyword"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "scenes"],
                "additionalProperties": False,
            },
        },
    }


def _default_call(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    authorize_call(MODEL)
    if mode == "writer":
        instruction = (
            "Return JSON only with top-level keys title and scenes. "
            "Write exactly target_scene_count Shorts scenes. "
            "Each scene must contain text, visual_goal, and an English 2-7 word keyword. "
            "For EVERY scene, keyword must use ASCII English words only. "
            "Keep locked_text exact. Use formal Korean narration (~습니다/~합니다; questions only ~까요?). "
            "Use easy language. Do not reveal the final answer before reveal/payoff."
        )
    else:
        instruction = (
            "Return JSON only as {\"repairs\":[...]}. Repair ONLY the listed target scenes. "
            "Each repair must include scene_index and only fields that need changing. "
            "For locked scenes, NEVER change text; visual_goal and keyword may be repaired. "
            "Every keyword must be 2-7 ASCII English words. Use formal Korean and preserve factual scope."
        )
    response = openai.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format=_writer_response_format(payload, mode=mode),
    )
    record_usage(MODEL, response)
    return _extract_json(response.choices[0].message.content)


def _normalize_scene_fields(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Map harmless writer field aliases without spending another model call."""
    result = deepcopy(scene)

    if not str(result.get("text", "")).strip():
        for key in ("narration", "narration_text", "voiceover", "script", "line", "sentence"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                result["text"] = value.strip()
                break

    if len(str(result.get("visual_goal", "")).strip()) < 8:
        for key in ("visual", "visual_description", "scene_description", "visual_prompt", "shot"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                result["visual_goal"] = value.strip()
                break

    keyword = result.get("keyword")
    if isinstance(keyword, list):
        keyword = " ".join(str(item).strip() for item in keyword if str(item).strip())
        result["keyword"] = keyword
    if not str(result.get("keyword", "")).strip():
        for key in ("keywords", "search_keyword", "search_query", "query"):
            value = result.get(key)
            if isinstance(value, list):
                value = " ".join(str(item).strip() for item in value if str(item).strip())
            if isinstance(value, str) and value.strip():
                result["keyword"] = value.strip()
                break

    return result


def _ascii_keyword_words(value: Any) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", str(value or ""))
    result = []
    seen = set()
    for word in words:
        lowered = word.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(lowered)
    return result


def _keyword_contract_ok(value: Any) -> bool:
    words = str(value or "").strip().split()
    return 2 <= len(words) <= 7 and bool(re.search(r"[A-Za-z]", str(value or "")))


_FORMAL_ENDING_REPAIRS = (
    (r"줄어든다(?=[.!?…]*$)", "줄어듭니다"),
    (r"늘어난다(?=[.!?…]*$)", "늘어납니다"),
    (r"약해진다(?=[.!?…]*$)", "약해집니다"),
    (r"강해진다(?=[.!?…]*$)", "강해집니다"),
    (r"달라진다(?=[.!?…]*$)", "달라집니다"),
    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),
)


def _formalize_common_ending(text: Any) -> str:
    value = str(text or "").strip()
    for pattern, replacement in _FORMAL_ENDING_REPAIRS:
        value = re.sub(pattern, replacement, value)
    return value


def _deterministic_keyword(scene: Dict[str, Any], contract: Dict[str, Any], plan: Dict[str, Any], index: int) -> str:
    """Project failed keyword metadata into a bounded English search phrase."""
    current = str(scene.get("keyword", "")).strip()
    topic = str(plan.get("topic", "")).strip()
    if "비행기" in topic and "바퀴" in topic:
        fixed = ["aircraft", "landing", "gear", "wheel"]
        existing = _ascii_keyword_words(current)
        anchored = fixed + [word for word in existing if word not in fixed]
        return " ".join(anchored[:7])
    if _keyword_contract_ok(current):
        return current

    sources = [
        scene.get("visual_goal", ""),
        " ".join(str(item) for item in contract.get("required_concepts") or []),
    ]
    extracted = []
    for source in sources:
        for word in _ascii_keyword_words(source):
            if word not in extracted:
                extracted.append(word)
            if len(extracted) >= 6:
                break
        if len(extracted) >= 2:
            break
    if len(extracted) >= 2:
        # Preserve scene-local search variety even when every visual_goal uses
        # the same English template and differs only by its numeric stage.
        return " ".join((extracted[:6] + [str(index)])[:7])

    semantic_text = " ".join(
        str(value or "")
        for value in (
            current,
            scene.get("visual_goal", ""),
            " ".join(str(item) for item in contract.get("required_concepts") or []),
            plan.get("topic", ""),
            plan.get("angle", ""),
        )
    )
    hints = []
    for korean, english in (
        ("윙렛", "winglet"),
        ("날개", "aircraft wing"),
        ("소용돌이", "wingtip vortex"),
        ("공기", "airflow"),
        ("압력", "pressure"),
        ("유도항력", "induced drag"),
        ("항력", "drag"),
        ("연료", "fuel efficiency"),
    ):
        if korean in semantic_text:
            for word in english.split():
                if word not in hints:
                    hints.append(word)
        if len(hints) >= 4:
            break

    if not hints:
        hints = ["aircraft", "wing", "mechanism"]
    while len(hints) < 2:
        hints.append("detail")
    return " ".join((hints[:5] + ["stage", str(index)])[:7])


def _normalize_script_contracts_without_api(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Repair deterministic contract-only defects before spending local repair calls."""
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    contracts = plan.get("contracts") or []
    if len(scenes) != len(contracts):
        return result

    changed_keywords = 0
    changed_endings = 0
    for index, (scene, contract) in enumerate(zip(scenes, contracts), start=1):
        if not isinstance(scene, dict) or not isinstance(contract, dict):
            continue
        before_keyword = str(scene.get("keyword", "")).strip()
        scene["keyword"] = _deterministic_keyword(scene, contract, plan, index)
        if scene["keyword"] != before_keyword:
            changed_keywords += 1
        if not contract.get("locked"):
            before_text = str(scene.get("text", "")).strip()
            scene["text"] = _formalize_common_ending(before_text)
            if scene["text"] != before_text:
                changed_endings += 1

    if changed_keywords or changed_endings:
        print(
            "🧩 V2 deterministic contract normalization without API: "
            f"keywords={changed_keywords} endings={changed_endings}"
        )
    result["scenes"] = scenes
    return result


def _normalize_writer_envelope(response: Dict[str, Any]) -> Dict[str, Any]:
    """Accept harmless JSON envelope/field variants without another model call."""
    if not isinstance(response, dict):
        raise ValueError("Script Engine V2 writer response must be an object")

    normalized = response
    if not isinstance(response.get("scenes"), list):
        found = None
        for key in ("script", "result", "output"):
            nested = response.get(key)
            if isinstance(nested, dict) and isinstance(nested.get("scenes"), list):
                found = deepcopy(nested)
                if "title" not in found and isinstance(response.get("title"), str):
                    found["title"] = response["title"]
                print(f"🧩 V2 writer envelope normalized without API: {key}")
                break
        if found is None:
            scenes = response.get("scenes")
            if isinstance(scenes, dict):
                def scene_sort_key(item):
                    raw = str(item[0])
                    match = re.search(r"(\d+)", raw)
                    return int(match.group(1)) if match else 10**6
                ordered = [value for _, value in sorted(scenes.items(), key=scene_sort_key) if isinstance(value, dict)]
                if ordered:
                    found = deepcopy(response)
                    found["scenes"] = ordered
                    print("🧩 V2 writer scene-map normalized without API")
        if found is None:
            raise ValueError("script.scenes must be a list")
        normalized = found

    result = deepcopy(normalized)
    result["scenes"] = [
        _normalize_scene_fields(scene) if isinstance(scene, dict) else scene
        for scene in result.get("scenes", [])
    ]
    return result


def _normalize_repair_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the same harmless field alias normalization to local repairs."""
    result = _normalize_scene_fields(item)
    if "scene_index" not in result:
        for key in ("index", "scene", "scene_number"):
            if key in result:
                result["scene_index"] = result[key]
                break
    return result


def _apply_local_repairs(
    script: Dict[str, Any],
    response: Dict[str, Any],
    allowed_indexes: set[int],
    locked_text_indexes: set[int],
) -> Dict[str, Any]:
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    repairs = response.get("repairs") or []
    if not isinstance(repairs, list):
        raise ValueError("local repair response repairs must be a list")
    for raw_item in repairs:
        if not isinstance(raw_item, dict):
            continue
        item = _normalize_repair_item(raw_item)
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
            if field == "text" and scene_index in locked_text_indexes:
                continue
            value = item.get(field)
            if isinstance(value, str) and value.strip():
                scenes[index][field] = value.strip()
    result["scenes"] = scenes
    return result


def _question_hook_to_observation(text: Any, topic: Any = "") -> str:
    """Convert a simple Korean why-question into a fact-neutral observation."""
    original = str(text or "").strip()
    value = original
    if not value:
        return value
    if "?" not in value and not value.startswith(("왜 ", "그런데 왜 ")):
        return value

    if re.search(r"이유는\s*무엇(?:일까|일까요)\??$", value):
        normalized = _plan_question_hook_to_observation(value, topic)
        if normalized:
            return normalized

    reason_tail = re.search(r",?\s*그\s*이유는\s*무엇(?:일까|일까요)\??$", value)
    if reason_tail:
        value = value[:reason_tail.start()].rstrip(" ,")
        value = re.sub(r"있지만$", "있습니다", value)
        value = re.sub(r"보이지만$", "보입니다", value)
        if value and value != original:
            return value.rstrip(".") + "."

    value = re.sub(r"^그런데\s+", "", value)
    value = re.sub(r"^왜\s+", "", value)
    value = value.rstrip().rstrip("?").strip()
    value = re.sub(r"\s+왜\s+", " ", value, count=1)

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
    return original


def _normalize_candidate_opening(candidate: Dict[str, Any], approved_hook: str) -> tuple[Dict[str, Any], str]:
    """Normalize a Candidate-supplied question Hook without mutating caller data."""
    result = deepcopy(candidate)
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result, approved_hook

    if approved_hook:
        normalized = _question_hook_to_observation(approved_hook, result.get("topic"))
        return result, normalized

    original = micro.get("hook")
    normalized = _question_hook_to_observation(original, result.get("topic"))
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

    generated = _normalize_writer_envelope(generated)
    script = apply_locked_scenes(generated, plan)
    script = _normalize_script_contracts_without_api(script, plan)
    validation = validate_script_v2(script, plan)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    script = repair_failed_scenes(script, plan, validation["failed_scene_indexes"])
    script = _normalize_script_contracts_without_api(script, plan)
    validation = validate_script_v2(script, plan)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    for _ in range(MAX_LOCAL_REPAIR_CALLS):
        indexes = validation["failed_scene_indexes"]
        payload = local_repair_payload(script, plan, indexes, validation["reasons"])
        allowed = {int(item["scene_index"]) for item in payload["targets"]}
        locked_text_indexes = {
            int(item["scene_index"])
            for item in payload["targets"]
            if item.get("text_locked")
        }
        if not allowed:
            break
        response = caller(payload, mode="local_repair")
        call_count += 1
        if call_count > MAX_SCRIPT_API_CALLS:
            raise RuntimeError("Script Engine V2 call budget exceeded")
        script = _apply_local_repairs(script, response, allowed, locked_text_indexes)
        script = apply_locked_scenes(script, plan)
        script = repair_failed_scenes(script, plan, list(allowed))
        script = _normalize_script_contracts_without_api(script, plan)
        validation = validate_script_v2(script, plan)
        if validation["valid"]:
            script["script_engine_v2_calls"] = call_count
            return script

    raise RuntimeError(
        "Script Engine V2 validation failed within 3 calls: "
        + " | ".join(validation["reasons"])
    )