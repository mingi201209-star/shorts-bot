from pathlib import Path


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_CLAIM_SEMANTIC_FALLBACK_V1"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_CLAIM_SEMANTIC_FALLBACK_V1
# Run 33250343057 proved subject identity alone is insufficient for grounded
# explanatory Scenes: `jet engine flow interface` fell back to generic
# `airplane engine detail`. Preserve the original grounded query's explanatory
# relation across the entire specificity ladder. No thresholds/retries/API calls.
_VISUAL_EXPLANATORY_TERM_GROUPS = {
    "flow": {"flow", "flows", "airflow", "exhaust", "stream", "streams", "plume", "plumes"},
    "interface": {"interface", "boundary", "boundaries", "junction", "meeting", "meet"},
    "mixing": {"mix", "mixes", "mixed", "mixing", "blend", "blending"},
    "noise": {"noise", "noisy", "sound", "acoustic", "acoustics", "decibel", "decibels"},
    "reduction": {"reduce", "reduces", "reduced", "reduction", "lower", "lowering", "quieter", "quiet"},
}
_VISUAL_EXPLANATORY_GENERIC = {
    "aircraft", "airplane", "airliner", "aviation", "jet", "engine", "engines",
    "nacelle", "nacelles", "nozzle", "nozzles", "chevron", "chevrons",
    "serrated", "serration", "detail", "mechanism", "stage", "design",
}


def _explanatory_anchor_groups(value):
    words = set(normalize_search_query(value).split())
    found = []
    for canonical, aliases in _VISUAL_EXPLANATORY_TERM_GROUPS.items():
        if words & aliases:
            found.append(canonical)
    return found


def _required_explanatory_anchors(contract):
    if not isinstance(contract, dict) or not bool(contract.get("required")):
        return []
    authority = str(contract.get("effective_query") or contract.get("original_query") or "")
    groups = _explanatory_anchor_groups(authority)
    # Only enforce explanatory semantics when the grounded/effective Scene query
    # actually contains a relation beyond physical subject identity.
    return [group for group in groups if group not in _VISUAL_EXPLANATORY_GENERIC]


def _candidate_explanatory_anchors(candidate):
    return _explanatory_anchor_groups(_candidate_text_for_visual_contract(candidate))


_visual_claim_semantic_previous_general_scene_tier = general_scene_unknown_safe_tier


def general_scene_unknown_safe_tier(candidate, scene_query):
    tier, label = _visual_claim_semantic_previous_general_scene_tier(candidate, scene_query)
    contract = get_current_visual_subject_anchor_contract()
    required = _required_explanatory_anchors(contract)
    if not required:
        return tier, label

    present = set(_candidate_explanatory_anchors(candidate))
    # The fallback query may broaden, but candidate evidence must still retain at
    # least one explanatory relation from the authoritative grounded Scene query.
    # This prevents generic aircraft/engine footage from satisfying flow/noise
    # explanation Scenes while allowing trusted semantic aliases such as
    # airflow/exhaust and noise/acoustic.
    if not (present & set(required)):
        return 5, "REQUIRED_EXPLANATORY_ANCHOR_MISSING"
    return tier, label


_visual_claim_semantic_previous_selection = get_last_final_visual_selection


def get_last_final_visual_selection():
    selection = _visual_claim_semantic_previous_selection()
    contract = get_current_visual_subject_anchor_contract()
    selection["required_explanatory_anchors"] = _required_explanatory_anchors(contract)
    return selection
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual Claim Semantic fallback V1 applied: explanatory relation survives specificity ladder")
