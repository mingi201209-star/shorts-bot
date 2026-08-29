from pathlib import Path


ENGINE = Path("content/script_engine_v2.py")
ROUTER = Path("content/script_generator_router.py")
FORMAL = Path("content/script_formal_endings.py")
ENGINE_MARKER = "# LIVE_SCRIPT_SEMANTIC_STATE_DELTA_V1"
ROUTER_MARKER = "# LIVE_SCRIPT_LOCKED_HOOK_FORMALIZATION_V1"
FORMAL_MARKER = "# LIVE_SCRIPT_OBSERVED_TTUINDA_FORMAL_ENDING_V1"


engine = ENGINE.read_text(encoding="utf-8")
if ENGINE_MARKER not in engine:
    engine += r'''

# LIVE_SCRIPT_SEMANTIC_STATE_DELTA_V1
# Run 33243842268 proved that lexical novelty is not sufficient evidence for an
# independently narratable downstream state. Reuse the existing grounded claim
# matcher and trusted paraphrase scope; never weaken duplicate validation.
from content.grounded_claim_plan import _claim_matches_text as _grounded_claim_matches_text
from content.grounded_claim_plan import _claim_effect_signatures as _grounded_claim_effect_signatures

_previous_evidence_state_delta_before_semantic_state = _evidence_state_delta

# Determiners, degree/pace words and boundary-local context can modify the same
# physical relation without creating a distinct downstream state. This list is
# relation-agnostic and applies only after the existing grounded matcher says the
# current transition is already semantically covered by the previous claim.
_SEMANTIC_STATE_DELTA_MODIFIERS = {
    "the", "a", "an", "two", "both", "more", "less", "much", "slightly",
    "gradually", "progressively", "steadily", "further", "across", "along",
    "around", "between", "through", "boundary", "boundaries", "interface",
    "interfaces", "how", "way", "ways", "manner", "degree", "relative",
    "same", "similar", "directly", "immediately", "then", "thereafter",
    "점차", "점진적", "점진적으로", "서서히", "경계", "경계면", "사이",
    "따라", "걸쳐", "방식", "정도", "두", "양쪽", "더욱", "보다",
}


def _semantic_state_delta(previous_claim, current_claim):
    lexical = _previous_evidence_state_delta_before_semantic_state(
        previous_claim, current_claim
    )
    if not lexical.get("supported"):
        return dict(lexical, semantic_supported=False, semantic_reason="no lexical delta")

    evidence_phrase = _text(lexical.get("evidence_phrase"))
    if not evidence_phrase:
        return dict(lexical, semantic_supported=False, semantic_reason="missing evidence phrase")

    # Existing grounded semantic relation normalization is authoritative here.
    # If the transition no longer matches the previous claim, it is genuinely
    # distinct enough to preserve without any modifier heuristic.
    previous_covers_transition = _grounded_claim_matches_text(
        evidence_phrase, previous_claim
    )
    previous_effects = _grounded_claim_effect_signatures(previous_claim)
    current_effects = _grounded_claim_effect_signatures(current_claim)
    new_effects = current_effects - previous_effects

    raw_novel_terms = list(lexical.get("novel_terms") or [])
    substantive_terms = [
        term for term in raw_novel_terms
        if _text(term).lower() not in _SEMANTIC_STATE_DELTA_MODIFIERS
    ]

    semantic_supported = (
        (not previous_covers_transition)
        or bool(new_effects)
        or bool(substantive_terms)
    )
    reason = (
        "distinct grounded semantic state"
        if semantic_supported
        else "same grounded semantic nucleus with modifier-only delta"
    )
    return {
        **lexical,
        "supported": semantic_supported,
        "semantic_supported": semantic_supported,
        "semantic_reason": reason,
        "previous_claim_covers_transition": previous_covers_transition,
        "substantive_delta_terms": substantive_terms,
        "new_effect_signatures": sorted(new_effects),
    }


def _evidence_state_delta(previous_claim, current_claim):
    return _semantic_state_delta(previous_claim, current_claim)


def _merge_collapsed_transition_scope(previous_claim, transition_claim):
    """Keep trusted transition detail available inside the surviving Scene."""
    merged = deepcopy(previous_claim)
    scopes = list(merged.get("allowed_paraphrase_scope") or [])
    for value in _claim_scope_values(transition_claim):
        if value and value not in scopes:
            scopes.append(value)
    merged["allowed_paraphrase_scope"] = scopes
    return merged


def _compact_indistinct_transitions(candidate, claims):
    kept = []
    collapsed = []
    for raw in claims or []:
        claim = deepcopy(raw)
        if kept:
            previous = kept[-1]
            previous_role = _grounded_causal_role(previous.get("claim_type"))
            role = _grounded_causal_role(claim.get("claim_type"))
            if previous_role == "mechanism_change" and role == "mechanism_transition":
                delta = _evidence_state_delta(previous, claim)
                if not delta["supported"]:
                    kept[-1] = _merge_collapsed_transition_scope(previous, claim)
                    collapsed.append({
                        "claim_id": _text(claim.get("claim_id")),
                        "claim_type": _text(claim.get("claim_type")),
                        "collapsed_into_claim_id": _text(previous.get("claim_id")),
                        "reason": "no evidence-backed downstream state delta",
                        "semantic_reason": _text(delta.get("semantic_reason")),
                    })
                    continue
        kept.append(claim)
    return kept, collapsed
'''
    ENGINE.write_text(engine, encoding="utf-8")


formal = FORMAL.read_text(encoding="utf-8")
if FORMAL_MARKER not in formal:
    needle = '_DECLARATIVE_ENDING_REPAIRS = (\n'
    if formal.count(needle) != 1:
        raise RuntimeError("shared formal-ending corpus marker mismatch")
    formal = formal.replace(
        needle,
        needle
        + '    # LIVE_SCRIPT_OBSERVED_TTUINDA_FORMAL_ENDING_V1\n'
        + '    (r"띈다(?=[.!…]*$)", "띕니다"),\n',
        1,
    )
    FORMAL.write_text(formal, encoding="utf-8")


router = ROUTER.read_text(encoding="utf-8")
if ROUTER_MARKER not in router:
    router += r'''

# LIVE_SCRIPT_LOCKED_HOOK_FORMALIZATION_V1
# The opening observation is locked before Writer repair, so apply the already
# shared deterministic formal-ending corpus at the router boundary as well.
_previous_normalize_locked_candidate_narration_before_hook_formal = (
    _normalize_locked_candidate_narration
)


def _normalize_locked_candidate_narration(candidate):
    result = _previous_normalize_locked_candidate_narration_before_hook_formal(candidate)
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result

    hook = str(micro.get("hook", "")).strip()
    if not hook or _question_like(hook):
        return result

    from content.script_formal_endings import formalize_declarative_text

    normalized = formalize_declarative_text(hook)
    if normalized == hook:
        return result

    updated_micro = dict(micro)
    updated_micro["hook"] = normalized
    result["micro_narrative"] = updated_micro
    print("🧩 Router locked narration normalized without API: hook")
    return result
'''
    ROUTER.write_text(router, encoding="utf-8")


print("✅ Live Script semantic-state collapse + locked opening formalization applied")
