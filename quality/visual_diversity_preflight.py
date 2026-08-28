from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPORT_PATH = Path("visual_diversity_preflight.json")
HARD_REPEAT_COUNT = 3
NON_INFORMATION_ROLES = {"transition", "atmosphere"}
SUPPORTED_TRANSFORMS = {"WINGLET_FLOW", "WINGLET_VORTEX", "WINGLET_RESULT"}


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _role(scene):
    return _norm(scene.get("role") or scene.get("scene_role")) or "setup"


def physical_asset_identity(item):
    item = dict(item or {})
    for key in ("physical_signature", "source_asset_id", "source_id"):
        value = _norm(item.get(key))
        if value:
            return value
    metadata = _norm(item.get("metadata"))
    match = re.search(r"(?:asset|file|path)=([^|]+)", metadata)
    return _norm(match.group(1)) if match else ""


def _template(item):
    value = str((item or {}).get("template_type") or "").strip().upper()
    if value:
        return value
    metadata = str((item or {}).get("metadata") or "").upper()
    return next((t for t in SUPPORTED_TRANSFORMS if t in metadata), "")


def _variant(scene, item):
    template = _template(item)
    mode = str((item or {}).get("mode") or "").upper()
    if template in SUPPORTED_TRANSFORMS and ("ANNOTATED" in mode or "EXPLANATORY" in mode):
        return f"transform:{template}"
    return "raw_physical_asset"


def evaluate_visual_diversity(scenes, lineage):
    scenes = list(scenes or [])
    by_index = {int(x.get("scene_index", -1)): dict(x or {}) for x in list(lineage or [])}
    physical_groups = defaultdict(list)
    information_groups = defaultdict(list)
    for idx, scene in enumerate(scenes):
        role = _role(scene)
        item = by_index.get(idx, {})
        asset_id = physical_asset_identity(item)
        if asset_id:
            physical_groups[asset_id].append({
                "scene_index": idx,
                "human_scene_number": idx + 1,
                "role": role,
                "source_type": str(item.get("mode") or item.get("provider") or ""),
                "physical_signature": str(item.get("physical_signature") or ""),
                "source_asset_id": str(item.get("source_asset_id") or ""),
                "source_id": str(item.get("source_id") or ""),
                "template": _template(item),
                "information_beat": _norm(scene.get("text")),
                "variant": _variant(scene, item),
            })
        text = _norm(scene.get("text"))
        if text and role not in NON_INFORMATION_ROLES:
            information_groups[text].append(idx)

    groups = []
    hard_failure = False
    for asset_id, members in physical_groups.items():
        info = [m for m in members if m["role"] not in NON_INFORMATION_ROLES]
        if len(info) < 2:
            continue
        counts = Counter(m["variant"] for m in info)
        hard_count = max(counts.values()) if counts else 0
        severity = "high" if hard_count >= HARD_REPEAT_COUNT else "medium"
        hard_failure = hard_failure or severity == "high"
        groups.append({
            "asset_id": asset_id,
            "scene_indices": [m["scene_index"] for m in info],
            "human_scene_numbers": [m["human_scene_number"] for m in info],
            "count": len(info),
            "hard_repeat_count": hard_count,
            "severity": severity,
            "members": info,
        })

    information = [{
        "information_beat": text,
        "scene_indices": indexes,
        "human_scene_numbers": [i + 1 for i in indexes],
        "count": len(indexes),
        "severity": "warning",
    } for text, indexes in information_groups.items() if len(indexes) >= 2]
    return {
        "pass": not hard_failure,
        "hard_repeat_count": HARD_REPEAT_COUNT,
        "repetition_groups": groups,
        "information_beat_repetition": information,
        "capability_exhausted": False,
    }


def plan_bounded_diversity_repair(result, scenes, max_repairs=2):
    scenes = list(scenes or [])
    chosen = []
    priority = {"mechanism": 0, "cause": 1, "solution": 1, "result": 2, "conclusion": 2}
    for group in result.get("repetition_groups") or []:
        if group.get("severity") != "high":
            continue
        needed = int(group.get("hard_repeat_count", 0)) - 2
        candidates = []
        for member in group.get("members", []):
            if member.get("variant") != "raw_physical_asset":
                continue
            idx = int(member["scene_index"])
            if not (0 <= idx < len(scenes)):
                continue
            try:
                from video.visual_explanation import annotation_fact_safe, plan_explanation
                plan = plan_explanation(scenes[idx])
                template = str((plan or {}).get("template") or "").upper()
                if template not in SUPPORTED_TRANSFORMS or not annotation_fact_safe(scenes[idx], plan):
                    continue
            except Exception:
                continue
            candidates.append({
                "scene_index": idx,
                "human_scene_number": idx + 1,
                "excluded_physical_asset_id": group["asset_id"],
                "template": template,
                "role": _role(scenes[idx]),
            })
        candidates.sort(key=lambda x: (priority.get(x["role"], 9), x["scene_index"]))
        if needed > max_repairs or len(candidates) < needed:
            result["capability_exhausted"] = True
            return []
        chosen.extend(candidates[:needed])
    deduped = {x["scene_index"]: x for x in chosen}
    if len(deduped) > max_repairs:
        result["capability_exhausted"] = True
        return []
    return list(deduped.values())


def write_visual_diversity_report(result, path=REPORT_PATH):
    Path(path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
