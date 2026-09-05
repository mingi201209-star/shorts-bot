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

# Run 33976145878 Human QA: the fixed flap production passed the generic
# aircraft+wing contract even when the selected stock did not visibly establish
# the trailing-edge flap itself. Treat flap as the concrete component named by
# the narration. This strengthens identity only; no score/floor/retry/API policy
# changes are introduced.
_QUERY_ANCHOR_GROUPS["flap"] = {"flap", "flaps"}
_CONCRETE_COMPONENT_ANCHORS.add("flap")
_VISUAL_SOURCE_ANCHOR_ALIASES["flap"] = (
    "플랩", "날개 플랩", "날개 뒤쪽 플랩", "후연 플랩",
    "flap", "flaps", "wing flap", "wing flaps",
    "trailing-edge flap", "trailing edge flap",
)
_VISUAL_ANCHOR_PREFERRED_TERM["flap"] = "flap"
if "flap" not in _VISUAL_ANCHOR_ORDER:
    _anchor_order = list(_VISUAL_ANCHOR_ORDER)
    try:
        _wing_index = _anchor_order.index("wing") + 1
    except ValueError:
        _wing_index = len(_anchor_order)
    _anchor_order.insert(_wing_index, "flap")
    _VISUAL_ANCHOR_ORDER = tuple(_anchor_order)

# V1 intentionally preserves historical aircraft+wing exact behavior. When a
# flap is explicitly present, extend that pair to the concrete third component
# instead of allowing the V1 two-anchor compatibility shortcut to erase it.
_visual_subject_anchor_v2_previous_extract_query_anchors = extract_query_anchors


def extract_query_anchors(query):
    anchors = list(_visual_subject_anchor_v2_previous_extract_query_anchors(query))
    words = set(normalize_search_query(query).split())
    flap_aliases = _QUERY_ANCHOR_GROUPS.get("flap", {"flap", "flaps"})
    if words & flap_aliases and "flap" not in anchors:
        if "wing" in anchors:
            anchors = [anchor for anchor in anchors if anchor != "flap"]
            anchors.append("flap")
        else:
            anchors.append("flap")
    return _dedupe_words(anchors)[:3]


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

    visual_type = str(contract.get("visual_type") or "real_world_broll")
    if visual_type == "real_world_broll" and _explicit_chroma_stock(candidate):
        return 6, "EXPLICIT_CHROMA_STOCK_REJECTED"
    return tier, label
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual Subject Anchor Contract V2 applied: compound aviation identity + explicit chroma fail-close")

# Run 33249110048: physical subject contract survives specificity fallback.
import ci_visual_subject_anchor_fallback_inheritance_hotfix  # noqa: F401,E402
# Run 33250343057: grounded explanatory relation survives the same fallback.
import ci_visual_claim_semantic_fallback_hotfix  # noqa: F401,E402
# Run 33251901169: strengthen opening supply only after #253/#254 guards exist.
import ci_canonical_visual_supply_contract_hotfix as _canonical_visual_supply  # noqa: E402
_canonical_visual_supply.main()
