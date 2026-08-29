from pathlib import Path


ENGINE = Path("content/script_engine_v2.py")
RUNNER = Path("content/script_engine_v2_runner.py")
ENGINE_MARKER = "# GROUNDED_CAUSAL_CONTRAST_CONTRACT_V2"
RUNNER_MARKER = "# GROUNDED_CAUSAL_CONTRAST_PROMPT_V2"


engine = ENGINE.read_text(encoding="utf-8")
if ENGINE_MARKER not in engine:
    engine += r'''

# GROUNDED_CAUSAL_CONTRAST_CONTRACT_V2
# Refine #245 without weakening validation: adjacent grounded causal scenes
# receive different deterministic answer targets. If trusted evidence cannot
# support a distinct transition state, compact the plan instead of inventing one.
from content.grounded_claim_plan import _tokens as _grounded_claim_tokens

_previous_build_narrative_plan_before_causal_contrast = build_narrative_plan
_previous_writer_payload_before_causal_contrast = writer_payload
_previous_local_repair_payload_before_causal_contrast = local_repair_payload


_CAUSAL_ANSWER_TARGETS = {
    "mechanism_input": "What condition, interface, force, or state exists before the subject acts?",
    "constraint": "What supported constraint or boundary condition exists?",
    "mechanism_change": "What does the subject directly change or do to the mechanism?",
    "mechanism_transition": "What new downstream state is different because of the previous direct change?",
    "primary_result": "What verified result follows from that downstream state?",
    "tradeoff": "What supported limitation or trade-off follows?",
    "supported_fact_step": "What new supported factual state is introduced here?",
}


def _causal_answer_target(role):
    return _CAUSAL_ANSWER_TARGETS.get(
        _text(role), _CAUSAL_ANSWER_TARGETS["supported_fact_step"]
    )


def _claim_scope_values(claim):
    values = [_text(claim.get("evidence_summary"))]
    values.extend(
        _text(item) for item in claim.get("allowed_paraphrase_scope") or []
    )
    return [item for item in values if item]


def _claim_scope_token_set(claim):
    result = set()
    for value in _claim_scope_values(claim):
        result.update(_grounded_claim_tokens(value))
    return result


def _evidence_state_delta(previous_claim, current_claim):
    """Return only source-backed lexical state delta; never infer a new fact.

    A transition is independently narratable only when its trusted evidence has
    at least one content token not present in the previous claim's entire
    paraphrase scope. The selected delta phrase is copied from trusted evidence,
    not generated here. Exact/paraphrase-equivalent fixtures therefore compact.
    """
    previous_tokens = _claim_scope_token_set(previous_claim)
    values = _claim_scope_values(current_claim)
    best_phrase = ""
    best_novel = []
    for value in values:
        novel = sorted(set(_grounded_claim_tokens(value)) - previous_tokens)
        if len(novel) > len(best_novel):
            best_phrase = value
            best_novel = novel
    return {
        "supported": bool(best_novel),
        "evidence_phrase": best_phrase if best_novel else "",
        "novel_terms": best_novel,
    }


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
                    collapsed.append({
                        "claim_id": _text(claim.get("claim_id")),
                        "claim_type": _text(claim.get("claim_type")),
                        "collapsed_into_claim_id": _text(previous.get("claim_id")),
                        "reason": "no evidence-backed downstream state delta",
                    })
                    continue
        kept.append(claim)
    return kept, collapsed


def _enrich_causal_contrast(plan):
    claims = {
        int(item.get("owner_scene") or 0): item
        for item in plan.get("grounded_claim_plan") or []
        if isinstance(item, dict)
    }
    contracts = plan.get("contracts") or []
    by_index = {
        int(item.get("index") or 0): item
        for item in contracts if isinstance(item, dict)
    }
    for index in sorted(by_index):
        contract = by_index[index]
        role = _text(contract.get("causal_role"))
        if not role:
            continue
        answer_target = _causal_answer_target(role)
        contract["answer_target"] = answer_target
        previous_contract = by_index.get(index - 1) or {}
        previous_claim = claims.get(index - 1) or {}
        current_claim = claims.get(index) or {}
        previous_role = _text(previous_contract.get("causal_role"))
        if previous_role:
            contract["previous_scene_owned_claim"] = _text(
                previous_contract.get("owned_claim_id")
            )
            contract["previous_scene_answer_target"] = _text(
                previous_contract.get("answer_target")
            ) or _causal_answer_target(previous_role)
            contract["must_not_answer_same_question_as_previous_scene"] = True
            contract["forbidden_semantic_relation"] = (
                "restate_previous_owned_claim:"
                + _text(previous_contract.get("owned_claim_id"))
            )
        else:
            contract["previous_scene_owned_claim"] = ""
            contract["previous_scene_answer_target"] = ""
            contract["must_not_answer_same_question_as_previous_scene"] = False
            contract["forbidden_semantic_relation"] = ""

        if role == "mechanism_transition" and previous_claim:
            delta = _evidence_state_delta(previous_claim, current_claim)
            contract["required_state_delta"] = delta["evidence_phrase"]
            contract["required_state_delta_terms"] = delta["novel_terms"]
            contract["required_state_delta_evidence_backed"] = bool(delta["supported"])
        else:
            contract["required_state_delta"] = ""
            contract["required_state_delta_terms"] = []
            contract["required_state_delta_evidence_backed"] = False
    return plan


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    initial = _previous_build_narrative_plan_before_causal_contrast(
        candidate, approved_hook=approved_hook
    )
    claims = initial.get("grounded_claim_plan") or []
    if not claims:
        return initial

    kept, collapsed = _compact_indistinct_transitions(candidate, claims)
    if collapsed:
        if len(kept) < 3:
            raise ValueError(
                "grounded causal contrast leaves fewer than 3 distinct supported factual claims"
            )
        compact_candidate = deepcopy(candidate)
        compact_candidate["_trusted_grounded_claims"] = [
            {
                key: deepcopy(value)
                for key, value in item.items()
                if key not in ("owner_scene", "provenance_present")
            }
            for item in kept
        ]
        initial = _previous_build_narrative_plan_before_causal_contrast(
            compact_candidate, approved_hook=approved_hook
        )
        initial["collapsed_grounded_claims"] = collapsed
        initial["scene_collapse_reason"] = "indistinct adjacent grounded causal evidence"
    else:
        initial["collapsed_grounded_claims"] = []

    return _enrich_causal_contrast(initial)


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    payload = _previous_writer_payload_before_causal_contrast(candidate, plan)
    if not plan.get("grounded_claim_plan"):
        return payload
    payload["causal_contrast_contract"] = [
        {
            "scene_index": int(item.get("index") or 0),
            "owned_claim_id": _text(item.get("owned_claim_id")),
            "causal_role": _text(item.get("causal_role")),
            "answer_target": _text(item.get("answer_target")),
            "previous_scene_owned_claim": _text(item.get("previous_scene_owned_claim")),
            "previous_scene_answer_target": _text(item.get("previous_scene_answer_target")),
            "must_not_answer_same_question_as_previous_scene": bool(
                item.get("must_not_answer_same_question_as_previous_scene")
            ),
            "required_state_delta": _text(item.get("required_state_delta")),
            "required_state_delta_terms": list(item.get("required_state_delta_terms") or []),
            "forbidden_semantic_relation": _text(item.get("forbidden_semantic_relation")),
        }
        for item in plan.get("contracts") or []
        if _text(item.get("owned_claim_id"))
    ]
    payload["collapsed_grounded_claims"] = deepcopy(
        plan.get("collapsed_grounded_claims") or []
    )
    payload.setdefault("rules", {}).update({
        "answer_each_causal_scene_target_exactly_once": True,
        "mechanism_change_answers_direct_change_only": True,
        "mechanism_transition_answers_downstream_state_only": True,
        "must_not_answer_previous_scene_target": True,
        "required_state_delta_must_come_from_trusted_evidence": True,
        "compact_plan_when_no_distinct_evidence_delta": True,
    })
    return payload


def local_repair_payload(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
    reasons: list[str],
) -> Dict[str, Any]:
    payload = _previous_local_repair_payload_before_causal_contrast(
        script, plan, failed_scene_indexes, reasons
    )
    if not plan.get("grounded_claim_plan"):
        return payload
    contracts = {
        int(item.get("index") or 0): item
        for item in plan.get("contracts") or []
        if isinstance(item, dict)
    }
    for target in payload.get("targets") or []:
        contract = contracts.get(int(target.get("scene_index") or 0)) or {}
        target.update({
            "answer_target": _text(contract.get("answer_target")),
            "previous_scene_owned_claim": _text(contract.get("previous_scene_owned_claim")),
            "previous_scene_answer_target": _text(contract.get("previous_scene_answer_target")),
            "must_not_answer_same_question_as_previous_scene": bool(
                contract.get("must_not_answer_same_question_as_previous_scene")
            ),
            "required_state_delta": _text(contract.get("required_state_delta")),
            "required_state_delta_terms": list(
                contract.get("required_state_delta_terms") or []
            ),
            "forbidden_semantic_relation": _text(
                contract.get("forbidden_semantic_relation")
            ),
        })
    payload.setdefault("rules", {}).update({
        "repair_must_answer_target_not_previous_target": True,
        "repair_state_delta_must_be_evidence_backed": True,
        "repair_must_not_restate_forbidden_semantic_relation": True,
    })
    return payload
'''
    ENGINE.write_text(engine, encoding="utf-8")


runner = RUNNER.read_text(encoding="utf-8")
if RUNNER_MARKER not in runner:
    runner += r'''

# GROUNDED_CAUSAL_CONTRAST_PROMPT_V2
_previous_default_call_before_causal_contrast = _default_call


def _default_call(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    grounded_mode = bool(
        payload.get("grounded_claim_plan") or payload.get("grounded_claim_mode")
    )
    if not grounded_mode:
        return _previous_default_call_before_causal_contrast(payload, mode=mode)

    authorize_call(MODEL)
    if mode == "writer":
        instruction = (
            "Return JSON only with top-level keys title and scenes. "
            "The Grounded Claim Plan, scene ownership, and causal_contrast_contract are authoritative. "
            "For each factual scene answer its answer_target, not merely its causal-role label. "
            "A mechanism_change scene answers what the subject DIRECTLY changes or does. "
            "A mechanism_transition scene answers what NEW downstream state is different BECAUSE OF that direct change. "
            "If required_state_delta is present, use only that trusted evidence plus the scene's supporting_evidence_summary and allowed_paraphrase_scope to express the new state. "
            "Never re-answer previous_scene_answer_target and never restate previous_scene_owned_claim as a paraphrase. "
            "Do not invent a downstream fact when the evidence does not contain one; plan compaction is handled before this call. "
            "Use each owned claim exactly once and never add function, benefit, safety, comfort, performance, efficiency, stability, or other outcomes unless owned and grounded. "
            "Keep locked opening text exact. Use natural formal Korean (~습니다/~합니다; questions only ~까요?). "
            "Each scene must contain text, visual_goal, and an English 2-7 word keyword."
        )
    else:
        instruction = (
            "Return JSON only as {\"repairs\":[...]}. Repair ONLY listed targets. "
            "Treat answer_target, previous_scene_answer_target, previous_scene_owned_claim, required_state_delta, required_state_delta_terms, and forbidden_semantic_relation as a structured contrast contract. "
            "The repaired narration must answer answer_target and must NOT answer previous_scene_answer_target again. "
            "For mechanism_transition, express the evidence-backed required_state_delta as the new downstream state; do not merely say the previous mechanism happens more, better, or again. "
            "Use only the target owned_claim, supporting_evidence_summary, allowed_paraphrase_scope, and required_state_delta. "
            "Do not add unplanned factual claims and do not change locked text. "
            "Each repair may include text, visual_goal and keyword only as needed; keywords remain 2-7 ASCII English words."
        )
    response = openai.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format=_writer_response_format(payload, mode=mode),
    )
    record_usage(MODEL, response)
    return _extract_json(response.choices[0].message.content)
'''
    RUNNER.write_text(runner, encoding="utf-8")


print("✅ Grounded Causal Contrast Contract V2 applied; validators/API/retry ceilings unchanged")
