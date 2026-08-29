"""Validation adapter for Script Engine V2.

Uses existing production validators without weakening them and reports scene-local
failures in a machine-readable way so the runner can repair only those scenes.
"""
import re
from typing import Any, Dict, List, Tuple

from content.retention_structure import (
    validate_density,
    validate_first5_progression,
    validate_new_information,
)
from quality.korean_speech_style import validate_korean_speech_text

BAD_VISUAL_KEYWORDS = {
    "science", "technology", "nature", "interesting", "amazing",
    "documentary", "random", "background", "concept", "future",
}


def _scene_index_from_reason(reason: str) -> int | None:
    text = str(reason or "")
    for pattern in (
        r"scene\s*(\d+)",
        r"(\d+)번\s*Scene",
        r"(\d+)번\s*scene",
        r"(\d+)번\s*장면",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def validate_scene_basics(
    script: Dict[str, Any],
    plan: Dict[str, Any],
) -> Tuple[bool, List[Dict[str, Any]]]:
    failures: List[Dict[str, Any]] = []
    scenes = script.get("scenes") if isinstance(script, dict) else None
    contracts = plan.get("contracts") if isinstance(plan, dict) else None

    if not isinstance(scenes, list):
        return False, [{"scene_index": None, "reason": "script.scenes must be a list"}]
    if not isinstance(contracts, list):
        return False, [{"scene_index": None, "reason": "plan.contracts must be a list"}]
    if len(scenes) != len(contracts):
        return False, [{
            "scene_index": None,
            "reason": f"scene count mismatch: {len(scenes)}/{len(contracts)}",
        }]

    keyword_values = []
    for index, (scene, contract) in enumerate(zip(scenes, contracts), start=1):
        if not isinstance(scene, dict):
            failures.append({"scene_index": index, "reason": "scene must be an object"})
            continue

        text = str(scene.get("text", "")).strip()
        visual_goal = str(scene.get("visual_goal", "")).strip()
        keyword = " ".join(str(scene.get("keyword", "")).strip().lower().split())
        keyword_values.append(keyword)

        if not text:
            failures.append({"scene_index": index, "reason": "scene text missing"})
        if len(visual_goal) < 8:
            failures.append({"scene_index": index, "reason": "visual_goal missing or too short"})
        if not keyword:
            failures.append({"scene_index": index, "reason": "keyword missing"})
        elif not re.search(r"[A-Za-z]", keyword):
            failures.append({"scene_index": index, "reason": "keyword must contain English"})
        elif not 2 <= len(keyword.split()) <= 7:
            failures.append({"scene_index": index, "reason": "keyword must be 2-7 words"})
        elif keyword in BAD_VISUAL_KEYWORDS:
            failures.append({"scene_index": index, "reason": "keyword too abstract"})

        if text:
            valid, reason = validate_korean_speech_text(text, allow_nominal=False)
            if not valid:
                failures.append({"scene_index": index, "reason": reason})

        if str(scene.get("role", "")).strip() != str(contract.get("role", "")).strip():
            failures.append({"scene_index": index, "reason": "scene role does not match plan"})

    if keyword_values:
        unique_count = len(set(keyword_values))
        required = max(6, len(keyword_values) // 2)
        if unique_count < required:
            failures.append({
                "scene_index": None,
                "reason": f"keyword variety too low: {unique_count}/{len(keyword_values)}",
            })

    return not failures, failures


def validate_script_v2(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []

    _, basic_failures = validate_scene_basics(script, plan)
    failures.extend(basic_failures)

    scenes = script.get("scenes", []) if isinstance(script, dict) else []
    if isinstance(scenes, list) and len(scenes) >= 3:
        first5_ok, first5_reason = validate_first5_progression(scenes)
        if not first5_ok:
            failures.append({
                "scene_index": _scene_index_from_reason(first5_reason) or 3,
                "reason": first5_reason,
            })

        density_ok, density_reason = validate_density(scenes)
        if not density_ok:
            failures.append({
                "scene_index": _scene_index_from_reason(density_reason),
                "reason": density_reason,
            })

        failures.extend(validate_new_information(scenes, plan))

    deduped = []
    seen = set()
    for failure in failures:
        key = (failure.get("scene_index"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)

    return {
        "valid": not deduped,
        "failures": deduped,
        "failed_scene_indexes": sorted({
            int(item["scene_index"])
            for item in deduped
            if isinstance(item.get("scene_index"), int)
        }),
        "reasons": [str(item.get("reason", "")) for item in deduped],
    }
