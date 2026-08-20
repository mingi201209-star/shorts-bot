import re

REVERSAL_MARKERS = (
    "처럼 보", "같아 보", "실제로", "사실은", "알고 보면", "위장", "가짜", "숨은",
    "looks like", "appears to", "actually", "disguised", "hidden", "facade", "fake",
)

APPEARANCE_QUERY_TERMS = {
    "ordinary", "normal", "disguised", "disguise", "facade", "fake", "hidden",
    "camouflage", "residential", "storefront", "house", "apartment", "office",
    "exterior", "lookalike", "resembles", "shaped",
}

GENERIC_QUERY_TERMS = {
    "close", "up", "closeup", "video", "shot", "view", "showing", "real", "actual",
    "the", "a", "an", "of", "and", "with",
}

GENERIC_SLUG_TERMS = GENERIC_QUERY_TERMS | {
    "pexels", "footage", "vertical", "portrait",
}


def _tokens(value):
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 3
    }


def is_reversal_scene(scene):
    combined = " ".join(
        str(scene.get(key, "") or "")
        for key in ("text", "visual_goal")
    ).lower()
    return any(marker in combined for marker in REVERSAL_MARKERS)


def validate_reversal_query(scene):
    if not is_reversal_scene(scene):
        return True, "non_reversal"

    query_tokens = _tokens(scene.get("keyword"))
    appearance_hits = query_tokens & APPEARANCE_QUERY_TERMS
    reveal_tokens = query_tokens - APPEARANCE_QUERY_TERMS - GENERIC_QUERY_TERMS

    if not appearance_hits:
        return False, "reversal_appearance_side_missing"
    if not reveal_tokens:
        return False, "reversal_reveal_side_missing"
    return True, "reversal_concept_preserved"


def visual_signature(keyword, slug):
    return {
        "keyword_tokens": _tokens(keyword) - GENERIC_QUERY_TERMS,
        "slug_tokens": _tokens(slug) - GENERIC_SLUG_TERMS,
    }


def _jaccard(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def progression_passes(first_signature, second_signature):
    if not first_signature:
        return True, "no_first_visual_state"

    first_kw = set(first_signature.get("keyword_tokens") or ())
    first_slug = set(first_signature.get("slug_tokens") or ())
    second_kw = set(second_signature.get("keyword_tokens") or ())
    second_slug = set(second_signature.get("slug_tokens") or ())

    keyword_similarity = _jaccard(first_kw, second_kw)
    slug_similarity = _jaccard(first_slug, second_slug)
    new_information = (second_kw | second_slug) - (first_kw | first_slug)

    if slug_similarity >= 0.75:
        return False, "opening_slug_too_similar"
    if keyword_similarity >= 0.60 and slug_similarity >= 0.45:
        return False, "opening_visual_concept_too_similar"
    if keyword_similarity >= 0.60 and len(new_information) < 2:
        return False, "opening_no_visual_progression"

    return True, "opening_progression_ok"
