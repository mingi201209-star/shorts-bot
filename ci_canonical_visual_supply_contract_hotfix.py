from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "CANONICAL_VISUAL_SUPPLY_CONTRACT_V1"


def patch_grounding_supply():
    path = ROOT / "quality/canonical_subject_grounding_supply.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    record_anchor = '''        "identity_confidence": 0.98,\n        "feature_descriptions": [\n'''
    record_replacement = '''        "identity_confidence": 0.98,\n        # CANONICAL_VISUAL_SUPPLY_CONTRACT_V1\n        # Evidence-owned visible discriminators only. These are not model hints\n        # and do not encode an aircraft model or a topic-specific stock source.\n        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],\n        "feature_descriptions": [\n'''
    if text.count(record_anchor) != 1:
        raise RuntimeError("canonical visual supply record anchor mismatch")
    text = text.replace(record_anchor, record_replacement, 1)

    claims_anchor = '''    claims = _trusted_grounded_claims(record)\n\n    result["subject_kind"] = _PHYSICAL_KIND\n'''
    claims_replacement = '''    claims = _trusted_grounded_claims(record)\n    visual_discriminators = [\n        _text(value).lower()\n        for value in record.get("visual_discriminators") or []\n        if _text(value)\n    ]\n\n    result["subject_kind"] = _PHYSICAL_KIND\n'''
    if text.count(claims_anchor) != 1:
        raise RuntimeError("canonical visual supply claims anchor mismatch")
    text = text.replace(claims_anchor, claims_replacement, 1)

    result_anchor = '''    if claims:\n        result["_trusted_grounded_claims"] = deepcopy(claims)\n    return result\n'''
    result_replacement = '''    if claims:\n        result["_trusted_grounded_claims"] = deepcopy(claims)\n    if visual_discriminators:\n        result["_trusted_visual_discriminators"] = list(dict.fromkeys(visual_discriminators))\n    return result\n'''
    if text.count(result_anchor) != 1:
        raise RuntimeError("canonical visual supply result anchor mismatch")
    text = text.replace(result_anchor, result_replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_video_downloader():
    path = ROOT / "video/video_downloader.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "VISUAL_SUBJECT_ANCHOR_CONTRACT_V1" not in text:
        raise RuntimeError("canonical visual supply requires Visual Subject Anchor Contract V1")
    if "VISUAL_SUBJECT_ANCHOR_COMPOUND_PHYSICAL_V2" not in text:
        raise RuntimeError("canonical visual supply requires Visual Subject Anchor Contract V2")
    if "VISUAL_CLAIM_SEMANTIC_FALLBACK_V1" not in text:
        raise RuntimeError("canonical visual supply requires #254 explanatory fallback")

    text = text.rstrip() + r'''


# CANONICAL_VISUAL_SUPPLY_CONTRACT_V1
# Run 33251901169: Canonical Subject Grounding already knew the subject was
# `jet engine nacelle/nozzle chevrons`, but the opening retrieval boundary kept
# only coarse aircraft+engine+chevron anchors. Preserve trusted visible
# discriminators for supply without weakening the existing 3/3 subject gate.
_CANONICAL_VISUAL_LOW_VALUE_TERMS = {
    "detail", "stage", "view", "shot", "scene", "show", "showing",
    "mechanism", "context", "motion", "generic",
}


def _canonical_visual_norm_term(value):
    word = str(value or "").strip().lower().replace("-", " ")
    parts = normalize_search_query(word).split()
    if len(parts) != 1:
        return ""
    word = parts[0]
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def build_canonical_visual_supply_profile(candidate):
    if not isinstance(candidate, dict):
        return {}
    if str(candidate.get("subject_kind") or "").strip().lower() != "physical_entity":
        return {}
    try:
        confidence = float(candidate.get("subject_identity_confidence") or 0.0)
    except (TypeError, ValueError):
        return {}
    if confidence < 0.80:
        return {}

    canonical = str(candidate.get("canonical_subject") or "").strip()
    trusted = candidate.get("_trusted_grounding_evidence") or []
    if not canonical or not any(
        isinstance(item, dict)
        and str(item.get("supports_subject") or "").strip() == canonical
        and str(item.get("source") or "").strip()
        for item in trusted
    ):
        return {}

    raw_discriminators = candidate.get("_trusted_visual_discriminators") or []
    discriminators = []
    for raw in raw_discriminators:
        for token in normalize_search_query(raw).split():
            token = _canonical_visual_norm_term(token)
            if token and token not in _CANONICAL_VISUAL_LOW_VALUE_TERMS and token not in discriminators:
                discriminators.append(token)
    if not discriminators:
        return {}

    canonical_terms = []
    for raw in normalize_search_query(canonical).split():
        token = _canonical_visual_norm_term(raw)
        if token and token not in _CANONICAL_VISUAL_LOW_VALUE_TERMS and token not in canonical_terms:
            canonical_terms.append(token)

    return {
        "canonical_subject": canonical,
        "identity_confidence": confidence,
        "canonical_terms": canonical_terms,
        "visual_discriminators": discriminators,
        "grounding_source": str(trusted[0].get("source") or "") if trusted else "",
    }


_canonical_visual_supply_previous_enforce = enforce_visual_subject_anchor_query


def enforce_visual_subject_anchor_query(
    *, narration, visual_goal, query, visual_type="real_world_broll",
    scene_role="", canonical_visual_supply=None,
):
    base = _canonical_visual_supply_previous_enforce(
        narration=narration,
        visual_goal=visual_goal,
        query=query,
        visual_type=visual_type,
    )
    contract = get_current_visual_subject_anchor_contract()
    profile = canonical_visual_supply if isinstance(canonical_visual_supply, dict) else {}
    role = str(scene_role or "").strip().lower()

    # Opening subject-observation scenes must prove the physical subject first.
    # Mechanism context and generic motion stay secondary. This does not apply to
    # explanatory factual scenes, whose #254 relation contract remains authoritative.
    if role not in {"phenomenon", "hook", "observation", "opening"}:
        return base
    required = list(contract.get("required_anchors") or [])
    canonical_terms = list(profile.get("canonical_terms") or [])
    discriminators = list(profile.get("visual_discriminators") or [])
    if not required or not canonical_terms or not discriminators:
        return base

    proof_words = []
    # Keep the physical domain first, then the trusted canonical identity, then
    # trusted visible discriminators. Required anchors are rechecked below.
    if "aircraft" in required:
        proof_words.append("aircraft")
    for word in canonical_terms + discriminators:
        if word not in proof_words:
            proof_words.append(word)
    for anchor in required:
        preferred = _VISUAL_ANCHOR_PREFERRED_TERM.get(anchor, anchor)
        if preferred not in proof_words:
            proof_words.append(preferred)
    proof_query = " ".join(proof_words[:7]).strip()

    proof_anchors = extract_query_anchors(proof_query)
    if any(anchor not in proof_anchors for anchor in required):
        # Never trade a required 3/3 subject identity for richer wording.
        return base

    contract.update({
        "effective_query": proof_query,
        "canonical_subject": str(profile.get("canonical_subject") or ""),
        "canonical_visual_discriminators": list(discriminators),
        "subject_proof_priority": True,
        "precanonical_query": base,
    })
    globals()["_CURRENT_VISUAL_SUBJECT_ANCHOR_CONTRACT"] = contract
    print(
        "[CANONICAL_VISUAL_SUPPLY] "
        f"role={role} canonical={profile.get('canonical_subject')} "
        f"required={'+'.join(required)} discriminators={'+'.join(discriminators)} "
        f"query={proof_query}"
    )
    return proof_query


_canonical_visual_supply_previous_general_fallback = _general_fallback_queries


def _general_fallback_queries(query):
    contract = get_current_visual_subject_anchor_contract()
    normalized = normalize_search_query(query)
    if not bool(contract.get("subject_proof_priority")) or normalized != normalize_search_query(contract.get("effective_query")):
        return _canonical_visual_supply_previous_general_fallback(query)

    required = list(contract.get("required_anchors") or [])
    words = normalized.split()
    variants = []

    def add(parts):
        value = " ".join(_dedupe_words(parts)[:7]).strip()
        if not value or value == normalized or value in variants:
            return
        anchors = extract_query_anchors(value)
        if any(anchor not in anchors for anchor in required):
            return
        variants.append(value)

    # Keep the same number of bounded fallback opportunities. Change wording,
    # never the trusted proof identity. No `aircraft engine detail` degradation.
    swapped = ["airplane" if word == "aircraft" else word for word in words]
    add(swapped)
    optional = [
        word for word in words
        if word not in {"aircraft", "jet", "engine", "chevron", "serrated"}
    ]
    for removable in optional:
        compact = [word for word in words if word != removable]
        add(compact + ["closeup"])
    add(words + ["closeup"])

    variants = variants[:3]
    print(
        "[CANONICAL_VISUAL_SUPPLY_LADDER] "
        f"goal={normalized} required={'+'.join(required)} "
        f"ladder={' | '.join(variants) if variants else 'none'}"
    )
    return variants
''' + "\n"
    path.write_text(text, encoding="utf-8")


def patch_video_engine():
    path = ROOT / "video/video_engine.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    needle = '''        query=keyword,\n        visual_type=visual_type,\n    )\n'''
    replacement = '''        query=keyword,\n        visual_type=visual_type,\n        # CANONICAL_VISUAL_SUPPLY_CONTRACT_V1\n        scene_role=str(item.get("role") or item.get("scene_role") or ""),\n        canonical_visual_supply=item.get("_canonical_visual_supply"),\n    )\n'''
    if text.count(needle) != 1:
        raise RuntimeError("canonical visual supply create_scene call anchor mismatch")
    text = text.replace(needle, replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_main():
    path = ROOT / "main.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    anchor = '''# ============================================================\n# Scene Production\n# ============================================================\n'''
    if text.count(anchor) != 1:
        raise RuntimeError("canonical visual supply main scene-production anchor mismatch")
    block = r'''
# CANONICAL_VISUAL_SUPPLY_CONTRACT_V1
# Attach a small, private supply profile only AFTER Script generation. Writer,
# Grounded Claim Plan, FACT, and Script V2 inputs remain untouched.
_original_generate_script_before_canonical_visual_supply = generate_script


def generate_script(topic_info, candidate):
    result = _original_generate_script_before_canonical_visual_supply(topic_info, candidate)
    if not isinstance(result, dict) or not isinstance(candidate, dict):
        return result
    try:
        from video.video_downloader import build_canonical_visual_supply_profile
        profile = build_canonical_visual_supply_profile(candidate)
    except Exception:
        profile = {}
    if not profile:
        return result
    scenes = result.get("scenes")
    if isinstance(scenes, list):
        for scene in scenes:
            if isinstance(scene, dict):
                scene["_canonical_visual_supply"] = dict(profile)
    return result


'''
    text = text.replace(anchor, block + anchor, 1)
    path.write_text(text, encoding="utf-8")


def patch_still_fallback():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    signature_anchor = '''    return tuple(signature) if len(signature) >= 2 else ()\n\n\ndef _reuse_signatures(scene):\n'''
    signature_replacement = '''    if len(signature) >= 2:\n        return tuple(signature)\n    # CANONICAL_VISUAL_SUPPLY_CONTRACT_V1\n    # Engine/chevron proof scenes were previously uncacheable because this older\n    # signature helper knew only wing/window/gear families. Reuse only an already\n    # verified still with the same complete subject-anchor tuple.\n    try:\n        from video.video_downloader import extract_query_anchors\n        anchors = tuple(extract_query_anchors(query))\n    except Exception:\n        anchors = ()\n    return anchors if len(anchors) >= 2 else ()\n\n\ndef _reuse_signatures(scene):\n'''
    if text.count(signature_anchor) != 1:
        raise RuntimeError("canonical visual supply still signature anchor mismatch")
    text = text.replace(signature_anchor, signature_replacement, 1)

    reject_anchor = '''            print(\n                f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=rejected_by_vision "\n                f"count={_GENERATION_COUNT}"\n            )\n'''
    reject_replacement = '''            # CANONICAL_VISUAL_SUPPLY_CONTRACT_V1\n            # Preserve the verifier decision for auditability; no extra Vision call.\n            reason = str(evidence.get("reason") or "unspecified")[:300]\n            visible = "+".join(str(value) for value in evidence.get("visible_components", []) or []) or "none"\n            print(\n                f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=rejected_by_vision "\n                f"count={_GENERATION_COUNT} pass={bool(evidence.get('pass', False))} "\n                f"visible={visible} reason={reason}"\n            )\n'''
    if text.count(reject_anchor) != 1:
        raise RuntimeError("canonical visual supply still rejection anchor mismatch")
    text = text.replace(reject_anchor, reject_replacement, 1)
    path.write_text(text, encoding="utf-8")


def main():
    patch_grounding_supply()
    patch_video_downloader()
    patch_video_engine()
    patch_main()
    patch_still_fallback()
    print("✅ Canonical Visual Supply Contract V1 applied; subject-proof supply strengthened without gate relaxation")


if __name__ == "__main__":
    main()
