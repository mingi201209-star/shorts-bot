from pathlib import Path


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_CLAIM_SEMANTIC_FALLBACK_V1"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_CLAIM_SEMANTIC_FALLBACK_V1
# Run 33250343057 proved subject identity alone is insufficient for grounded
# explanatory Scenes: `jet engine flow interface` fell back to generic
# `airplane engine detail`. Preserve the grounded keyword's explanatory nucleus
# across the entire specificity ladder. #251 already derives that authoritative
# keyword deterministically from owned_claim_id + provenance-backed evidence +
# allowed paraphrase scope. No new model call, threshold, retry, or provider.
_VISUAL_EXPLANATORY_TERM_GROUPS = {
    "flow": {"flow", "flows", "airflow", "airflows", "exhaust", "stream", "streams", "plume", "plumes"},
    "interface": {"interface", "interfaces", "boundary", "boundaries", "junction", "junctions", "meeting", "meet"},
    "mixing": {"mix", "mixes", "mixed", "mixing", "blend", "blends", "blended", "blending"},
    "noise": {"noise", "noisy", "sound", "sounds", "acoustic", "acoustics", "decibel", "decibels"},
    "reduction": {"reduce", "reduces", "reduced", "reduction", "decrease", "decreases", "lower", "lowering", "quieter", "quiet"},
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

    # Grounded factual keywords produced by #251 carry a claim-specific semantic
    # nucleus, while opening/establishing queries can contain a lone descriptive
    # word such as `airflow`. Do not turn that lone lexical hint into a factual
    # gate. Two or more independent relation/state groups are required before
    # this layer activates. This preserves non-grounded/legacy/Opening behavior.
    if len(groups) < 2:
        return []
    return groups


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
    missing = [group for group in required if group not in present]

    # The specificity ladder may broaden retrieval wording, but it cannot reduce
    # the original grounded claim semantics. A candidate must retain the complete
    # explanatory nucleus, not merely one overlapping word. General Visual Parity,
    # verified reuse, and contextual fallback all pass through this tier boundary.
    if missing:
        print(
            "[VISUAL_CLAIM_SEMANTIC_REJECT] "
            f"candidate={candidate.get('source_id', candidate.get('id'))} "
            f"required={'+'.join(required)} present={'+'.join(sorted(present)) or 'none'} "
            f"fallback_query={normalize_search_query(scene_query)}"
        )
        return 5, "REQUIRED_EXPLANATORY_ANCHOR_MISSING"
    return tier, label


_visual_claim_semantic_previous_selection = get_last_final_visual_selection


def get_last_final_visual_selection():
    selection = _visual_claim_semantic_previous_selection()
    contract = get_current_visual_subject_anchor_contract()
    required = _required_explanatory_anchors(contract)
    selection["required_explanatory_anchors"] = list(required)
    selection["explanatory_anchor_authority"] = (
        str(contract.get("effective_query") or contract.get("original_query") or "")
        if required else ""
    )
    return selection
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual Claim Semantic fallback V1 applied: complete grounded explanatory nucleus survives specificity ladder")
