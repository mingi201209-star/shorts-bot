from pathlib import Path


ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 1) Retrieval/selection contract: preserve concrete subject identity from the
#    existing Scene text/visual_goal when Writer-produced keyword became generic.
#    No new API calls, retries, providers, thresholds, or templates.
# ---------------------------------------------------------------------------
downloader = ROOT / "video/video_downloader.py"
text = downloader.read_text(encoding="utf-8")
marker = "VISUAL_SUBJECT_ANCHOR_CONTRACT_V1"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_SUBJECT_ANCHOR_CONTRACT_V1
# General subject/domain preservation at the visual retrieval boundary. This
# deliberately consumes the Scene fields that already exist; it does not alter
# Writer/Retention output and does not introduce a topic-specific recovery path.
_QUERY_ANCHOR_GROUPS.update({
    "engine": {"engine", "engines", "turbofan", "turbofans", "nacelle", "nacelles"},
    "spinner": {"spinner", "spinners", "spiral", "spirals"},
})
_CONCRETE_COMPONENT_ANCHORS.update({"engine", "spinner"})

_VISUAL_SOURCE_ANCHOR_ALIASES = {
    "aircraft": ("비행기", "항공기", "여객기", "aircraft", "airplane", "airliner"),
    "window": ("창문", "aircraft window", "airplane window"),
    "wing": ("날개", "윙렛", "날개끝", "날개 끝", "wing", "winglet", "wingtip"),
    "cabin": ("기내", "객실", "cabin"),
    "engine": ("엔진", "터보팬", "turbofan", "jet engine", "engine", "nacelle"),
    # Do not map a bare vortex/swirl to spinner: wingtip vortices and other
    # phenomena are valid concrete subjects of their own.
    "spinner": ("스피너", "소용돌이 무늬", "소용돌이무늬", "나선 무늬", "spinner", "spinner spiral"),
    "bridge": ("다리", "교량", "bridge"),
    "tunnel": ("터널", "tunnel"),
    "road": ("도로", "road", "highway"),
    "building": ("건물", "빌딩", "building", "skyscraper"),
}
_VISUAL_ANCHOR_PREFERRED_TERM = {
    "aircraft": "aircraft",
    "window": "window",
    "wing": "wing",
    "cabin": "cabin",
    "engine": "engine",
    "spinner": "spinner",
    "bridge": "bridge",
    "tunnel": "tunnel",
    "road": "road",
    "building": "building",
}
_VISUAL_ANCHOR_ORDER = (
    "aircraft", "engine", "spinner", "window", "wing", "cabin",
    "bridge", "tunnel", "road", "building",
)
_CURRENT_VISUAL_SUBJECT_ANCHOR_CONTRACT = {
    "required": False,
    "required_anchors": [],
    "original_query": "",
    "effective_query": "",
    "reason": "no_concrete_subject",
}


def extract_query_anchors(query):
    """Return existing semantic anchors without silently truncating a compound subject.

    Existing window/wing behavior is preserved. Compound subjects may carry up
    to three identity anchors so domain + subject + component can survive.
    """
    words = set(normalize_search_query(query).split())
    found = []
    for canonical in _VISUAL_ANCHOR_ORDER:
        aliases = _QUERY_ANCHOR_GROUPS.get(canonical, {canonical})
        if words & aliases:
            found.append(canonical)

    # Preserve the historical contract that a wing query is aircraft-domain,
    # even when a caller supplied only the component word.
    if "wing" in found and "aircraft" not in found:
        found.insert(0, "aircraft")

    # Keep old exact regression behavior for the established two-anchor cases.
    if "aircraft" in found and "window" in found and not ({"engine", "spinner"} & set(found)):
        return ["aircraft", "window"]
    if "aircraft" in found and "wing" in found and not ({"engine", "spinner"} & set(found)):
        return ["aircraft", "wing"]

    return _dedupe_words(found)[:3]


def _source_visual_anchors(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return []
    normalized = normalize_search_query(raw)
    anchors = list(extract_query_anchors(normalized))
    for canonical in _VISUAL_ANCHOR_ORDER:
        if canonical in anchors:
            continue
        aliases = _VISUAL_SOURCE_ANCHOR_ALIASES.get(canonical, ())
        if any(alias.lower() in raw for alias in aliases):
            anchors.append(canonical)
    return _dedupe_words(anchors)[:3]


def _required_scene_subject_anchors(narration, visual_goal):
    narration_anchors = _source_visual_anchors(narration)
    goal_anchors = _source_visual_anchors(visual_goal)
    combined = _dedupe_words(narration_anchors + goal_anchors)

    # Prefer a coherent identity tuple: domain first, then concrete component(s).
    ordered = [anchor for anchor in _VISUAL_ANCHOR_ORDER if anchor in combined]
    return ordered[:3]


def enforce_visual_subject_anchor_query(*, narration, visual_goal, query, visual_type="real_world_broll"):
    """Preserve source subject identity in the visual search query.

    Generic/transition scenes with no recognized concrete source subject remain
    unchanged. Already-specific queries are also left unchanged.
    """
    global _CURRENT_VISUAL_SUBJECT_ANCHOR_CONTRACT

    original = normalize_search_query(query)
    required = _required_scene_subject_anchors(narration, visual_goal)
    query_anchors = extract_query_anchors(original)
    missing = [anchor for anchor in required if anchor not in query_anchors]

    if not required:
        effective = original
        reason = "no_concrete_subject"
    elif not missing:
        effective = original
        reason = "anchors_already_preserved"
    else:
        prefix = [_VISUAL_ANCHOR_PREFERRED_TERM.get(anchor, anchor) for anchor in required]
        original_words = original.split()
        effective = " ".join(_dedupe_words(prefix + original_words)[:7]).strip()
        reason = "restored_source_subject_anchor"

    _CURRENT_VISUAL_SUBJECT_ANCHOR_CONTRACT = {
        "required": bool(required),
        "required_anchors": list(required),
        "original_query": original,
        "effective_query": effective,
        "visual_type": str(visual_type or ""),
        "reason": reason,
    }

    if effective != original:
        print(
            "[VISUAL_SUBJECT_ANCHOR] "
            f"required={'+'.join(required)} original={original or 'none'} "
            f"effective={effective} reason={reason}"
        )
    return effective


def get_current_visual_subject_anchor_contract():
    return dict(_CURRENT_VISUAL_SUBJECT_ANCHOR_CONTRACT)


_visual_subject_anchor_previous_final_selection = get_last_final_visual_selection


def get_last_final_visual_selection():
    selection = _visual_subject_anchor_previous_final_selection()
    contract = get_current_visual_subject_anchor_contract()
    selection["subject_anchor_contract_required"] = bool(contract.get("required"))
    selection["required_subject_anchors"] = list(contract.get("required_anchors") or [])
    selection["subject_anchor_original_query"] = str(contract.get("original_query") or "")
    selection["subject_anchor_effective_query"] = str(contract.get("effective_query") or "")
    selection["subject_anchor_contract_reason"] = str(contract.get("reason") or "")
    return selection
''' + "\n"
    downloader.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 2) Wire the contract into create_scene without changing its interface or any
#    Writer/Retention code. Hook receives a local Scene copy with the strengthened
#    keyword, so First5 uses the same preserved identity.
# ---------------------------------------------------------------------------
engine = ROOT / "video/video_engine.py"
text = engine.read_text(encoding="utf-8")
engine_marker = "VISUAL_SUBJECT_ANCHOR_CREATE_SCENE_V1"
if engine_marker not in text:
    start = text.find("def create_scene(")
    if start < 0:
        raise RuntimeError("Visual Subject Anchor Contract: create_scene not found")
    insert_at = text.find("    if not text:", start)
    if insert_at < 0:
        raise RuntimeError("Visual Subject Anchor Contract: create_scene validation anchor not found")
    block = '''    # VISUAL_SUBJECT_ANCHOR_CREATE_SCENE_V1\n    # Strengthen only the local retrieval query. Writer-produced Scene fields are\n    # not persisted or rewritten.\n    from video.video_downloader import enforce_visual_subject_anchor_query\n    original_visual_keyword = keyword\n    keyword = enforce_visual_subject_anchor_query(\n        narration=text,\n        visual_goal=visual_goal,\n        query=keyword,\n        visual_type=visual_type,\n    )\n    if keyword != original_visual_keyword:\n        item = dict(item)\n        item["keyword"] = keyword\n\n'''
    text = text[:insert_at] + block + text[insert_at:]
    engine.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 3) Persist the contract into Final Visual Semantic QA and fail closed on the
#    exact vacuous condition: a required subject exists but extracted total=0.
# ---------------------------------------------------------------------------
qa = ROOT / "quality/final_visual_semantic_qa.py"
text = qa.read_text(encoding="utf-8")
qa_marker = "VISUAL_SUBJECT_ANCHOR_FINAL_QA_V1"
if qa_marker not in text:
    metadata_line = '            "metadata": str(selection.get("metadata") or "")[:500],\n'
    if metadata_line not in text:
        raise RuntimeError("Visual Subject Anchor Contract: final QA lineage anchor not found")
    lineage = metadata_line + '''            "subject_anchor_contract_required": bool(selection.get("subject_anchor_contract_required", False)),\n            "required_subject_anchors": list(selection.get("required_subject_anchors") or []),\n            "subject_anchor_original_query": str(selection.get("subject_anchor_original_query") or ""),\n            "subject_anchor_effective_query": str(selection.get("subject_anchor_effective_query") or ""),\n            "subject_anchor_contract_reason": str(selection.get("subject_anchor_contract_reason") or ""),\n'''
    text = text.replace(metadata_line, lineage, 1)

    failure_clause = '        if not item.get("accepted") or _missing_required_aviation_component_anchor(item)\n'
    if failure_clause not in text:
        raise RuntimeError("Visual Subject Anchor Contract: final QA failure clause not found")
    text = text.replace(
        failure_clause,
        '        if (not item.get("accepted")\n            or _missing_required_subject_anchor(item)\n            or _missing_required_aviation_component_anchor(item))\n',
        1,
    )

    text = text.rstrip() + r'''


# VISUAL_SUBJECT_ANCHOR_FINAL_QA_V1
def _missing_required_subject_anchor(item):
    """Reject vacuous semantic evidence for a Scene known to require a subject."""
    if not bool(item.get("subject_anchor_contract_required", False)):
        return False
    required = list(item.get("required_subject_anchors") or [])
    total = int(item.get("anchor_total", 0) or 0)
    if required and total <= 0:
        item["failure_reason"] = "missing_required_subject_anchor"
        return True
    return False
''' + "\n"
    qa.write_text(text, encoding="utf-8")

print("✅ Visual Subject Anchor Contract V1 applied: source anchors preserved; vacuous required 0/0 fails closed")
