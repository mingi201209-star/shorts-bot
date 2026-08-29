from pathlib import Path


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_SUBJECT_ANCHOR_REQUIRED_SELECTION_V1"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_SUBJECT_ANCHOR_REQUIRED_SELECTION_V1
_visual_subject_anchor_previous_general_scene_tier = general_scene_unknown_safe_tier


def general_scene_unknown_safe_tier(candidate, scene_query):
    tier, label = _visual_subject_anchor_previous_general_scene_tier(candidate, scene_query)
    contract = get_current_visual_subject_anchor_contract()
    if not bool(contract.get("required")):
        return tier, label
    if normalize_search_query(scene_query) != normalize_search_query(contract.get("effective_query")):
        return tier, label

    required = list(contract.get("required_anchors") or [])
    compatibility = candidate_anchor_compatibility(candidate, scene_query)
    total = int(compatibility.get("total", 0) or 0)
    matched = int(compatibility.get("matched", 0) or 0)

    # A source-derived concrete subject is a contract, not a soft relevance hint.
    # Do not let a single overlapping token (e.g. car 'engine') restore tier 4.
    if required and total <= 0:
        return 6, "MISSING_REQUIRED_SUBJECT_ANCHOR"
    if required and matched < total:
        return 5, "REQUIRED_SUBJECT_ANCHOR_INCOMPLETE"
    return tier, label
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual Subject Anchor Contract V1 completion applied: partial required anchors fail closed")
