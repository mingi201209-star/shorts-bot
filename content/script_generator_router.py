"""Stable Script Generator router with a legacy-compatible V2 boundary.

V2 is the production default after its dedicated regressions pass. Set
SCRIPT_ENGINE_MODE=legacy for an immediate rollback without changing code.
"""
import os
import re
from copy import deepcopy


def _observable_hook_from_candidate(candidate):
    """Project a question-shaped Candidate hook into a grounded observation."""
    result = deepcopy(candidate)
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result

    hook = str(micro.get("hook", "")).strip()
    if hook and "?" not in hook and not hook.startswith(("왜 ", "그런데 왜 ")):
        return result

    topic = str(result.get("topic", "")).strip()
    source = topic or hook
    value = source.rstrip(" ?.!…").strip()
    value = re.sub(r"^그런데\s+왜\s+", "", value)
    value = re.sub(r"^왜\s+", "", value)
    value = re.sub(r"\s*그\s*이유(?:는\s*무엇(?:일까|일까요)?)?$", "", value)
    value = re.sub(r"\s*이유(?:는\s*무엇(?:일까|일까요)?)?$", "", value)

    replacements = (
        (r"되어\s*있는$", "되어 있습니다"),
        (r"돼\s*있는$", "돼 있습니다"),
        (r"꺾여\s*있는$", "꺾여 있습니다"),
        (r"붙어\s*있는$", "붙어 있습니다"),
        (r"달려\s*있는$", "달려 있습니다"),
        (r"있는$", "있습니다"),
        (r"인다$", "입니다"),
    )
    observation = value
    for pattern, replacement in replacements:
        converted, count = re.subn(pattern, replacement, observation)
        if count:
            observation = converted
            break

    # Only accept a deterministic projection when it is plainly a statement.
    # Otherwise leave the original Candidate untouched so V2 still fails closed.
    observation = observation.strip()
    if observation and observation != source and "?" not in observation and observation.endswith(("습니다", "입니다")):
        micro = dict(micro)
        micro["hook"] = observation + "."
        result["micro_narrative"] = micro
        print(f"🧩 Router opening normalized without API: {micro['hook']}")
    return result


def _normalize_v2_result(result, topic_info, candidate):
    if not isinstance(result, dict):
        raise TypeError("Script Engine V2 result must be a dict")
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")
    if not isinstance(topic_info, dict):
        raise TypeError("topic_info must be a dict")

    scenes = result.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("Script Engine V2 scenes must be a list")

    normalized_scenes = []
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError("Script Engine V2 scene must be an object")
        item = dict(scene)
        item["text"] = str(item.get("text", "")).strip()
        item["visual_goal"] = str(item.get("visual_goal", "")).strip()
        item["keyword"] = " ".join(str(item.get("keyword", "")).strip().split())
        item["visual_type"] = str(item.get("visual_type", "real_world_broll")).strip() or "real_world_broll"
        normalized_scenes.append(item)

    normalized = dict(result)
    normalized.update({
        "title": str(result.get("title", "")).strip(),
        "topic": str(candidate.get("topic", "")).strip(),
        "category": str(topic_info.get("category", "")).strip(),
        "angle": str(candidate.get("angle", "")).strip(),
        "core_question": str(candidate.get("core_question", "")).strip(),
        "micro_narrative": candidate.get("micro_narrative") or {},
        "fact_check_focus": list(candidate.get("fact_check_focus") or []),
        "visual_proof": list(candidate.get("visual_proof") or []),
        "candidate_selection_reason": str(candidate.get("selection_reason", "")).strip(),
        "scenes": normalized_scenes,
    })

    required = ("title", "topic", "category", "angle", "core_question")
    missing = [key for key in required if not normalized.get(key)]
    if missing:
        raise ValueError("V2 compatibility metadata missing: " + ", ".join(missing))
    return normalized


def generate_script(topic_info, candidate):
    mode = os.environ.get("SCRIPT_ENGINE_MODE", "v2").strip().lower()
    if mode in ("", "v2"):
        from content.script_engine_v2_runner import generate_script_v2
        normalized_candidate = _observable_hook_from_candidate(candidate)
        return _normalize_v2_result(
            generate_script_v2(normalized_candidate),
            topic_info,
            normalized_candidate,
        )

    if mode in ("legacy", "v1"):
        from content.script_generator import generate_script as legacy_generate_script
        return legacy_generate_script(topic_info, candidate)

    raise ValueError(f"Unsupported SCRIPT_ENGINE_MODE: {mode}")
