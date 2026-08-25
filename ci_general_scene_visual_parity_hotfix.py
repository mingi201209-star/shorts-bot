from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "GENERAL_SCENE_VISUAL_PARITY_UNKNOWN_SAFE",
    r'''
# GENERAL_SCENE_VISUAL_PARITY_UNKNOWN_SAFE
# No new frame/vision API is introduced here. Existing #26 visual evidence is
# authoritative when present; otherwise UNKNOWN stays UNKNOWN and is ranked by
# semantic/domain integrity instead of being promoted to visible evidence.


def _general_scene_strengthening_applicable(scene_query):
    anchors = extract_query_anchors(scene_query)
    if not anchors:
        return False
    return bool(_visual_is_concrete_query(scene_query) or len(anchors) >= 1)


def _missing_required_aviation_component_anchor(candidate, scene_query):
    anchors = set(extract_query_anchors(scene_query))
    if "aircraft" not in anchors or not (anchors & {"wing", "window"}):
        return False
    compatibility = candidate_anchor_compatibility(candidate, scene_query)
    total = int(compatibility.get("total", 0) or 0)
    matched = int(compatibility.get("matched", 0) or 0)
    return total >= 2 and matched < total


def general_scene_unknown_safe_tier(candidate, scene_query):
    visual = candidate_visible_component_evidence(candidate, scene_query)
    semantic = concrete_visual_evidence(candidate, scene_query)
    compatibility = candidate_anchor_compatibility(candidate, scene_query)
    decision = visual_specificity_decision(candidate, scene_query)
    state = str(visual.get("state") or "UNKNOWN").upper()
    specific_hits = int(decision.get("specific_hits", 0) or 0)
    specific_total = int(decision.get("specific_total", 0) or 0)
    mechanism_specific = specific_total > 0 and specific_hits >= max(1, (specific_total + 1) // 2)

    # Run 32796378299: metadata-only aircraft evidence must not satisfy a
    # concrete wing/window query when the required component anchor is absent.
    if state == "UNKNOWN" and _missing_required_aviation_component_anchor(candidate, scene_query):
        return 5, "MISSING_REQUIRED_AVIATION_COMPONENT_UNKNOWN"

    if state == "TRUE" and int(decision.get("level", 99)) <= 3:
        return 1, "VISUALLY_VERIFIED_DIRECT"
    if state == "UNKNOWN" and bool(semantic.get("complete")) and bool(compatibility.get("compatible")) and mechanism_specific:
        return 3, "SEMANTIC_COMPLETE_UNKNOWN"
    if state == "UNKNOWN" and int(compatibility.get("matched", 0)) > 0:
        return 4, "SAME_DOMAIN_CONTEXTUAL_UNKNOWN"
    if state == "FALSE":
        if int(compatibility.get("matched", 0)) > 0:
            return 5, "VISUAL_FALSE_CONTEXTUAL"
        return 6, "VISUAL_FALSE_CROSS_DOMAIN"
    if bool(decision.get("abstract")) or int(compatibility.get("matched", 0)) == 0:
        return 5, "CROSS_DOMAIN_OR_ABSTRACT_UNKNOWN"
    return 6, "LAST_RESORT"


def semantic_safe_reuse_candidate(scene_query):
    eligible = []
    for key, candidate in _SAFE_REUSE_HISTORY.items():
        if _SAFE_REUSE_COUNTS.get(key, 0) >= _SAFE_REUSE_MAX:
            continue
        visual = candidate_visible_component_evidence(candidate, scene_query)
        if str(visual.get("state") or "UNKNOWN").upper() == "FALSE":
            continue
        semantic = concrete_visual_evidence(candidate, scene_query)
        compatibility = candidate_anchor_compatibility(candidate, scene_query)
        if not semantic.get("complete") or not compatibility.get("compatible"):
            continue
        if str(visual.get("state") or "UNKNOWN").upper() == "TRUE":
            continue
        tier, _ = general_scene_unknown_safe_tier(candidate, scene_query)
        if tier > 4:
            continue
        eligible.append((tier, _SAFE_REUSE_COUNTS.get(key, 0), candidate))

    if not eligible:
        return None
    eligible.sort(key=lambda item: (item[0], item[1], int(item[2].get("search_position", 9999))))
    reused = dict(eligible[0][2])
    reused["_safe_reuse"] = True
    reused["_semantic_safe_reuse"] = True
    reused["_safe_reuse_key"] = _safe_reuse_key(eligible[0][2])
    reused["_safe_reuse_next_count"] = _SAFE_REUSE_COUNTS.get(reused["_safe_reuse_key"], 0) + 1
    return reused


_general_parity_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    if not candidates or not subject_filter_query or historical or not _general_scene_strengthening_applicable(subject_filter_query):
        return _general_parity_previous_choose_best_candidate(
            candidates,
            relevant_top_n=relevant_top_n,
            historical=historical,
            subject_filter_query=subject_filter_query,
        )

    fresh = [item for item in candidates if not _candidate_is_used(item)]
    ranked = []
    for item in fresh:
        tier, label = general_scene_unknown_safe_tier(item, subject_filter_query)
        ranked.append((tier, int(item.get("search_position", 9999)), label, item))

    selected = None
    selected_mode = None
    selected_tier = 99

    if ranked:
        best_tier = min(item[0] for item in ranked)
        tier_pool = [item[3] for item in ranked if item[0] == best_tier]
        selected = _general_parity_previous_choose_best_candidate(
            tier_pool,
            relevant_top_n=relevant_top_n,
            historical=historical,
            subject_filter_query=subject_filter_query,
        )
        if selected is not None:
            selected_tier, selected_mode = general_scene_unknown_safe_tier(selected, subject_filter_query)

    verified_reuse = safe_reuse_candidate(subject_filter_query)
    if verified_reuse is not None and selected_tier > 1:
        selected = verified_reuse
        selected_tier = 2
        selected_mode = "VERIFIED_COMPATIBLE_REUSE"

    if selected_tier >= 4:
        semantic_reuse = semantic_safe_reuse_candidate(subject_filter_query)
        if semantic_reuse is not None:
            selected = semantic_reuse
            selected_tier = 3
            selected_mode = "SEMANTIC_SAFE_REUSE"

    anchors = extract_query_anchors(subject_filter_query)
    # For anchored scenes, never fill with cross-domain/abstract stock. Returning
    # None lets existing retry/AI/contextual fallback paths handle the scene.
    if anchors and selected is not None and selected_tier >= 5:
        print(
            "[GENERAL_VISUAL_REJECT] "
            f"candidate={selected.get('source_id', selected.get('id'))} "
            f"anchors={'+'.join(anchors)} tier={selected_tier} reason=cross_domain"
        )
        selected = None
        selected_mode = "REJECTED_CROSS_DOMAIN"

    if selected is None and not anchors:
        selected = _general_parity_previous_choose_best_candidate(
            candidates,
            relevant_top_n=relevant_top_n,
            historical=historical,
            subject_filter_query=subject_filter_query,
        )
        if selected is not None:
            selected_tier, selected_mode = general_scene_unknown_safe_tier(selected, subject_filter_query)

    if selected is not None:
        visual = candidate_visible_component_evidence(selected, subject_filter_query)
        compatibility = candidate_anchor_compatibility(selected, subject_filter_query)
        print(
            "[GENERAL_VISUAL_PARITY] "
            f"candidate={selected.get('source_id', selected.get('id'))} "
            f"visual={visual.get('state', 'UNKNOWN')} "
            f"anchor={compatibility.get('matched', 0)}/{compatibility.get('total', 0)} "
            f"tier={selected_tier} mode={selected_mode or 'UNKNOWN'} "
            f"reuse={str(bool(selected.get('_safe_reuse'))).lower()}"
        )
    return selected
''',
)
path.write_text(text, encoding="utf-8")

print("✅ General-scene visual parity + UNKNOWN-safe selection applied; cross-domain anchored stock blocked")
