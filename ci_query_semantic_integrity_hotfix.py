from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "QUERY_SEMANTIC_INTEGRITY",
    r'''
# QUERY_SEMANTIC_INTEGRITY
_QUERY_ANCHOR_GROUPS = {
    "aircraft": {"aircraft", "airplane", "plane", "aviation", "airliner"},
    "window": {"window", "windows", "pane", "panes"},
    "wing": {"wing", "wings", "winglet", "winglets"},
    "cabin": {"cabin", "passenger", "interior"},
    "bridge": {"bridge", "bridges"},
    "tunnel": {"tunnel", "tunnels"},
    "road": {"road", "roads", "street", "highway", "motorway"},
    "building": {"building", "buildings", "skyscraper", "tower"},
}
_QUERY_ATTRIBUTE_TERMS = {
    "rounded", "round", "corner", "corners", "shape", "pressure", "structural",
    "structure", "layer", "layers", "hole", "holes", "small", "detail", "closeup",
    "mechanism", "pane", "panes",
}


def extract_query_anchors(query):
    words = set(normalize_search_query(query).split())
    anchors = []
    for canonical, aliases in _QUERY_ANCHOR_GROUPS.items():
        if words & aliases:
            anchors.append(canonical)
    # Aircraft component narration must preserve both the domain and component.
    if "aircraft" in anchors and "window" in anchors:
        return ["aircraft", "window"]
    return anchors[:2]


def _anchor_aliases(anchor):
    return _QUERY_ANCHOR_GROUPS.get(anchor, {anchor})


def candidate_anchor_compatibility(candidate, query):
    anchors = extract_query_anchors(query)
    if not anchors:
        return {"matched": 0, "total": 0, "ratio": 1.0, "compatible": True}
    words = set(_candidate_metadata(candidate).split())
    matched = sum(1 for anchor in anchors if words & _anchor_aliases(anchor))
    return {
        "matched": matched,
        "total": len(anchors),
        "ratio": matched / max(1, len(anchors)),
        "compatible": matched == len(anchors),
    }


def query_relaxation_ladder(query):
    normalized = normalize_search_query(query)
    words = normalized.split()
    if not words:
        return []
    anchors = extract_query_anchors(normalized)
    if not anchors:
        return _general_fallback_queries(normalized)

    anchor_words = []
    for anchor in anchors:
        preferred = "airplane" if anchor == "aircraft" else anchor
        anchor_words.append(preferred)
    attributes = [word for word in words if word in _QUERY_ATTRIBUTE_TERMS and word not in anchor_words]

    variants = []
    def add(parts):
        value = " ".join(_dedupe_words(parts)).strip()
        if value and value != normalized and value not in variants:
            variants.append(value)

    # Relax attributes first; never drop the compound aircraft+window anchor.
    if attributes:
        add(anchor_words + attributes[:2])
    if anchors == ["aircraft", "window"]:
        add(["aircraft", "window", "closeup"])
        add(["airplane", "cabin", "window"])
    else:
        add(anchor_words + ["detail"])
        add(anchor_words)
    return variants[:3]


_query_integrity_previous_general_fallback = _general_fallback_queries


def _general_fallback_queries(query):
    anchors = extract_query_anchors(query)
    if anchors:
        variants = query_relaxation_ladder(query)
        print(
            "[QUERY_SPECIFICITY] "
            f"goal={normalize_search_query(query)} anchors={'+'.join(anchors)} "
            f"ladder={' | '.join(variants) if variants else 'none'}"
        )
        return variants
    return _query_integrity_previous_general_fallback(query)


_query_integrity_previous_visual_decision = visual_specificity_decision


def visual_specificity_decision(candidate, scene_query):
    decision = _query_integrity_previous_visual_decision(candidate, scene_query)
    compatibility = candidate_anchor_compatibility(candidate, scene_query)
    anchors = extract_query_anchors(scene_query)
    if anchors:
        # Full compound-anchor compatibility is required for direct/close tiers.
        if compatibility["compatible"]:
            pass
        elif compatibility["matched"] > 0:
            decision["level"] = max(4, decision["level"])
            decision["label"] = "generic_contextual_anchor_partial"
            decision["confidence"] = "low"
        else:
            decision["level"] = 5
            decision["label"] = "semantic_drift_anchor_missing"
            decision["confidence"] = "very_low"
        decision["anchor_compatibility"] = compatibility["ratio"]
        decision["anchors"] = anchors
    return decision


_query_integrity_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(
    candidates,
    relevant_top_n=None,
    *,
    historical=False,
    subject_filter_query=None,
):
    selected = _query_integrity_previous_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
    if selected and subject_filter_query and not historical:
        decision = visual_specificity_decision(selected, subject_filter_query)
        compatibility = candidate_anchor_compatibility(selected, subject_filter_query)
        print(
            "[SEMANTIC_FALLBACK] "
            f"candidate={selected.get('id')} anchor={compatibility['matched']}/{compatibility['total']} "
            f"tier={decision['label']} fallback_level={decision['level']}"
        )
    return selected
''',
)
path.write_text(text, encoding="utf-8")
print("✅ Search query specificity + semantic fallback integrity applied")
