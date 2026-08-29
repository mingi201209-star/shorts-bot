"""Stable Script Generator router with a legacy-compatible V2 boundary.

V2 is the production default after its dedicated regressions pass. Set
SCRIPT_ENGINE_MODE=legacy for an immediate rollback without changing code.
"""
import os
import re
from copy import deepcopy

from content.script_visual_budget import compact_duplicate_visual_demand
from content.winglet_visual_beat_recovery import recover_unsupported_winglet_visual_beat


def _question_like(text):
    value = str(text or "").strip()
    return bool(value) and (
        "?" in value
        or value.startswith(("왜 ", "그런데 왜 "))
        or bool(re.search(r"\b왜\b", value))
        or value.endswith(("을까", "ㄹ까", "일까", "을까요", "ㄹ까요", "일까요"))
    )


def _observable_statement(text):
    """Project only supported Korean observation forms; otherwise fail closed."""
    source = str(text or "").strip()
    if not source:
        return ""

    value = source.rstrip(" ?.!…").strip()
    value = re.sub(r"^그런데\s+왜\s+", "", value)
    value = re.sub(r"^왜\s+", "", value)
    value = re.sub(r"\s*그\s*이유(?:는\s*무엇(?:일까|일까요)?)?$", "", value)
    value = re.sub(r"\s*이유(?:는\s*무엇(?:일까|일까요)?)?$", "", value)

    # Opening-role contract: a fixed topic may itself be a why-question even
    # though Scene 1 must remain an observable statement. Convert only concrete
    # predicate shapes whose physical observation is already present in text.
    embedded_why_repairs = (
        (r"^(.+?(?:은|는|이|가))\s+왜\s+(.+?)\s*생겼(?:을까|을까요)$", r"\1 \2 생겼습니다"),
        (r"^(.+?(?:은|는|이|가))\s+왜\s+(.+?)\s*되어\s*있(?:을까|을까요)$", r"\1 \2 되어 있습니다"),
        (r"^(.+?(?:은|는|이|가))\s+왜\s+(.+?)\s*있(?:을까|을까요)$", r"\1 \2 있습니다"),
    )
    observation = value
    for pattern, replacement in embedded_why_repairs:
        converted, count = re.subn(pattern, replacement, observation)
        if count:
            observation = converted
            break

    replacements = (
        (r"지 않는다$", "지 않습니다"),
        (r"되어\s*있는$", "되어 있습니다"),
        (r"돼\s*있는$", "돼 있습니다"),
        (r"꺾여\s*있는$", "꺾여 있습니다"),
        (r"붙어\s*있는$", "붙어 있습니다"),
        (r"달려\s*있는$", "달려 있습니다"),
        (r"만든다$", "만듭니다"),
        (r"아낀다$", "아낍니다"),
        (r"단다$", "답니다"),
        (r"있는$", "있습니다"),
        (r"인다$", "입니다"),
    )
    for pattern, replacement in replacements:
        converted, count = re.subn(pattern, replacement, observation)
        if count:
            observation = converted
            break

    observation = observation.strip()
    if (
        observation
        and "?" not in observation
        and not re.search(r"\b왜\b", observation)
        and observation.endswith(("습니다", "입니다", "니다"))
    ):
        return observation + "."
    return ""


def _observable_hook_from_candidate(candidate):
    """Keep Candidate question role separate from the Scene 1 observation role."""
    result = deepcopy(candidate)
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result

    hook = str(micro.get("hook", "")).strip()
    if hook and not _question_like(hook):
        return result

    # Reuse already-existing Candidate information only. No LLM call and no new
    # factual claim: prefer an explicit observation when present, then the fixed
    # topic, then the question-shaped hook itself. Unsupported forms stay intact
    # so Script V2's observable-statement validation continues to fail closed.
    sources = (
        result.get("observation"),
        micro.get("observation"),
        result.get("topic"),
        hook,
    )
    observation = ""
    for source in sources:
        observation = _observable_statement(source)
        if observation:
            break

    if observation and observation != hook:
        micro = dict(micro)
        micro["hook"] = observation
        result["micro_narrative"] = micro
        print(f"🧩 Router opening normalized without API: {micro['hook']}")
    return result


def _formal_question(text):
    value = str(text or "").strip()
    if not value:
        return value
    repairs = (
        (r"을까\?$", "을까요?"),
        (r"ㄹ까\?$", "ㄹ까요?"),
        (r"일까\?$", "일까요?"),
        (r"할까\?$", "할까요?"),
        (r"될까\?$", "될까요?"),
        (r"있을까\?$", "있을까요?"),
        (r"없을까\?$", "없을까요?"),
    )
    for pattern, replacement in repairs:
        converted, count = re.subn(pattern, replacement, value)
        if count:
            return converted
    return value


def _formal_locked_statement(text):
    value = str(text or "").strip()
    repairs = (
        (r"높아진다(?=[.!?…]*$)", "높아집니다"),
        (r"낮아진다(?=[.!?…]*$)", "낮아집니다"),
        (r"줄어든다(?=[.!?…]*$)", "줄어듭니다"),
        (r"늘어난다(?=[.!?…]*$)", "늘어납니다"),
        (r"개선된다(?=[.!?…]*$)", "개선됩니다"),
    )
    for pattern, replacement in repairs:
        value = re.sub(pattern, replacement, value)
    return value


def _normalize_locked_candidate_narration(candidate):
    result = deepcopy(candidate)
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result

    normalized_micro = dict(micro)
    changed = []

    top_question_source = str(result.get("core_question", "")).strip()
    top_question = _formal_question(top_question_source)
    if top_question and top_question != top_question_source:
        result["core_question"] = top_question
        changed.append("core_question")

    micro_question_source = str(normalized_micro.get("core_question", "")).strip()
    micro_question = _formal_question(micro_question_source)
    if micro_question and micro_question != micro_question_source:
        normalized_micro["core_question"] = micro_question
        changed.append("scene2_question")

    for key in ("reveal", "payoff"):
        source = str(normalized_micro.get(key, "")).strip()
        normalized = _formal_locked_statement(source)
        if normalized != source:
            normalized_micro[key] = normalized
            changed.append(key)

    if changed:
        result["micro_narrative"] = normalized_micro
        print("🧩 Router locked narration normalized without API: " + ",".join(changed))
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
        normalized_candidate = _normalize_locked_candidate_narration(normalized_candidate)
        generated = generate_script_v2(normalized_candidate)
        recovered = recover_unsupported_winglet_visual_beat(
            generated,
            normalized_candidate,
        )
        normalized = _normalize_v2_result(
            recovered,
            topic_info,
            normalized_candidate,
        )
        return compact_duplicate_visual_demand(normalized)

    if mode in ("legacy", "v1"):
        from content.script_generator import generate_script as legacy_generate_script
        return legacy_generate_script(topic_info, candidate)

    raise ValueError(f"Unsupported SCRIPT_ENGINE_MODE: {mode}")