from __future__ import annotations

from copy import deepcopy
import re

_PROTECTED_ROLES = {"phenomenon", "question", "hook", "reveal", "payoff", "conclusion"}


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _role(scene):
    return _norm((scene or {}).get("role") or (scene or {}).get("scene_role"))


def _visual_family(scene):
    scene = scene or {}
    goal = _norm(scene.get("visual_goal"))
    keyword = _norm(scene.get("keyword"))
    return (goal, keyword)


def information_fingerprint(scene):
    """Return a conservative deterministic fingerprint for exact information duplication.

    V1 intentionally does not attempt fuzzy semantic rewriting.  A Scene is compactable
    only when its normalized narration and visual demand are both identical to an earlier
    non-protected Scene.  This preserves distinct factual beats and requires no LLM call.
    """
    scene = scene or {}
    return (_norm(scene.get("text")),) + _visual_family(scene)


def compact_duplicate_visual_demand(script):
    """Remove only exact duplicate non-protected information Scenes.

    Hook/question/reveal/payoff/conclusion Scenes are never removed.  The function keeps
    the first occurrence, preserves order, and creates no new factual claim.
    """
    result = deepcopy(script or {})
    scenes = list(result.get("scenes") or [])
    seen = set()
    compacted = []
    removed = []

    for index, scene in enumerate(scenes):
        item = dict(scene or {})
        role = _role(item)
        fingerprint = information_fingerprint(item)
        text = fingerprint[0]
        if role not in _PROTECTED_ROLES and text and fingerprint in seen:
            removed.append({
                "scene_index": index,
                "human_scene_number": index + 1,
                "role": role,
                "text": str(item.get("text") or ""),
                "visual_goal": str(item.get("visual_goal") or ""),
                "keyword": str(item.get("keyword") or ""),
                "reason": "exact_information_and_visual_demand_duplicate",
            })
            continue
        if text:
            seen.add(fingerprint)
        compacted.append(item)

    result["scenes"] = compacted
    result["script_visual_budget"] = {
        "version": "v1",
        "original_scene_count": len(scenes),
        "final_scene_count": len(compacted),
        "removed_duplicate_count": len(removed),
        "removed_duplicates": removed,
        "extra_llm_calls": 0,
    }
    if removed:
        print(
            "[SCRIPT_VISUAL_BUDGET_V1] compacted="
            f"{len(removed)} scenes={','.join(str(x['human_scene_number']) for x in removed)}"
        )
    else:
        print("[SCRIPT_VISUAL_BUDGET_V1] compacted=0")
    return result
