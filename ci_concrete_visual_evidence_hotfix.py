from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Extend #24 semantic anchors into a concrete evidence contract. No new API/vision call.
path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "CONCRETE_VISUAL_EVIDENCE_SAFE_REUSE",
    r'''
# CONCRETE_VISUAL_EVIDENCE_SAFE_REUSE
_SAFE_REUSE_MAX = 2
_SAFE_REUSE_HISTORY = {}
_SAFE_REUSE_COUNTS = {}
_LAST_SAFE_REUSE_OFFSET = 0.0
_CONCRETE_COMPONENT_ANCHORS = {"window", "wing", "cabin", "bridge", "tunnel", "road", "building"}


def concrete_visual_evidence(candidate, scene_query):
    anchors = extract_query_anchors(scene_query)
    words = set(_candidate_metadata(candidate).split())
    required = list(anchors)
    detected = [
        anchor for anchor in required
        if words & _anchor_aliases(anchor)
    ]
    concrete = bool(
        len(required) >= 2
        or any(anchor in _CONCRETE_COMPONENT_ANCHORS for anchor in required)
    )
    completeness = (
        len(detected) / max(1, len(required))
        if required else 1.0
    )
    return {
        "concrete": concrete,
        "required": required,
        "detected": detected,
        "completeness": completeness,
        "complete": (not concrete) or (bool(required) and len(detected) == len(required)),
    }


_concrete_previous_visual_specificity_decision = visual_specificity_decision


def visual_specificity_decision(candidate, scene_query):
    decision = _concrete_previous_visual_specificity_decision(candidate, scene_query)
    evidence = concrete_visual_evidence(candidate, scene_query)
    decision["required_evidence"] = evidence["required"]
    decision["detected_evidence"] = evidence["detected"]
    decision["evidence_completeness"] = evidence["completeness"]
    if evidence["concrete"] and not evidence["complete"]:
        domain_anchor = evidence["required"][0] if len(evidence["required"]) >= 2 else None
        same_domain = bool(domain_anchor and domain_anchor in evidence["detected"])
        if same_domain:
            # A same-world contextual fallback (e.g. aircraft without visible window)
            # remains usable, but can never enter direct/close tiers.
            decision["level"] = 4
            decision["label"] = "same_domain_contextual_incomplete_component"
            decision["confidence"] = "low"
        elif evidence["detected"]:
            # Component-only evidence from another world (e.g. decorative window)
            # is worse than same-domain context even though one token overlaps.
            decision["level"] = 5
            decision["label"] = "cross_domain_component_only"
            decision["confidence"] = "very_low"
        else:
            decision["level"] = 5
            decision["label"] = "concrete_evidence_missing"
            decision["confidence"] = "very_low"
    return decision


def _safe_reuse_key(candidate):
    return _candidate_unique_key(candidate)


def _safe_reuse_record(candidate):
    key = _safe_reuse_key(candidate)
    if key not in _SAFE_REUSE_HISTORY:
        _SAFE_REUSE_HISTORY[key] = dict(candidate)
        _SAFE_REUSE_COUNTS.setdefault(key, 0)


def safe_reuse_candidate(scene_query):
    eligible = []
    for key, candidate in _SAFE_REUSE_HISTORY.items():
        if _SAFE_REUSE_COUNTS.get(key, 0) >= _SAFE_REUSE_MAX:
            continue
        evidence = concrete_visual_evidence(candidate, scene_query)
        if not evidence["concrete"] or not evidence["complete"]:
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


_concrete_previous_mark_candidate_used = _mark_candidate_used


def _mark_candidate_used(candidate):
    global _LAST_SAFE_REUSE_OFFSET
    if candidate.get("_safe_reuse"):
        key = candidate.get("_safe_reuse_key") or _safe_reuse_key(candidate)
        _SAFE_REUSE_COUNTS[key] = _SAFE_REUSE_COUNTS.get(key, 0) + 1
        # Bounded temporal offset so a reuse does not start from the identical frame.
        _LAST_SAFE_REUSE_OFFSET = min(2.0, 0.75 * _SAFE_REUSE_COUNTS[key])
        print(
            "[SAFE_REUSE] "
            f"reason=concrete_scarcity anchor_compatible=true "
            f"candidate={candidate.get('source_id', candidate.get('id'))} "
            f"reuse_count={_SAFE_REUSE_COUNTS[key]}/{_SAFE_REUSE_MAX} "
            f"segment_offset={_LAST_SAFE_REUSE_OFFSET:.2f}s"
        )
        return
    _LAST_SAFE_REUSE_OFFSET = 0.0
    _safe_reuse_record(candidate)
    _concrete_previous_mark_candidate_used(candidate)


def get_last_safe_reuse_offset():
    global _LAST_SAFE_REUSE_OFFSET
    value = float(_LAST_SAFE_REUSE_OFFSET or 0.0)
    _LAST_SAFE_REUSE_OFFSET = 0.0
    return value


_concrete_previous_choose_best_candidate = choose_best_candidate


def choose_best_candidate(
    candidates,
    relevant_top_n=None,
    *,
    historical=False,
    subject_filter_query=None,
):
    selected = _concrete_previous_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
    if not subject_filter_query or historical:
        return selected

    selected_decision = (
        visual_specificity_decision(selected, subject_filter_query)
        if selected else None
    )
    evidence = (
        concrete_visual_evidence(selected, subject_filter_query)
        if selected else None
    )

    # Only rescue a previous fully-compatible concrete shot when the fresh result
    # has fallen to generic/contextual or worse. Direct/close fresh evidence wins.
    if selected_decision is None or selected_decision["level"] >= 4:
        reused = safe_reuse_candidate(subject_filter_query)
        if reused is not None:
            selected = reused
            selected_decision = visual_specificity_decision(selected, subject_filter_query)
            evidence = concrete_visual_evidence(selected, subject_filter_query)

    if selected:
        print(
            "[VISUAL_EVIDENCE] "
            f"goal={normalize_search_query(subject_filter_query)} "
            f"anchors={'+'.join(extract_query_anchors(subject_filter_query)) or 'none'} "
            f"required={'+'.join((evidence or {}).get('required', [])) or 'none'} "
            f"detected={'+'.join((evidence or {}).get('detected', [])) or 'none'} "
            f"completeness={(evidence or {}).get('completeness', 1.0):.2f} "
            f"tier={(selected_decision or {}).get('label', 'unknown')}"
        )
    return selected
''',
)
path.write_text(text, encoding="utf-8")


# First Hook scene: reuse existing metadata/vision gates but prevent candidates with
# incomplete concrete compound evidence from entering the strict metadata gate.
path = Path("video/hook_visual.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    search_video_candidates,\n)",
    "    search_video_candidates,\n    concrete_visual_evidence,\n)",
    1,
)
text = append_once(
    text,
    "HOOK_CONCRETE_VISUAL_EVIDENCE",
    r'''
# HOOK_CONCRETE_VISUAL_EVIDENCE
_hook_concrete_previous_score_candidate = _score_candidate


def _score_candidate(candidate, scene):
    scores, total = _hook_concrete_previous_score_candidate(candidate, scene)
    query = str(scene.get("keyword", ""))
    evidence = concrete_visual_evidence(candidate, query)
    if evidence["concrete"] and not evidence["complete"]:
        scores["semantic_match"] = min(scores["semantic_match"], 4.0)
        scores["subject_visibility"] = min(scores["subject_visibility"], 4.0)
        total = min(total, 5.0)
    print(
        "[VISUAL_EVIDENCE] "
        f"hook=true goal={normalize_search_query(query)} "
        f"required={'+'.join(evidence['required']) or 'none'} "
        f"detected={'+'.join(evidence['detected']) or 'none'} "
        f"completeness={evidence['completeness']:.2f} "
        f"direct_allowed={str(evidence['complete']).lower()}"
    )
    return scores, total
''',
)
path.write_text(text, encoding="utf-8")


# Apply a small temporal offset only for bounded safe reuse; normal scenes remain 0s.
path = Path("video/video_engine.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    fetch_video,\n    download_video,\n)",
    "    fetch_video,\n    download_video,\n    get_last_safe_reuse_offset,\n)",
    1,
)
text = text.replace(
    "def prepare_vertical_video(\n    input_path,\n    output_path,\n    duration,\n):",
    "def prepare_vertical_video(\n    input_path,\n    output_path,\n    duration,\n    start_offset=0.0,\n):",
    1,
)
text = text.replace(
    "    command = [\n        \"ffmpeg\",\n        \"-y\",\n\n        \"-i\",",
    "    command = [\n        \"ffmpeg\",\n        \"-y\",\n    ]\n\n    if float(start_offset or 0.0) > 0:\n        command.extend([\"-ss\", str(float(start_offset))])\n\n    command.extend([\n        \"-i\",",
    1,
)
text = text.replace(
    "        output_path,\n    ]\n\n    print(\n        \"🎞️ FFmpeg 세로 변환 시작...\"",
    "        output_path,\n    ])\n\n    print(\n        \"🎞️ FFmpeg 세로 변환 시작...\"",
    1,
)
text = text.replace(
    "        prepare_vertical_video(\n            source_video_path,\n            vertical_video_path,\n            duration,\n        )",
    "        prepare_vertical_video(\n            source_video_path,\n            vertical_video_path,\n            duration,\n            start_offset=get_last_safe_reuse_offset(),\n        )",
    1,
)
path.write_text(text, encoding="utf-8")

print("✅ Concrete visual evidence gate + bounded safe reuse applied")
