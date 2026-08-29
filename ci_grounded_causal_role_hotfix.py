from pathlib import Path


ENGINE = Path("content/script_engine_v2.py")
RUNNER = Path("content/script_engine_v2_runner.py")
ENGINE_MARKER = "# GROUNDED_CAUSAL_ROLE_DISTINCTION_V1"
RUNNER_MARKER = "# GROUNDED_CAUSAL_ROLE_PROMPT_V1"


engine = ENGINE.read_text(encoding="utf-8")
if ENGINE_MARKER not in engine:
    engine += r'''

# GROUNDED_CAUSAL_ROLE_DISTINCTION_V1
# Keep the #244 trusted claim plan/ownership untouched. This layer only tells
# Writer/repair how adjacent causal claims differ as information states.
_previous_grounded_contract_before_causal_roles = _grounded_contract
_previous_writer_payload_before_causal_roles = writer_payload
_previous_local_repair_payload_before_causal_roles = local_repair_payload


def _grounded_causal_role(claim_type):
    value = _text(claim_type)
    if value == "mechanism_input":
        return "mechanism_input"
    if value in ("constraint",):
        return "constraint"
    if value == "mechanism_change":
        return "mechanism_change"
    if value in ("mechanism_step", "mechanism_effect"):
        return "mechanism_transition"
    if value in ("result", "primary_result", "payoff"):
        return "primary_result"
    if value == "tradeoff":
        return "tradeoff"
    return "supported_fact_step"


def _grounded_causal_instruction(causal_role):
    return {
        "mechanism_input": (
            "Describe the condition, interface, force, or state that exists before the subject changes it."
        ),
        "constraint": (
            "Describe the supported constraint or boundary condition without turning it into an outcome."
        ),
        "mechanism_change": (
            "Describe what the subject directly changes or does to the mechanism."
        ),
        "mechanism_transition": (
            "Describe the new downstream state, transition, distribution, or condition that results from the previous mechanism change. "
            "Do not merely paraphrase the previous scene's action or say that the same process happens more/better."
        ),
        "primary_result": (
            "Describe only the supported observable result that follows from the preceding causal state."
        ),
        "tradeoff": (
            "Describe only the supported cost, limitation, or trade-off."
        ),
        "supported_fact_step": (
            "Describe this supported factual step as new information rather than restating an adjacent scene."
        ),
    }.get(causal_role, "Describe a new supported factual state for this causal step.")


def _grounded_contract(contract, claim, all_claim_ids, already_used):
    data = _previous_grounded_contract_before_causal_roles(
        contract, claim, all_claim_ids, already_used
    )
    claim_type = _text(claim.get("claim_type"))
    causal_role = _grounded_causal_role(claim_type)
    data["grounded_claim_type"] = claim_type
    data["causal_role"] = causal_role
    data["causal_role_instruction"] = _grounded_causal_instruction(causal_role)
    data["must_describe_new_downstream_state"] = causal_role == "mechanism_transition"
    return data


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    payload = _previous_writer_payload_before_causal_roles(candidate, plan)
    if not plan.get("grounded_claim_plan"):
        return payload
    payload["causal_role_contract"] = {
        role: _grounded_causal_instruction(role)
        for role in (
            "mechanism_input",
            "constraint",
            "mechanism_change",
            "mechanism_transition",
            "primary_result",
            "tradeoff",
        )
    }
    payload.setdefault("rules", {}).update({
        "causal_roles_are_semantically_distinct": True,
        "adjacent_causal_scene_must_advance_state": True,
        "mechanism_transition_must_describe_downstream_state": True,
        "do_not_paraphrase_previous_causal_action_as_new_state": True,
    })
    return payload


def _causal_duplicate_feedback(reasons, scene_index):
    offending_claim = ""
    owner_scene = None
    for reason in reasons or []:
        text = str(reason or "")
        duplicate = re.search(
            r"duplicate claim ([A-Za-z0-9_:+-]+) owner_scene=(\d+) offending_scene=(\d+)",
            text,
        )
        if duplicate and int(duplicate.group(3)) == int(scene_index):
            offending_claim = duplicate.group(1)
            owner_scene = int(duplicate.group(2))
            break
        repeated = re.search(
            r"semantic claim ([A-Za-z0-9_:+-]+) reserved for scene (\d+)",
            text,
        )
        if repeated:
            offending_claim = repeated.group(1)
            owner_scene = int(repeated.group(2))
            break
    return offending_claim, owner_scene


def local_repair_payload(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
    reasons: list[str],
) -> Dict[str, Any]:
    payload = _previous_local_repair_payload_before_causal_roles(
        script, plan, failed_scene_indexes, reasons
    )
    if not plan.get("grounded_claim_plan"):
        return payload

    contracts = {
        int(item.get("index")): item
        for item in plan.get("contracts") or []
        if isinstance(item, dict) and item.get("index") is not None
    }
    scenes = script.get("scenes") or []
    for target in payload.get("targets") or []:
        scene_index = int(target.get("scene_index") or 0)
        contract = contracts.get(scene_index) or {}
        offending_claim, owner_scene = _causal_duplicate_feedback(reasons, scene_index)
        if not offending_claim:
            offending_claim = _text(target.get("duplicate_claim"))
        if owner_scene is None and target.get("owner_scene_index") is not None:
            owner_scene = int(target.get("owner_scene_index"))
        owner_contract = contracts.get(int(owner_scene or 0)) or {}
        target.update({
            "offending_scene": scene_index,
            "owner_scene": owner_scene,
            "offending_claim": offending_claim,
            "required_owned_claim": _text(target.get("owned_claim_id")),
            "owner_causal_role": _text(owner_contract.get("causal_role")),
            "required_causal_role": _text(contract.get("causal_role")),
            "causal_role_instruction": _text(contract.get("causal_role_instruction")),
            "must_describe_new_downstream_state": bool(
                contract.get("must_describe_new_downstream_state")
            ),
        })
        if owner_scene and 0 < int(owner_scene) <= len(scenes):
            owner = scenes[int(owner_scene) - 1]
            if isinstance(owner, dict):
                target["owner_scene_text"] = _text(owner.get("text"))

    payload.setdefault("rules", {}).update({
        "do_not_paraphrase_owner_scene": True,
        "adjacent_causal_repair_must_advance_state": True,
        "downstream_state_required_when_flagged": True,
    })
    return payload
'''
    ENGINE.write_text(engine, encoding="utf-8")


runner = RUNNER.read_text(encoding="utf-8")
if RUNNER_MARKER not in runner:
    runner += r'''

# GROUNDED_CAUSAL_ROLE_PROMPT_V1
_previous_default_call_before_causal_roles = _default_call


def _default_call(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    grounded_mode = bool(payload.get("grounded_claim_plan") or payload.get("grounded_claim_mode"))
    if not grounded_mode:
        return _previous_default_call_before_causal_roles(payload, mode=mode)

    authorize_call(MODEL)
    if mode == "writer":
        instruction = (
            "Return JSON only with top-level keys title and scenes. "
            "Write exactly one scene for each scene_contract in order. "
            "The Grounded Claim Plan and claim ownership are authoritative; do not invent factual effects. "
            "For every factual scene, obey causal_role and causal_role_instruction as well as owned_claim_id. "
            "Causal roles are information-state boundaries, not labels that may be paraphrased away: "
            "mechanism_input states the pre-existing condition; mechanism_change states what the subject directly changes; "
            "mechanism_transition states the NEW downstream state/transition caused by that change; primary_result states only the supported outcome. "
            "Adjacent causal scenes must advance the state. Never turn a mechanism_transition into a synonym, stronger version, or repeated description of the prior mechanism_change. "
            "Use only supporting_evidence_summary and allowed_paraphrase_scope for factual content. "
            "Never add function, benefit, safety, comfort, performance, efficiency, stability, or other outcomes unless owned and grounded. "
            "Do not use forbidden_claims or repeat already_used_claims. Keep locked opening text exact. "
            "Use natural formal Korean (~습니다/~합니다; questions only ~까요?). "
            "Each scene must contain text, visual_goal, and an English 2-7 word keyword."
        )
    else:
        instruction = (
            "Return JSON only as {\"repairs\":[...]}. Repair ONLY listed targets. "
            "Use offending_scene, owner_scene, offending_claim, required_owned_claim, owner_causal_role, required_causal_role, "
            "owner_scene_text, causal_role_instruction, and must_describe_new_downstream_state as a structured repair contract. "
            "Remove the offending duplicate; do not paraphrase owner_scene_text. "
            "When must_describe_new_downstream_state is true, narration MUST describe the new downstream state/transition resulting from the owner scene's change, "
            "not say that the same process happens, mixes, changes, improves, or is controlled again. "
            "Realize only the target owned_claim using its supporting_evidence_summary and allowed_paraphrase_scope. "
            "Do not add any factual claim outside the grounded plan. Do not change locked text. "
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


_previous_writer_trace_before_causal_roles = _writer_trace


def _writer_trace(attempt, plan, validation=None):
    reasons = list((validation or {}).get("reasons") or [])
    failed = list((validation or {}).get("failed_scene_indexes") or [])
    duplicate_claims = [
        reason for reason in reasons
        if "duplicate claim" in str(reason) or "repeats semantic claim" in str(reason)
    ]
    unplanned_claims = [
        reason for reason in reasons if "unplanned factual claim" in str(reason)
    ]
    scene_claims = []
    for item in plan.get("contracts") or []:
        scene_claims.append({
            "scene_index": int(item.get("index") or 0),
            "semantic_purpose": str(item.get("semantic_purpose", item.get("role", ""))),
            "owned_claim_id": str(item.get("owned_claim_id", "")),
            "causal_role": str(item.get("causal_role", "")),
            "grounding_provenance_present": bool(item.get("grounding_provenance_present")),
        })
    trace = {
        "attempt": int(attempt),
        "target_scene_count": int(plan.get("target_scene_count") or 0),
        "scene_claims": scene_claims,
        "duplicate_claims": duplicate_claims,
        "unplanned_claims": unplanned_claims,
        "validation_failure_reason": reasons,
        "offending_scene_indexes": failed,
    }
    print("[WRITER_COMPLIANCE_TRACE] " + json.dumps(trace, ensure_ascii=False, sort_keys=True))
'''
    RUNNER.write_text(runner, encoding="utf-8")


print("✅ Grounded causal-role distinction applied; claim plan/API/retry ceilings unchanged")
