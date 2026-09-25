from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

REPORT_PATH = Path("visual_diversity_preflight.json")
HARD_REPEAT_COUNT = 3
MAX_CONTINUOUS_SOURCE_SECONDS = 6.0
MAX_STATIC_LIKE_SECONDS = 4.0
MEANINGFUL_BEAT_SECONDS = 4.0
FIRST5_MIN_MEANINGFUL_BEATS = 2
NON_INFORMATION_ROLES = {"transition", "atmosphere"}
SUPPORTED_TRANSFORMS = {"WINGLET_FLOW", "WINGLET_VORTEX", "WINGLET_RESULT"}
NON_MEANINGFUL_MOTION = {"zoom", "crop", "small_pan", "slow_zoom", "slow_pan"}


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
    presentation = str((item or {}).get("presentation_variant") or "").strip().upper()
    if presentation and template and ("ANNOTATED" in mode or "EXPLANATORY" in mode):
        return f"presentation:{template}:{presentation}"
    if template in SUPPORTED_TRANSFORMS and ("ANNOTATED" in mode or "EXPLANATORY" in mode):
        return f"transform:{template}"
    return "raw_physical_asset"


def _member(idx, scene, item, asset_id):
    return {
        "scene_index": idx,
        "human_scene_number": idx + 1,
        "role": _role(scene),
        "source_type": str(item.get("mode") or item.get("provider") or ""),
        "physical_signature": str(item.get("physical_signature") or ""),
        "source_asset_id": str(item.get("source_asset_id") or ""),
        "source_id": str(item.get("source_id") or ""),
        "template": _template(item),
        "presentation_variant": str(item.get("presentation_variant") or ""),
        "motion_profile": str(item.get("motion_profile") or ""),
        "information_beat": _norm(scene.get("text")),
        "variant": _variant(scene, item),
        "asset_id": asset_id,
    }


def _duration(item):
    try:
        return max(0.0, float((item or {}).get("duration", 0) or 0))
    except Exception:
        return 0.0


def _motion_profile(item):
    return _norm((item or {}).get("motion_profile")).replace("-", "_")


def _meaningful_visual_signature(scene, item):
    asset = physical_asset_identity(item)
    template = _template(item)
    presentation = _norm((item or {}).get("presentation_variant"))
    mode = _norm((item or {}).get("mode") or (item or {}).get("provider"))
    motion = _motion_profile(item)
    if motion in NON_MEANINGFUL_MOTION:
        motion = ""
    return "|".join(part for part in (asset, template, presentation, mode, motion) if part)


def _timeline_entries(scenes, lineage):
    by_index = {int(x.get("scene_index", -1)): dict(x or {}) for x in list(lineage or [])}
    entries = []
    cursor = 0.0
    for idx, scene in enumerate(scenes):
        item = by_index.get(idx, {})
        duration = _duration(item)
        end = cursor + duration
        entries.append({
            "scene_index": idx,
            "human_scene_number": idx + 1,
            "role": _role(scene),
            "duration": duration,
            "start_sec": cursor,
            "end_sec": end,
            "asset_id": physical_asset_identity(item),
            "signature": _meaningful_visual_signature(scene, item),
            "motion_profile": _motion_profile(item),
        })
        cursor = end
    return entries


def _same_continuous_source_groups(entries):
    groups = []
    current = []
    for entry in entries:
        if entry["role"] in NON_INFORMATION_ROLES or not entry["asset_id"]:
            if current:
                groups.append(current)
                current = []
            continue
        if current and entry["asset_id"] != current[-1]["asset_id"]:
            groups.append(current)
            current = []
        current.append(entry)
    if current:
        groups.append(current)
    return groups


def _meaningful_beat_count(entries, *, until_sec=None):
    previous = None
    count = 0
    for entry in entries:
        if entry["role"] in NON_INFORMATION_ROLES:
            continue
        if until_sec is not None and entry["start_sec"] >= until_sec:
            break
        signature = entry["signature"]
        if not signature:
            continue
        if signature != previous:
            count += 1
            previous = signature
    return count


def _append_group(groups, group_id, members, *, group_type):
    info = [m for m in members if m["role"] not in NON_INFORMATION_ROLES]
    if len(info) < 2:
        return False
    counts = Counter(m["variant"] for m in info)
    hard_count = max(counts.values()) if counts else 0
    severity = "high" if hard_count >= HARD_REPEAT_COUNT else "medium"
    groups.append({
        "asset_id": group_id,
        "group_type": group_type,
        "scene_indices": [m["scene_index"] for m in info],
        "human_scene_numbers": [m["human_scene_number"] for m in info],
        "count": len(info),
        "hard_repeat_count": hard_count,
        "severity": severity,
        "members": info,
    })
    return severity == "high"


def evaluate_visual_diversity(scenes, lineage):
    scenes = list(scenes or [])
    by_index = {int(x.get("scene_index", -1)): dict(x or {}) for x in list(lineage or [])}
    physical_groups = defaultdict(list)
    presentation_groups = defaultdict(list)
    information_groups = defaultdict(list)

    for idx, scene in enumerate(scenes):
        role = _role(scene)
        item = by_index.get(idx, {})
        asset_id = physical_asset_identity(item)
        member = _member(idx, scene, item, asset_id)
        if asset_id:
            physical_groups[asset_id].append(member)

        # Run 34616204901: AIRCRAFT_WINDOW_STRESS_V1 used three different
        # claim-derived source_asset_id values, so physical identity alone hid
        # an effectively identical split-screen composition repeated 3 times.
        # Group explanatory renders by template family too.  A real
        # presentation_variant keeps distinct treatments distinct; merely
        # changing the claim-specific asset id does not.
        template = _template(item)
        mode = str(item.get("mode") or "").upper()
        if template and ("ANNOTATED" in mode or "EXPLANATORY" in mode):
            presentation_groups[template].append(member)

        text = _norm(scene.get("text"))
        if text and role not in NON_INFORMATION_ROLES:
            information_groups[text].append(idx)

    groups = []
    hard_failure = False
    for asset_id, members in physical_groups.items():
        hard_failure = _append_group(
            groups, asset_id, members, group_type="physical_asset"
        ) or hard_failure

    for template, members in presentation_groups.items():
        hard_failure = _append_group(
            groups,
            f"presentation-family:{template}",
            members,
            group_type="presentation_family",
        ) or hard_failure

    information = [{
        "information_beat": text,
        "scene_indices": indexes,
        "human_scene_numbers": [i + 1 for i in indexes],
        "count": len(indexes),
        "severity": "warning",
    } for text, indexes in information_groups.items() if len(indexes) >= 2]
    timeline = _timeline_entries(scenes, lineage)
    total_duration = sum(entry["duration"] for entry in timeline)
    meaningful_beats = _meaningful_beat_count(timeline)
    required_beats = (
        int(math.ceil(total_duration / MEANINGFUL_BEAT_SECONDS))
        if total_duration > 0
        else 0
    )
    first5_beats = _meaningful_beat_count(timeline, until_sec=5.0)

    for continuous in _same_continuous_source_groups(timeline):
        duration = sum(entry["duration"] for entry in continuous)
        if duration > MAX_CONTINUOUS_SOURCE_SECONDS:
            hard_failure = True
            groups.append({
                "asset_id": continuous[0]["asset_id"],
                "group_type": "continuous_source_duration",
                "scene_indices": [entry["scene_index"] for entry in continuous],
                "human_scene_numbers": [entry["human_scene_number"] for entry in continuous],
                "duration": duration,
                "max_duration": MAX_CONTINUOUS_SOURCE_SECONDS,
                "severity": "high",
                "members": continuous,
            })
        if len(continuous) == 1 and duration > MAX_STATIC_LIKE_SECONDS:
            motion = continuous[0].get("motion_profile")
            if not motion or motion in NON_MEANINGFUL_MOTION:
                hard_failure = True
                groups.append({
                    "asset_id": continuous[0]["asset_id"],
                    "group_type": "static_like_duration",
                    "scene_indices": [continuous[0]["scene_index"]],
                    "human_scene_numbers": [continuous[0]["human_scene_number"]],
                    "duration": duration,
                    "max_duration": MAX_STATIC_LIKE_SECONDS,
                    "severity": "high",
                    "members": continuous,
                })

    beat_failures = []
    if total_duration > 0 and meaningful_beats < required_beats:
        hard_failure = True
        beat_failures.append({
            "type": "insufficient_meaningful_visual_beats",
            "count": meaningful_beats,
            "required": required_beats,
            "severity": "high",
        })
    if total_duration >= 5.0 and first5_beats < FIRST5_MIN_MEANINGFUL_BEATS:
        hard_failure = True
        beat_failures.append({
            "type": "insufficient_first5_visual_change",
            "count": first5_beats,
            "required": FIRST5_MIN_MEANINGFUL_BEATS,
            "severity": "high",
        })
    return {
        "pass": not hard_failure,
        "hard_repeat_count": HARD_REPEAT_COUNT,
        "max_continuous_source_seconds": MAX_CONTINUOUS_SOURCE_SECONDS,
        "max_static_like_seconds": MAX_STATIC_LIKE_SECONDS,
        "total_duration": total_duration,
        "meaningful_visual_beats": meaningful_beats,
        "required_meaningful_visual_beats": required_beats,
        "first5_meaningful_visual_beats": first5_beats,
        "first5_required_meaningful_visual_beats": FIRST5_MIN_MEANINGFUL_BEATS,
        "repetition_groups": groups,
        "beat_failures": beat_failures,
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
