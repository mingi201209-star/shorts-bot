from pathlib import Path


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_SUBJECT_ANCHOR_COMPOUND_PHYSICAL_V2"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_SUBJECT_ANCHOR_COMPOUND_PHYSICAL_V2
# Run 33248013901 exposed a lexical false positive after Script grounding was
# already correct: "jet engine flow interface" could be satisfied by a gas
# stove tagged "Unreal Engine", and "jet engine chevron flow mixing" by a
# clock mechanism tagged "engine/engineering". Preserve compound physical
# identity at retrieval without adding providers, retries, thresholds or calls.
_QUERY_ANCHOR_GROUPS.setdefault("aircraft", set()).update({"jet", "jets"})
_QUERY_ANCHOR_GROUPS["chevron"] = {
    "chevron", "chevrons", "serrated", "serration", "serrations",
}
_CONCRETE_COMPONENT_ANCHORS.add("chevron")
_VISUAL_SOURCE_ANCHOR_ALIASES["chevron"] = (
    "톱니", "톱니 모양", "셰브론", "쉐브론", "chevron", "chevrons",
    "serrated nozzle", "serrated edge",
)
_VISUAL_ANCHOR_PREFERRED_TERM["chevron"] = "chevron"
if "chevron" not in _VISUAL_ANCHOR_ORDER:
    _VISUAL_ANCHOR_ORDER = tuple(
        list(_VISUAL_ANCHOR_ORDER[:2]) + ["chevron"] + list(_VISUAL_ANCHOR_ORDER[2:])
    )


def _candidate_text_for_visual_contract(candidate):
    if not isinstance(candidate, dict):
        return ""
    values = (
        candidate.get("title"), candidate.get("tags"), candidate.get("description"),
        candidate.get("metadata"), candidate.get("source_url"), candidate.get("url"),
    )
    return " ".join(str(value or "").lower() for value in values)


def _explicit_chroma_stock(candidate):
    value = _candidate_text_for_visual_contract(candidate)
    return any(token in value for token in (
        "green screen", "green-screen", "greenscreen",
        "chroma key", "chroma-key", "chromakey",
    ))


_visual_subject_anchor_v2_previous_general_scene_tier = general_scene_unknown_safe_tier


def general_scene_unknown_safe_tier(candidate, scene_query):
    tier, label = _visual_subject_anchor_v2_previous_general_scene_tier(candidate, scene_query)
    contract = get_current_visual_subject_anchor_contract()
    if not bool(contract.get("required")):
        return tier, label
    if normalize_search_query(scene_query) != normalize_search_query(contract.get("effective_query")):
        return tier, label

    # A stock clip that explicitly advertises an unkeyed chroma background is
    # not acceptable real-world evidence. This is metadata fail-close, not a
    # score/threshold relaxation and does not consume another retrieval retry.
    visual_type = str(contract.get("visual_type") or "real_world_broll")
    if visual_type == "real_world_broll" and _explicit_chroma_stock(candidate):
        return 6, "EXPLICIT_CHROMA_STOCK_REJECTED"
    return tier, label
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual Subject Anchor Contract V2 applied: compound aviation identity + explicit chroma fail-close")
