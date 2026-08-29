from pathlib import Path


VALIDATION = Path("content/script_engine_v2_validation.py")
RUNNER = Path("content/script_engine_v2_runner.py")
VALIDATION_MARKER = "# GROUNDED_KEYWORD_CANONICAL_CONTEXT_V1"
RUNNER_MARKER = "# GROUNDED_KEYWORD_NORMALIZER_V1"


validation = VALIDATION.read_text(encoding="utf-8")
if VALIDATION_MARKER not in validation:
    validation += r'''

# GROUNDED_KEYWORD_CANONICAL_CONTEXT_V1
# A factual grounded retrieval keyword must keep both its owned-claim grounding
# and enough canonical subject identity to avoid cross-domain visual drift.
_previous_validate_scene_basics_before_grounded_keyword_context = validate_scene_basics


def validate_scene_basics(script, plan):
    ok, failures = _previous_validate_scene_basics_before_grounded_keyword_context(script, plan)
    scenes = script.get("scenes") if isinstance(script, dict) else None
    contracts = plan.get("contracts") if isinstance(plan, dict) else None
    canonical_terms = _keyword_terms(plan.get("canonical_subject")) if isinstance(plan, dict) else []

    if isinstance(scenes, list) and isinstance(contracts, list) and len(scenes) == len(contracts):
        for index, (scene, contract) in enumerate(zip(scenes, contracts), start=1):
            if not isinstance(scene, dict) or not isinstance(contract, dict):
                continue
            if not str(contract.get("owned_claim_id") or "").strip():
                continue
            if not bool(contract.get("grounding_provenance_present")):
                continue
            terms = _keyword_terms(scene.get("keyword"))
            if canonical_terms and terms and not _keyword_has_grounded_overlap(terms, canonical_terms):
                failures.append({
                    "scene_index": index,
                    "reason": "keyword missing canonical subject context",
                })

    deduped = []
    seen = set()
    for item in failures:
        key = (item.get("scene_index"), item.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return not deduped, deduped
'''
    VALIDATION.write_text(validation, encoding="utf-8")


runner = RUNNER.read_text(encoding="utf-8")
if RUNNER_MARKER not in runner:
    runner += r'''

# GROUNDED_KEYWORD_NORMALIZER_V1
# Run 33246584198 proved the generic deterministic fallback could overwrite all
# five Writer keywords with one semantic signature. For factual grounded Scenes,
# derive retrieval metadata from canonical subject context + the owned claim.
_previous_deterministic_keyword_before_grounded_keyword_contract = _deterministic_keyword

_GROUNDED_KEYWORD_STOP_TERMS = {
    "the", "and", "that", "this", "with", "from", "into", "over", "under",
    "more", "less", "than", "then", "when", "where", "which", "while",
    "through", "across", "around", "between", "after", "before", "only",
    "change", "changes", "changed", "make", "makes", "made", "becomes",
    "scene", "claim", "result", "effect", "state", "step", "detail",
}


def _grounded_keyword_norm_term(term):
    value = str(term or "").lower().strip("-_ ")
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        return value[:-1]
    return value


def _grounded_keyword_terms(value):
    result = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9-]*", str(value or "")):
        term = _grounded_keyword_norm_term(raw)
        if len(term) < 3 or term in _GROUNDED_KEYWORD_STOP_TERMS:
            continue
        if term not in result:
            result.append(term)
    return result


def _owned_claim_keyword_terms(contract):
    values = [
        str(contract.get("owned_claim_id") or "").replace("_", " "),
        str(contract.get("supporting_evidence_summary") or ""),
    ]
    values.extend(str(item) for item in contract.get("allowed_paraphrase_scope") or [] if item)
    values.extend(str(item) for item in contract.get("required_concepts") or [] if item)
    result = []
    for value in values:
        for term in _grounded_keyword_terms(value):
            if term not in result:
                result.append(term)
    return result


def _canonical_keyword_context(plan):
    return _grounded_keyword_terms(plan.get("canonical_subject") if isinstance(plan, dict) else "")


def _grounded_claim_aware_keyword(contract, plan):
    if not isinstance(contract, dict) or not isinstance(plan, dict):
        return ""
    claim_id = str(contract.get("owned_claim_id") or "").strip()
    if not claim_id or not bool(contract.get("grounding_provenance_present")):
        return ""
    canonical = _canonical_keyword_context(plan)
    claim_terms = _owned_claim_keyword_terms(contract)
    if not canonical or not claim_terms:
        return ""

    words = []
    # Stable subject head keeps physical identity without forcing every canonical
    # token into every Scene.
    for term in canonical[:2]:
        if term not in words:
            words.append(term)

    # Keep claim-specific canonical discriminators when the owned evidence names
    # them (for example a part/feature), then add the owned claim nucleus.
    for term in canonical[2:]:
        if term in claim_terms and term not in words:
            words.append(term)
    for term in claim_terms:
        if term not in words:
            words.append(term)
        if len(words) >= 7:
            break

    # A grounded keyword must contain at least one claim-specific term beyond the
    # canonical context. Otherwise let the legacy path fail closed downstream.
    canonical_set = set(canonical)
    if not any(term not in canonical_set for term in words):
        return ""
    return " ".join(words[:7])


def _deterministic_keyword(scene: Dict[str, Any], contract: Dict[str, Any], plan: Dict[str, Any], index: int) -> str:
    grounded = _grounded_claim_aware_keyword(contract, plan)
    if grounded:
        print(
            "[GROUNDED_KEYWORD_TRACE] "
            f"scene={index} claim={str(contract.get('owned_claim_id') or '')} "
            f"input={str(scene.get('keyword') or '').strip()} output={grounded}"
        )
        return grounded
    return _previous_deterministic_keyword_before_grounded_keyword_contract(
        scene, contract, plan, index
    )
'''
    RUNNER.write_text(runner, encoding="utf-8")


print("✅ Grounded Keyword Contract V1 applied; no Writer/API/retry changes")
