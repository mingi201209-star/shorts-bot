"""Stable Script Generator router with a legacy-compatible V2 boundary."""
import os


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
    mode = os.environ.get("SCRIPT_ENGINE_MODE", "legacy").strip().lower()
    if mode == "v2":
        from content.script_engine_v2_runner import generate_script_v2
        return _normalize_v2_result(generate_script_v2(candidate), topic_info, candidate)

    if mode not in ("", "legacy", "v1"):
        raise ValueError(f"Unsupported SCRIPT_ENGINE_MODE: {mode}")

    from content.script_generator import generate_script as legacy_generate_script
    return legacy_generate_script(topic_info, candidate)
