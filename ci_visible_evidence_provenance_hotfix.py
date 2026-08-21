from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Extend the existing Hook vision call to expose component-level visibility provenance.
# No additional model/API call is introduced.
path = Path("video/hook_visual_dominance.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    '        "reason": str(payload.get("reason", "")).strip()[:500],\n',
    '        "reason": str(payload.get("reason", "")).strip()[:500],\n'
    '        "visible_components": [str(item).strip().lower() for item in payload.get("visible_components", []) if str(item).strip()],\n',
    1,
)
text = text.replace(
    '- vertical_crop_subject_visible: false if the 9:16 crop makes the promised subject small, cut off, peripheral, or hard to identify.\n',
    '- vertical_crop_subject_visible: false if the 9:16 crop makes the promised subject small, cut off, peripheral, or hard to identify.\n'
    '- visible_components: list ONLY concrete components actually visible in the supplied frames. Never infer a component from Hook text, query, title, tags, or metadata. Example: wing/cloud view from a window may have aircraft visible but window absent.\n',
    1,
)
text = text.replace(
    '  "vertical_crop_subject_visible": false,\n  "reason": "short concrete explanation"\n',
    '  "vertical_crop_subject_visible": false,\n  "visible_components": ["aircraft", "window"],\n  "reason": "short concrete explanation"\n',
    1,
)
path.write_text(text, encoding="utf-8")


# Separate semantic context from actual frame-visible evidence. Unknown is explicit.
path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "VISIBLE_EVIDENCE_PROVENANCE_GATE",
    r'''
# VISIBLE_EVIDENCE_PROVENANCE_GATE
_VISUAL_EVIDENCE_REGISTRY = {}


def _visual_evidence_key(candidate):
    return _candidate_unique_key(candidate)


def register_visual_evidence(candidate, *, visible_components=None, source="visual/vision", definitive=True):
    key = _visual_evidence_key(candidate)
    components = {str(item).strip().lower() for item in (visible_components or []) if str(item).strip()}
    _VISUAL_EVIDENCE_REGISTRY[key] = {
        "source": source,
        "definitive": bool(definitive),
        "visible_components": components,
    }


def candidate_visible_component_evidence(candidate, scene_query):
    semantic = concrete_visual_evidence(candidate, scene_query)
    required = list(semantic.get("required") or [])
    record = _VISUAL_EVIDENCE_REGISTRY.get(_visual_evidence_key(candidate))
    if not required:
        return {
            "state": "TRUE",
            "required": [],
            "visible": [],
            "source": "not_required",
            "semantic": semantic,
        }
    if not record or not record.get("definitive"):
        return {
            "state": "UNKNOWN",
            "required": required,
            "visible": [],
            "source": "none",
            "semantic": semantic,
        }
    visible = set(record.get("visible_components") or set())
    matched = [anchor for anchor in required if anchor in visible]
    return {
        "state": "TRUE" if len(matched) == len(required) else "FALSE",
        "required": required,
        "visible": matched,
        "source": str(record.get("source") or "visual/vision"),
        "semantic": semantic,
    }


_visible_previous_visual_specificity_decision = visual_specificity_decision


def visual_specificity_decision(candidate, scene_query):
    decision = _visible_previous_visual_specificity_decision(candidate, scene_query)
    visual = candidate_visible_component_evidence(candidate, scene_query)
    decision["visual_evidence_state"] = visual["state"]
    decision["visual_evidence_source"] = visual["source"]
    decision["visible_components"] = visual["visible"]
    # Concrete direct/close tiers require actual visual evidence. Semantic completeness
    # alone cannot promote UNKNOWN/FALSE into those tiers.
    if visual["required"] and visual["state"] != "TRUE" and decision["level"] <= 3:
        decision["level"] = 4 if visual["semantic"].get("detected") else 5
        decision["label"] = (
            "semantic_only_visibility_unknown"
            if visual["state"] == "UNKNOWN"
            else "visual_component_not_visible"
        )
        decision["confidence"] = "low" if visual["state"] == "UNKNOWN" else "very_low"
    return decision


def safe_reuse_candidate(scene_query):
    # Only visually verified reuse may outrank an unverified fresh concrete candidate.
    eligible = []
    for key, candidate in _SAFE_REUSE_HISTORY.items():
        if _SAFE_REUSE_COUNTS.get(key, 0) >= _SAFE_REUSE_MAX:
            continue
        visual = candidate_visible_component_evidence(candidate, scene_query)
        if visual["state"] != "TRUE":
            continue
        decision = visual_specificity_decision(candidate, scene_query)
        if decision["level"] <= 3:
            eligible.append((decision["level"], _SAFE_REUSE_COUNTS.get(key, 0), candidate))
    if not eligible:
        return None
    eligible.sort(key=lambda item: (item[0], item[1]))
    reused = dict(eligible[0][2])
    reused["_safe_reuse"] = True
    reused["_safe_reuse_key"] = _safe_reuse_key(eligible[0][2])
    reused["_safe_reuse_next_count"] = _SAFE_REUSE_COUNTS.get(reused["_safe_reuse_key"], 0) + 1
    return reused


def visual_evidence_diagnostic(candidate, scene_query):
    semantic = concrete_visual_evidence(candidate, scene_query)
    visual = candidate_visible_component_evidence(candidate, scene_query)
    decision = visual_specificity_decision(candidate, scene_query)
    print(
        "[VISUAL_EVIDENCE] "
        f"candidate={candidate.get('source_id', candidate.get('id'))} "
        f"semantic_anchors={'+'.join(extract_query_anchors(scene_query)) or 'none'} "
        f"semantic_evidence={'+'.join(semantic.get('detected', [])) or 'none'} "
        f"required_visible={'+'.join(visual.get('required', [])) or 'none'} "
        f"visual_evidence={visual['state']} "
        f"visible={'+'.join(visual.get('visible', [])) or 'none'} "
        f"provenance={visual['source']} tier={decision['label']}"
    )
    return visual
''',
)
path.write_text(text, encoding="utf-8")


# Hook selector: register only the existing vision result as actual visual evidence.
path = Path("video/hook_visual.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    concrete_visual_evidence,\n)",
    "    concrete_visual_evidence,\n    register_visual_evidence,\n    candidate_visible_component_evidence,\n)",
    1,
)
text = text.replace(
    "            item[\"dominance\"] = dominance\n            if dominance.get(\"pass\"):\n",
    "            item[\"dominance\"] = dominance\n"
    "            register_visual_evidence(\n"
    "                item[\"candidate\"],\n"
    "                visible_components=dominance.get(\"visible_components\", []),\n"
    "                source=\"hook_dominance_vision\",\n"
    "                definitive=True,\n"
    "            )\n"
    "            visual = candidate_visible_component_evidence(item[\"candidate\"], search_query)\n"
    "            print(\n"
    "                \"[VISUAL_EVIDENCE] \"\n"
    "                f\"hook=true candidate={item['candidate'].get('source_id', item['candidate'].get('id'))} \"\n"
    "                f\"required_visible={'+'.join(visual['required']) or 'none'} \"\n"
    "                f\"visual_evidence={visual['state']} provenance={visual['source']}\"\n"
    "            )\n"
    "            if dominance.get(\"pass\") and visual[\"state\"] == \"TRUE\":\n",
    1,
)
path.write_text(text, encoding="utf-8")

print("✅ Visible evidence provenance gate applied without additional vision calls")
