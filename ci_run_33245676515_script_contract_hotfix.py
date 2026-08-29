from pathlib import Path


VALIDATION = Path("content/script_engine_v2_validation.py")
ENGINE = Path("content/script_engine_v2.py")
VALIDATION_MARKER = "# COMPACT_GROUNDED_KEYWORD_VARIETY_V1"
ENGINE_MARKER = "# MECHANISM_INPUT_CAUSAL_CLUE_CONTRACT_V1"


validation = VALIDATION.read_text(encoding="utf-8")
if VALIDATION_MARKER not in validation:
    validation += r'''

# COMPACT_GROUNDED_KEYWORD_VARIETY_V1
# Run 33245676515 proved that max(6, scene_count//2) makes every 5-Scene
# compact plan impossible to validate even when all five keywords are unique.
# Keep a scene-count-aware diversity floor and additionally require factual
# grounded scenes to keep retrieval keywords tied to their owned evidence.
_previous_validate_scene_basics_before_compact_keyword_contract = validate_scene_basics

_KEYWORD_DECORATION_TERMS = {
    "stage", "scene", "detail", "details", "view", "visual", "shot",
    "closeup", "close-up", "generic", "background", "concept",
}
_KEYWORD_EVIDENCE_STOP_TERMS = {
    "the", "and", "that", "this", "with", "from", "into", "over", "under",
    "more", "less", "than", "then", "when", "where", "which", "while",
    "through", "across", "around", "between", "after", "before", "only",
    "scene", "claim", "result", "effect", "state", "step",
}


def _keyword_norm_term(term):
    value = str(term or "").lower().strip("-_ ")
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        return value[:-1]
    return value


def _keyword_terms(value):
    terms = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9-]*", str(value or "")):
        term = _keyword_norm_term(raw)
        if not term or term in _KEYWORD_DECORATION_TERMS:
            continue
        if term not in terms:
            terms.append(term)
    return terms


def _grounded_keyword_evidence_terms(contract):
    values = []
    if isinstance(contract, dict):
        values.append(str(contract.get("owned_claim_id") or "").replace("_", " "))
        values.append(str(contract.get("supporting_evidence_summary") or ""))
        values.extend(str(v) for v in contract.get("allowed_paraphrase_scope") or [] if v)
        values.extend(str(v) for v in contract.get("required_concepts") or [] if v)
    result = []
    for value in values:
        for term in _keyword_terms(value):
            if len(term) < 3 or term in _KEYWORD_EVIDENCE_STOP_TERMS:
                continue
            if term not in result:
                result.append(term)
    return result


def _keyword_has_grounded_overlap(keyword_terms, evidence_terms):
    for left in keyword_terms:
        for right in evidence_terms:
            if left == right:
                return True
            if min(len(left), len(right)) >= 4 and (left in right or right in left):
                return True
    return False


def _compact_keyword_required(scene_count):
    # Diversity scales with actual information slots; it is never allowed to
    # exceed the number of Scenes. Five compact Scenes therefore require three
    # semantically distinct retrieval phrases, while repeated metadata still fails.
    if scene_count <= 2:
        return scene_count
    return min(scene_count, max(2, (scene_count + 1) // 2))


def validate_scene_basics(script, plan):
    ok, failures = _previous_validate_scene_basics_before_compact_keyword_contract(script, plan)
    failures = [
        item for item in failures
        if not str(item.get("reason", "")).startswith("keyword variety too low:")
    ]

    scenes = script.get("scenes") if isinstance(script, dict) else None
    contracts = plan.get("contracts") if isinstance(plan, dict) else None
    if not isinstance(scenes, list) or not isinstance(contracts, list) or len(scenes) != len(contracts):
        return not failures, failures

    signatures = []
    for index, (scene, contract) in enumerate(zip(scenes, contracts), start=1):
        if not isinstance(scene, dict) or not isinstance(contract, dict):
            continue
        terms = _keyword_terms(scene.get("keyword"))
        signatures.append(tuple(terms))

        owned_claim = str(contract.get("owned_claim_id") or "").strip()
        if not owned_claim:
            continue
        evidence_terms = _grounded_keyword_evidence_terms(contract)
        # Only enforce evidence overlap where the trusted contract exposes
        # usable English evidence terms. This keeps legacy/non-grounded paths intact.
        if evidence_terms and terms and not _keyword_has_grounded_overlap(terms, evidence_terms):
            failures.append({
                "scene_index": index,
                "reason": "keyword not grounded in owned claim evidence",
            })

    if signatures:
        unique_count = len(set(signatures))
        required = _compact_keyword_required(len(signatures))
        if unique_count < required:
            failures.append({
                "scene_index": None,
                "reason": (
                    f"keyword variety too low: {unique_count}/{len(signatures)} "
                    f"(scene-aware required={required})"
                ),
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


engine = ENGINE.read_text(encoding="utf-8")
if ENGINE_MARKER not in engine:
    engine += r'''

# MECHANISM_INPUT_CAUSAL_CLUE_CONTRACT_V1
# Run 33245676515 showed that a grounded mechanism_input can still be written as
# passive background. Make Scene 3 answer why its evidence-backed condition is
# causally relevant to the next owned mechanism change, without inventing facts.
_previous_writer_payload_before_mechanism_input_clue = writer_payload
_previous_local_repair_payload_before_mechanism_input_clue = local_repair_payload

_MECHANISM_INPUT_ANSWER_TARGET = (
    "State the evidence-backed pre-existing condition/interface/difference and explain why that condition is causally relevant to the next grounded mechanism change. "
    "Do not reveal the final result and do not invent a new physical effect."
)


def _next_grounded_contract(contracts, scene_index):
    for item in contracts or []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index") or 0)
        except Exception:
            continue
        if index <= int(scene_index):
            continue
        if str(item.get("owned_claim_id") or "").strip():
            return item
    return {}


def _decorate_mechanism_input_contracts(contracts):
    decorated = deepcopy(contracts or [])
    for item in decorated:
        if not isinstance(item, dict):
            continue
        if str(item.get("causal_role") or "") != "mechanism_input":
            continue
        scene_index = int(item.get("index") or 0)
        nxt = _next_grounded_contract(decorated, scene_index)
        item["answer_target"] = _MECHANISM_INPUT_ANSWER_TARGET
        item["must_explain_causal_relevance_to_next_claim"] = True
        item["next_owned_claim_id"] = _text(nxt.get("owned_claim_id"))
        item["next_causal_role"] = _text(nxt.get("causal_role"))
        existing = _text(item.get("causal_role_instruction"))
        if _MECHANISM_INPUT_ANSWER_TARGET not in existing:
            item["causal_role_instruction"] = (
                existing + " " + _MECHANISM_INPUT_ANSWER_TARGET
            ).strip()
    return decorated


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    payload = _previous_writer_payload_before_mechanism_input_clue(candidate, plan)
    if not plan.get("grounded_claim_plan"):
        return payload
    payload["scene_contracts"] = _decorate_mechanism_input_contracts(
        payload.get("scene_contracts") or plan.get("contracts") or []
    )
    payload.setdefault("rules", {}).update({
        "mechanism_input_must_be_explicit_causal_clue": True,
        "mechanism_input_must_connect_to_next_owned_claim": True,
        "mechanism_input_must_not_invent_effect": True,
    })
    return payload


def local_repair_payload(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
    reasons: list[str],
) -> Dict[str, Any]:
    payload = _previous_local_repair_payload_before_mechanism_input_clue(
        script, plan, failed_scene_indexes, reasons
    )
    if not plan.get("grounded_claim_plan"):
        return payload

    contracts = _decorate_mechanism_input_contracts(plan.get("contracts") or [])
    by_index = {
        int(item.get("index") or 0): item
        for item in contracts
        if isinstance(item, dict) and item.get("index") is not None
    }
    for target in payload.get("targets") or []:
        scene_index = int(target.get("scene_index") or 0)
        contract = by_index.get(scene_index) or {}
        if str(contract.get("causal_role") or "") != "mechanism_input":
            continue
        target.update({
            "answer_target": _MECHANISM_INPUT_ANSWER_TARGET,
            "must_explain_causal_relevance_to_next_claim": True,
            "next_owned_claim_id": _text(contract.get("next_owned_claim_id")),
            "next_causal_role": _text(contract.get("next_causal_role")),
            "causal_role_instruction": _text(contract.get("causal_role_instruction")),
        })
    payload.setdefault("rules", {}).update({
        "repair_mechanism_input_as_explicit_causal_clue": True,
        "do_not_add_unowned_effect_to_make_causal_clue": True,
    })
    return payload
'''
    ENGINE.write_text(engine, encoding="utf-8")


print("✅ Run 33245676515 compact keyword + mechanism-input causal clue contracts applied")
