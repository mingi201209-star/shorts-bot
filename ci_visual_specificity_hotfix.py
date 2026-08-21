from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "VISUAL_SPECIFICITY_ANTI_GENERIC",
    r'''
# VISUAL_SPECIFICITY_ANTI_GENERIC
_VISUAL_SPECIFICITY_BROAD_TERMS = {
    "airplane", "aircraft", "plane", "aviation", "flight", "airport",
    "building", "city", "road", "bridge", "tunnel", "people", "person",
    "video", "scene", "view", "shot", "close", "closeup", "detail",
}
_VISUAL_SPECIFICITY_MODIFIER_TERMS = {
    "small", "tiny", "little", "multiple", "several", "inside", "outside",
    "showing", "visible", "structure", "mechanism", "system",
}
_VISUAL_ABSTRACT_TERMS = {
    "abstract", "animation", "animated", "network", "particles", "particle",
    "ink", "liquid", "fluid", "jellyfish", "animal", "animals", "cloud",
    "clouds", "ocean", "sea", "smoke", "bokeh", "ambient", "decorative",
    "metaphor", "metaphorical", "pattern", "patterns", "swirl", "swirling",
}


def _visual_specificity_terms(scene_query):
    words = normalize_search_query(scene_query).split()
    return [
        word for word in words
        if len(word) >= 3
        and word not in _VISUAL_SPECIFICITY_BROAD_TERMS
        and word not in _VISUAL_SPECIFICITY_MODIFIER_TERMS
    ]


def _visual_candidate_words(candidate):
    return set(_candidate_metadata(candidate).split())


def _visual_is_concrete_query(scene_query):
    return bool(_visual_specificity_terms(scene_query))


def visual_specificity_decision(candidate, scene_query):
    """Return bounded specificity level (1 best, 5 abstract fallback)."""
    required = _visual_specificity_terms(scene_query)
    metadata_words = _visual_candidate_words(candidate)
    hits = [word for word in required if word in metadata_words]
    abstract = bool(metadata_words & _VISUAL_ABSTRACT_TERMS)

    if required and len(hits) == len(required):
        level = 1
        label = "exact_subject"
    elif required and len(hits) >= max(1, (len(required) + 1) // 2):
        level = 2
        label = "same_object_component"
    elif hits:
        level = 3
        label = "close_semantic"
    else:
        level = 4
        label = "generic_contextual"

    # Concrete narration should prefer even generic contextual footage over
    # decorative/metaphorical footage. Keep it as a bounded last fallback so
    # scarcity does not fail production outright.
    if _visual_is_concrete_query(scene_query) and abstract:
        level = 5
        label = "abstract_metaphorical_fallback"

    confidence = {
        1: "high",
        2: "medium_high",
        3: "medium",
        4: "low",
        5: "very_low",
    }[level]
    return {
        "level": level,
        "label": label,
        "confidence": confidence,
        "specific_hits": len(hits),
        "specific_total": len(required),
        "abstract": abstract,
    }


_visual_specificity_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(
    candidates,
    relevant_top_n=None,
    *,
    historical=False,
    subject_filter_query=None,
):
    if candidates and subject_filter_query and not historical:
        decisions = [
            (visual_specificity_decision(item, subject_filter_query), item)
            for item in candidates
        ]
        best_level = min((decision["level"] for decision, _ in decisions), default=5)
        tier = [
            item for decision, item in decisions
            if decision["level"] == best_level
        ]
        selected = _visual_specificity_previous_choose_best_candidate(
            tier,
            relevant_top_n=relevant_top_n,
            historical=historical,
            subject_filter_query=subject_filter_query,
        )
        if selected:
            decision = visual_specificity_decision(selected, subject_filter_query)
            print(
                "[VISUAL_SPECIFICITY] "
                f"level={decision['level']} label={decision['label']} "
                f"confidence={decision['confidence']} "
                f"hits={decision['specific_hits']}/{decision['specific_total']} "
                f"abstract={str(decision['abstract']).lower()} "
                f"tier={len(tier)}/{len(candidates)}"
            )
            return selected

    return _visual_specificity_previous_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
''',
)
path.write_text(text, encoding="utf-8")

print("✅ Visual specificity + anti-generic B-roll hotfix applied")
