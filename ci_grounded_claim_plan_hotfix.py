from pathlib import Path


ENGINE = Path("content/script_engine_v2.py")
RUNNER = Path("content/script_engine_v2_runner.py")
ENGINE_MARKER = "# GROUNDED_CLAIM_PLAN_WRITER_V2"
RUNNER_MARKER = "# GROUNDED_CLAIM_VALIDATION_TRACE_V2"


engine = ENGINE.read_text(encoding="utf-8")
if ENGINE_MARKER not in engine:
    engine += r'''

# GROUNDED_CLAIM_PLAN_WRITER_V2
# Grounding -> source-backed claim plan -> unique owner scene -> Writer.
# The legacy Plan-First V1 remains the fallback when no private trusted claim
# channel exists, preserving existing non-grounded/legacy behavior.
from content.grounded_claim_plan import build_grounded_claim_plan as _build_grounded_claim_plan

_original_build_narrative_plan_before_grounded_claims = build_narrative_plan
_original_writer_payload_before_grounded_claims = writer_payload
_original_local_repair_payload_before_grounded_claims = local_repair_payload


def _grounded_opening(candidate, approved_hook=""):
    micro = _micro(candidate)
    hook = _text(approved_hook) or _text(micro.get("hook"))
    question = _text(candidate.get("core_question")) or _text(micro.get("core_question"))
    if not hook or not question:
        raise ValueError("grounded claim plan requires opening hook and core question")
    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):
        hook = _question_hook_to_observation(hook, candidate.get("topic"))
        if not hook:
            raise ValueError("scene 1 hook must be an observable statement, not a question")
    hook = _normalize_locked_narration(hook, "phenomenon")
    if not question.startswith("그런데"):
        question = "그런데 " + question
    question = _normalize_locked_narration(question, "question")
    return hook, question


def _grounded_role(scene_index, scene_count):
    if scene_index == 3:
        return "causal_clue"
    if scene_index == scene_count:
        return "payoff"
    if scene_index == scene_count - 1:
        return "reveal"
    return f"mechanism_{scene_index - 3}"


def _grounded_contract(contract, claim, all_claim_ids, already_used):
    data = contract.to_dict()
    claim_id = _text(claim.get("claim_id"))
    data.update({
        "semantic_purpose": f"{contract.role}: {_text(claim.get('claim_type'))}",
        "owned_claim_id": claim_id,
        "owned_claim": _text(claim.get("evidence_summary")),
        "supporting_evidence_summary": _text(claim.get("evidence_summary")),
        "grounding_provenance_present": bool(claim.get("provenance_present")),
        "allowed_claims": [claim_id],
        "forbidden_claims": [item for item in all_claim_ids if item != claim_id],
        "already_used_claims": list(already_used),
        "new_information_required": True,
    })
    return data


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    grounded_claims = _build_grounded_claim_plan(candidate)
    if not grounded_claims:
        return _original_build_narrative_plan_before_grounded_claims(candidate, approved_hook=approved_hook)
    if len(grounded_claims) < 3:
        # Do not manufacture filler just to retain a structural quota.
        raise ValueError("grounded claim plan requires at least 3 distinct supported factual claims")

    hook, question = _grounded_opening(candidate, approved_hook)
    retention = build_retention_plan(candidate)
    scene_count = 2 + len(grounded_claims)
    all_claim_ids = [_text(item.get("claim_id")) for item in grounded_claims]

    contracts = [
        SceneContract(1, "phenomenon", True, hook, forbidden=("question", "answer")),
        SceneContract(2, "question", True, question, forbidden=("answer",)),
    ]
    plan_contracts = [
        {
            **contracts[0].to_dict(),
            "semantic_purpose": "phenomenon: canonical physical observation",
            "owned_claim_id": "",
            "owned_claim": "",
            "supporting_evidence_summary": "",
            "grounding_provenance_present": bool(candidate.get("_trusted_grounding_evidence")),
            "allowed_claims": [],
            "forbidden_claims": list(all_claim_ids),
            "already_used_claims": [],
            "new_information_required": False,
        },
        {
            **contracts[1].to_dict(),
            "semantic_purpose": "question: ask why the observed physical feature exists",
            "owned_claim_id": "",
            "owned_claim": "",
            "supporting_evidence_summary": "",
            "grounding_provenance_present": bool(candidate.get("_trusted_grounding_evidence")),
            "allowed_claims": [],
            "forbidden_claims": list(all_claim_ids),
            "already_used_claims": [],
            "new_information_required": False,
        },
    ]

    already_used = []
    for claim in grounded_claims:
        index = int(claim["owner_scene"])
        role = _grounded_role(index, scene_count)
        summary = _text(claim.get("evidence_summary"))
        contract = SceneContract(
            index,
            role,
            False,
            "",
            required_concepts=(summary,),
            forbidden=(),
        )
        plan_contracts.append(_grounded_contract(
            contract,
            claim,
            all_claim_ids,
            already_used,
        ))
        already_used.append(_text(claim.get("claim_id")))

    owner_map = {
        _text(item.get("claim_id")): int(item.get("owner_scene"))
        for item in grounded_claims
    }
    return {
        "version": "script-engine-v2-grounded-claim-plan",
        "topic": _text(candidate.get("topic")),
        "angle": _text(candidate.get("angle")),
        "canonical_subject": _text(candidate.get("canonical_subject")),
        "api_call_budget": MAX_SCRIPT_API_CALLS,
        "runtime_bucket": retention["runtime_bucket"],
        "target_scene_count": len(plan_contracts),
        "reserved_claim_owners": owner_map,
        "grounded_claim_plan": grounded_claims,
        "contracts": plan_contracts,
    }


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    if not plan.get("grounded_claim_plan"):
        return _original_writer_payload_before_grounded_claims(candidate, plan)
    contracts = plan.get("contracts") or []
    claims = deepcopy(plan.get("grounded_claim_plan") or [])
    return {
        "topic": plan.get("topic"),
        "angle": plan.get("angle"),
        "canonical_subject": plan.get("canonical_subject"),
        "runtime_bucket": plan.get("runtime_bucket"),
        "target_scene_count": len(contracts),
        "reserved_claim_owners": dict(plan.get("reserved_claim_owners") or {}),
        "grounded_claim_plan": claims,
        "scene_contracts": contracts,
        "rules": {
            "formal_korean": True,
            "easy_language": True,
            "do_not_change_locked_text": True,
            "follow_scene_contract_order_exactly": True,
            "writer_does_not_choose_facts": True,
            "use_each_owned_claim_exactly_once": True,
            "reject_unplanned_factual_claims": True,
            "do_not_use_forbidden_claims": True,
            "do_not_restate_already_used_claims": True,
            "new_information_each_scene": True,
            "payoff_must_use_owned_grounded_result_or_tradeoff": True,
            "do_not_add_generic_positive_outcomes": True,
            "do_not_pad_runtime_or_scene_count": True,
            "no_visual_goal_or_meta_narration": True,
            "max_total_api_calls": MAX_SCRIPT_API_CALLS,
        },
    }


def local_repair_payload(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
    reasons: list[str],
) -> Dict[str, Any]:
    payload = _original_local_repair_payload_before_grounded_claims(
        script, plan, failed_scene_indexes, reasons
    )
    if not plan.get("grounded_claim_plan"):
        return payload

    claims = {
        _text(item.get("claim_id")): item
        for item in plan.get("grounded_claim_plan") or []
    }
    for target in payload.get("targets") or []:
        claim_id = _text(target.get("allowed_claims", [""])[0] if target.get("allowed_claims") else "")
        claim = claims.get(claim_id) or {}
        target["owned_claim_id"] = claim_id
        target["owned_claim"] = _text(claim.get("evidence_summary"))
        target["supporting_evidence_summary"] = _text(claim.get("evidence_summary"))
        target["allowed_paraphrase_scope"] = list(claim.get("allowed_paraphrase_scope") or [])
        target["grounding_provenance_present"] = bool(claim.get("provenance_present"))
        target["must_replace_with"] = _text(claim.get("evidence_summary")) or target.get("must_replace_with")
    payload["grounded_claim_plan"] = deepcopy(plan.get("grounded_claim_plan") or [])
    payload["grounded_claim_mode"] = True
    payload.setdefault("rules", {}).update({
        "writer_does_not_choose_facts": True,
        "repair_must_realize_owned_claim_only": True,
        "reject_unplanned_factual_claims": True,
        "use_each_owned_claim_exactly_once": True,
    })
    return payload
'''
    ENGINE.write_text(engine, encoding="utf-8")


runner = RUNNER.read_text(encoding="utf-8")
if RUNNER_MARKER not in runner:
    runner += r'''

# GROUNDED_CLAIM_VALIDATION_TRACE_V2
from content.grounded_claim_plan import validate_grounded_claim_usage as _validate_grounded_claim_usage

_previous_default_call_before_grounded_claims = _default_call


def _default_call(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    grounded_mode = bool(payload.get("grounded_claim_plan") or payload.get("grounded_claim_mode"))
    if not grounded_mode:
        return _previous_default_call_before_grounded_claims(payload, mode=mode)

    authorize_call(MODEL)
    if mode == "writer":
        instruction = (
            "Return JSON only with top-level keys title and scenes. "
            "Write exactly one scene for each scene_contract in order. "
            "The Grounded Claim Plan is authoritative: you DO NOT decide what factual effects exist. "
            "For each factual scene, express only owned_claim_id using supporting_evidence_summary and "
            "allowed_paraphrase_scope. Never add a function, benefit, safety, comfort, performance, efficiency, "
            "stability, or other outcome unless it is an owned grounded claim. "
            "Do not state another scene's forbidden_claims and do not repeat already_used_claims. "
            "The payoff may only express its owned grounded result/tradeoff; do not invent a better-sounding ending. "
            "Keep locked opening text exact. Use natural formal Korean (~습니다/~합니다; questions only ~까요?). "
            "Each scene must contain text, visual_goal, and an English 2-7 word keyword."
        )
    else:
        instruction = (
            "Return JSON only as {\"repairs\":[...]}. Repair ONLY listed targets. "
            "Replace unsupported/duplicate narration with a natural Korean paraphrase of that target's owned_claim "
            "and supporting_evidence_summary. Do not add any factual claim outside allowed_paraphrase_scope. "
            "Do not change locked text. Each repair may include text, visual_goal and keyword only as needed; "
            "keywords remain 2-7 ASCII English words."
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


def _combined_validation(script, plan):
    base = validate_script_v2(script, plan)
    extra = _validate_grounded_claim_usage(script, plan)
    failures = list(base.get("failures") or []) + list(extra or [])
    deduped = []
    seen = set()
    for failure in failures:
        key = (failure.get("scene_index"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)
    return {
        "valid": not deduped,
        "failures": deduped,
        "failed_scene_indexes": sorted({
            int(item["scene_index"])
            for item in deduped
            if isinstance(item.get("scene_index"), int)
        }),
        "reasons": [str(item.get("reason", "")) for item in deduped],
    }


def _writer_trace(attempt, plan, validation=None):
    reasons = list((validation or {}).get("reasons") or [])
    failed = list((validation or {}).get("failed_scene_indexes") or [])
    duplicate_claims = [reason for reason in reasons if "duplicate claim" in str(reason)]
    unplanned_claims = [reason for reason in reasons if "unplanned factual claim" in str(reason)]
    scene_claims = []
    for item in plan.get("contracts") or []:
        scene_claims.append({
            "scene_index": int(item.get("index") or 0),
            "semantic_purpose": str(item.get("semantic_purpose", item.get("role", ""))),
            "owned_claim_id": str(item.get("owned_claim_id", "")),
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


def generate_script_v2(
    candidate: Dict[str, Any],
    approved_hook: str = "",
    *,
    call_fn: Callable[..., Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    caller = call_fn or _default_call
    candidate, approved_hook = _normalize_candidate_opening(candidate, approved_hook)
    plan = build_narrative_plan(candidate, approved_hook=approved_hook)
    call_count = 0

    generated = caller(writer_payload(candidate, plan), mode="writer")
    call_count += 1
    if call_count > MAX_SCRIPT_API_CALLS:
        raise RuntimeError("Script Engine V2 call budget exceeded")
    generated = _normalize_writer_envelope(generated)
    script = apply_locked_scenes(generated, plan)
    script = _normalize_script_contracts_without_api(script, plan)
    validation = _combined_validation(script, plan)
    _writer_trace(1, plan, validation if not validation["valid"] else None)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    script = repair_failed_scenes(script, plan, validation["failed_scene_indexes"])
    script = _normalize_script_contracts_without_api(script, plan)
    validation = _combined_validation(script, plan)
    if validation["valid"]:
        _writer_trace(1, plan, None)
        script["script_engine_v2_calls"] = call_count
        return script

    for attempt in range(2, 2 + MAX_LOCAL_REPAIR_CALLS):
        indexes = validation["failed_scene_indexes"]
        payload = local_repair_payload(script, plan, indexes, validation["reasons"])
        allowed = {int(item["scene_index"]) for item in payload["targets"]}
        locked_text_indexes = {
            int(item["scene_index"])
            for item in payload["targets"]
            if item.get("text_locked")
        }
        if not allowed:
            break
        response = caller(payload, mode="local_repair")
        call_count += 1
        if call_count > MAX_SCRIPT_API_CALLS:
            raise RuntimeError("Script Engine V2 call budget exceeded")
        script = _apply_local_repairs(script, response, allowed, locked_text_indexes)
        script = apply_locked_scenes(script, plan)
        script = repair_failed_scenes(script, plan, list(allowed))
        script = _normalize_script_contracts_without_api(script, plan)
        validation = _combined_validation(script, plan)
        _writer_trace(attempt, plan, validation if not validation["valid"] else None)
        if validation["valid"]:
            script["script_engine_v2_calls"] = call_count
            return script

    raise RuntimeError(
        "Script Engine V2 validation failed within 3 calls: " + " | ".join(validation["reasons"])
    )
'''
    RUNNER.write_text(runner, encoding="utf-8")


print("✅ Grounded Claim Plan + ownership validation applied; API/retry ceilings unchanged")
