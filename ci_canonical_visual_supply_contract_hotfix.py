from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "CANONICAL_VISUAL_SUPPLY_CONTRACT_V1"


def patch_grounding_supply():
    path = ROOT / "quality/canonical_subject_grounding_supply.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    record_anchor = '''        "canonical_subject": "jet engine nacelle/nozzle chevrons",\n        "identity_confidence": 0.98,\n        "feature_descriptions": [\n'''
    record_replacement = '''        "canonical_subject": "jet engine nacelle/nozzle chevrons",\n        "identity_confidence": 0.98,\n        # CANONICAL_VISUAL_SUPPLY_CONTRACT_V1\n        # Evidence-owned visible discriminators only. These are not model hints\n        # and do not encode an aircraft model or a topic-specific stock source.\n        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],\n        "feature_descriptions": [\n'''
    if text.count(record_anchor) != 1:
        raise RuntimeError("canonical visual supply chevron record anchor mismatch")
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
        confidence = 0.0
    if confidence < 0.80:
        return {}
    evidence = candidate.get("_trusted_grounding_evidence") or []
    if not isinstance(evidence, list) or not evidence:
        return {}
    discriminators = []
    for raw in candidate.get("_trusted_visual_discriminators") or []:
        term = _canonical_visual_norm_term(raw)
        if term and term not in _CANONICAL_VISUAL_LOW_VALUE_TERMS and term not in discriminators:
            discriminators.append(term)
    if not discriminators:
        return {}
    canonical = str(candidate.get("canonical_subject") or "").strip()
    return {
        "canonical_subject": canonical,
        "visual_discriminators": discriminators,
    }


_original_build_visual_contract_before_canonical_supply = build_visual_contract


def build_visual_contract(scene, candidate=None, *args, **kwargs):
    contract = _original_build_visual_contract_before_canonical_supply(
        scene, candidate=candidate, *args, **kwargs
    )
    if not isinstance(contract, dict):
        return contract
    profile = build_canonical_visual_supply_profile(candidate)
    if profile:
        contract = dict(contract)
        contract["canonical_visual_supply"] = profile
    return contract
'''
    path.write_text(text + "\n", encoding="utf-8")


def main():
    patch_grounding_supply()
    patch_video_downloader()
    print("✅ Canonical Visual Supply Contract V1 applied; subject-proof supply strengthened without gate relaxation")


if __name__ == "__main__":
    main()
