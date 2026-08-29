from pathlib import Path


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_SUBJECT_ANCHOR_FALLBACK_INHERITANCE_V1"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_SUBJECT_ANCHOR_FALLBACK_INHERITANCE_V1
# Run 33249110048 proved that the compound subject contract was extracted
# correctly, but specificity-ladder fallback queries could bypass enforcement
# because V1/V2 only applied when scene_query == contract.effective_query.
# Keep the original Scene contract authoritative for every fallback query in
# the same retrieval attempt. No score/threshold/retry/API changes.
_visual_subject_anchor_fallback_previous_general_scene_tier = general_scene_unknown_safe_tier


def _anchor_contract_authority_query(contract, scene_query):
    effective = str((contract or {}).get("effective_query") or "").strip()
    return effective or str(scene_query or "")


def general_scene_unknown_safe_tier(candidate, scene_query):
    tier, label = _visual_subject_anchor_fallback_previous_general_scene_tier(candidate, scene_query)
    contract = get_current_visual_subject_anchor_contract()
    if not bool(contract.get("required")):
        return tier, label

    authority_query = _anchor_contract_authority_query(contract, scene_query)
    required = list(contract.get("required_anchors") or [])
    compatibility = candidate_anchor_compatibility(candidate, authority_query)
    total = int(compatibility.get("total", 0) or 0)
    matched = int(compatibility.get("matched", 0) or 0)

    # The source-derived Scene subject contract survives the entire specificity
    # ladder. A fallback query may broaden retrieval, but it cannot lower the
    # required physical identity or let parity resurrect partial matches.
    if required and total <= 0:
        return 6, "MISSING_REQUIRED_SUBJECT_ANCHOR"
    if required and matched < total:
        return 5, "REQUIRED_SUBJECT_ANCHOR_INCOMPLETE"

    # Chroma metadata is also a property of the selected asset, not of the
    # particular fallback query that found it. Preserve the V2 fail-close rule
    # across every query in the same real-world Scene retrieval contract.
    visual_type = str(contract.get("visual_type") or "real_world_broll")
    if visual_type == "real_world_broll" and _explicit_chroma_stock(candidate):
        return 6, "EXPLICIT_CHROMA_STOCK_REJECTED"

    return tier, label
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual Subject Anchor fallback inheritance applied: Scene contract survives specificity ladder")
