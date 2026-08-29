from pathlib import Path

ENGINE = Path("content/script_engine_v2.py")
RUNNER = Path("content/script_engine_v2_runner.py")

ENGINE_MARKER = "# WRITER_COMPLIANCE_PLAN_FIRST_V1"
RUNNER_MARKER = "# WRITER_COMPLIANCE_TRACE_V1"

engine = ENGINE.read_text(encoding="utf-8")
if ENGINE_MARKER not in engine:
    engine += r'''

# WRITER_COMPLIANCE_PLAN_FIRST_V1
# Reserve semantic claims before the Writer call so scene slots cannot compete
# for the same mechanism/result/payoff. No additional model calls are introduced.
from content.retention_structure import _semantic_atoms as _retention_semantic_atoms


def _writer_claims(text):
    return sorted(_retention_semantic_atoms(_text(text)))


def _writer_concept_key(text):
    value = _text(text)
    atoms = _writer_claims(value)
    if atoms:
        return "atom:" + "+".join(atoms)
    tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", value.lower())
    return "text:" + " ".join(tokens[:8])


def _writer_unique_concepts(candidate):
    ordered = []
    seen = set()
    for raw in list(candidate.get("fact_check_focus") or []) + list(candidate.get("visual_proof") or []):
        value = _text(raw)
        if not value:
            continue
        key = _writer_concept_key(value)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


def _writer_claim_owner_map(reveal, payoff, scene_count):
    owners = {}
    for claim in _writer_claims(reveal):
        owners.setdefault(claim, scene_count - 1)
    for claim in _writer_claims(payoff):
        if claim == "experience_payoff":
            owners[claim] = scene_count
        else:
            owners.setdefault(claim, scene_count - 1)
    return owners


def _writer_contract_dict(contract, *, purpose, allowed_claims, forbidden_claims, already_used_claims):
    data = contract.to_dict()
    data["semantic_purpose"] = purpose
    data["allowed_claims"] = list(allowed_claims)
    data["forbidden_claims"] = list(forbidden_claims)
    data["already_used_claims"] = list(already_used_claims)
    data["new_information_required"] = not bool(contract.locked)
    return data


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    """Build a compact claim-owned plan before spending a Writer call."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    micro = _micro(candidate)
    hook = _text(approved_hook) or _text(micro.get("hook"))
    question = _text(candidate.get("core_question")) or _text(micro.get("core_question"))
    reveal = _text(micro.get("reveal"))
    payoff = _text(micro.get("payoff"))
    missing = [name for name, value in (
        ("hook", hook), ("core_question", question), ("reveal", reveal), ("payoff", payoff)
    ) if not value]
    if missing:
        raise ValueError("missing narrative locks: " + ", ".join(missing))

    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):
        hook = _question_hook_to_observation(hook, candidate.get("topic"))
        if not hook:
            raise ValueError("scene 1 hook must be an observable statement, not a question")

    hook = _normalize_locked_narration(hook, "phenomenon")
    if not question.startswith("그런데"):
        question = "그런데 " + question
    question = _normalize_locked_narration(question, "question")
    reveal = _normalize_locked_narration(reveal, "reveal")
    payoff = _normalize_locked_narration(payoff, "payoff")

    retention = build_retention_plan(candidate)
    desired = max(5, int(retention["target_scene_count"]))
    concepts = _writer_unique_concepts(candidate)

    # Five structural roles are fixed. Extra slots exist only when supported
    # distinct concepts exist; runtime never creates a slot by itself.
    explanatory_slots = max(1, min(max(1, desired - 5), max(1, len(concepts))))
    scene_count = 5 + explanatory_slots

    owner_map = _writer_claim_owner_map(reveal, payoff, scene_count)
    reserved_claims = set(owner_map)
    usable_concepts = []
    for concept in concepts:
        claims = set(_writer_claims(concept))
        if claims and claims.issubset(reserved_claims):
            continue
        usable_concepts.append(concept)
    if usable_concepts:
        explanatory_slots = max(1, min(explanatory_slots, len(usable_concepts)))
        scene_count = 5 + explanatory_slots
        owner_map = _writer_claim_owner_map(reveal, payoff, scene_count)
        reserved_claims = set(owner_map)
    else:
        explanatory_slots = 1
        scene_count = 6
        owner_map = _writer_claim_owner_map(reveal, payoff, scene_count)
        reserved_claims = set(owner_map)

    contracts = [
        SceneContract(1, "phenomenon", True, hook, forbidden=("question", "answer")),
        SceneContract(2, "question", True, question, forbidden=("answer",)),
        SceneContract(3, "causal_clue", required_concepts=_concept_window(tuple(usable_concepts or concepts), 0), forbidden=("final_answer",)),
    ]
    middle_slots = scene_count - 5
    for offset in range(middle_slots):
        index = 4 + offset
        role = "consequence" if offset == middle_slots - 1 else f"mechanism_{offset + 1}"
        contracts.append(SceneContract(
            index,
            role,
            required_concepts=_concept_window(tuple(usable_concepts or concepts), offset + 1),
        ))
    contracts.extend([
        SceneContract(scene_count - 1, "reveal", True, reveal),
        SceneContract(scene_count, "payoff", True, payoff),
    ])

    plan_contracts = []
    used_claims = set()
    for contract in contracts:
        idx = contract.index
        required = list(contract.required_concepts)
        concept_claims = []
        for item in required:
            for claim in _writer_claims(item):
                if claim not in concept_claims and owner_map.get(claim, idx) == idx:
                    concept_claims.append(claim)
        owned = [claim for claim, owner in owner_map.items() if owner == idx]
        allowed = list(dict.fromkeys(owned + concept_claims))
        forbidden = sorted(claim for claim, owner in owner_map.items() if owner != idx)
        purpose = contract.role
        if required:
            purpose += ": " + " / ".join(required)
        plan_contracts.append(_writer_contract_dict(
            contract,
            purpose=purpose,
            allowed_claims=allowed,
            forbidden_claims=forbidden,
            already_used_claims=sorted(used_claims),
        ))
        used_claims.update(allowed)

    return {
        "version": "script-engine-v2-plan-first",
        "topic": _text(candidate.get("topic")),
        "angle": _text(candidate.get("angle")),
        "api_call_budget": MAX_SCRIPT_API_CALLS,
        "runtime_bucket": retention["runtime_bucket"],
        "target_scene_count": len(plan_contracts),
        "reserved_claim_owners": {key: int(value) for key, value in sorted(owner_map.items())},
        "contracts": plan_contracts,
    }


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    contracts = plan.get("contracts") or []
    return {
        "topic": plan.get("topic"),
        "angle": plan.get("angle"),
        "facts": list(candidate.get("fact_check_focus") or []),
        "visual_proof": list(candidate.get("visual_proof") or []),
        "runtime_bucket": plan.get("runtime_bucket"),
        "target_scene_count": len(contracts),
        "reserved_claim_owners": dict(plan.get("reserved_claim_owners") or {}),
        "scene_contracts": contracts,
        "rules": {
            "formal_korean": True,
            "easy_language": True,
            "do_not_change_locked_text": True,
            "follow_scene_contract_order_exactly": True,
            "use_each_reserved_claim_only_in_owner_scene": True,
            "do_not_use_forbidden_claims": True,
            "do_not_restate_already_used_claims": True,
            "new_information_each_scene": True,
            "single_payoff_only": True,
            "do_not_pad_runtime_or_scene_count": True,
            "no_generic_evaluation_scene": True,
            "no_visual_goal_or_meta_narration": True,
            "no_positive_effect_unless_supported_by_facts": True,
            "compress_single_causal_chain": True,
            "max_total_api_calls": MAX_SCRIPT_API_CALLS,
        },
    }


def _writer_duplicate_feedback(reasons, scene_index):
    duplicate_claim = ""
    owner_scene = None
    for reason in reasons or []:
        text = str(reason or "")
        if f"scene {scene_index}" not in text and not text.startswith(("new-information contract", "payoff contract")):
            continue
        match = re.search(r"semantic claim ([A-Za-z0-9_+-]+) reserved for scene (\d+)", text)
        if match:
            duplicate_claim = match.group(1)
            owner_scene = int(match.group(2))
            break
        match = re.search(r"payoff already reserved for scene (\d+)", text)
        if match:
            duplicate_claim = "experience_payoff"
            owner_scene = int(match.group(1))
            break
    return duplicate_claim, owner_scene


def local_repair_payload(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
    reasons: list[str],
) -> Dict[str, Any]:
    contracts = {int(item["index"]): item for item in plan.get("contracts") or []}
    scenes = script.get("scenes") or []
    targets = []
    for scene_index in failed_scene_indexes:
        scene_index = int(scene_index)
        contract = contracts.get(scene_index)
        index = scene_index - 1
        if not (contract and 0 <= index < len(scenes) and isinstance(scenes[index], dict)):
            continue
        duplicate_claim, owner_scene = _writer_duplicate_feedback(reasons, scene_index)
        targets.append({
            "scene_index": scene_index,
            "role": contract.get("role"),
            "required_concepts": contract.get("required_concepts") or [],
            "semantic_purpose": contract.get("semantic_purpose", contract.get("role")),
            "allowed_claims": contract.get("allowed_claims") or [],
            "forbidden_claims": contract.get("forbidden_claims") or [],
            "already_used_claims": contract.get("already_used_claims") or [],
            "duplicate_claim": duplicate_claim,
            "owner_scene_index": owner_scene,
            "required_role": contract.get("role"),
            "must_replace_with": contract.get("semantic_purpose", contract.get("role")),
            "current_text": _text(scenes[index].get("text")),
            "text_locked": bool(contract.get("locked")),
            "locked_text": _text(contract.get("locked_text")) if contract.get("locked") else "",
            "current_visual_goal": _text(scenes[index].get("visual_goal")),
            "current_keyword": _text(scenes[index].get("keyword")),
        })
    return {
        "targets": targets,
        "validation_reasons": list(reasons or []),
        "rules": {
            "repair_only_targets": True,
            "formal_korean": True,
            "easy_language": True,
            "do_not_rewrite_other_scenes": True,
            "locked_scene_text_is_immutable": True,
            "metadata_on_locked_scenes_may_be_repaired": True,
            "replace_duplicate_with_target_semantic_purpose": True,
            "do_not_use_forbidden_claims": True,
            "do_not_restate_already_used_claims": True,
            "new_information_each_scene": True,
            "no_generic_evaluation_scene": True,
            "no_positive_effect_unless_supported_by_facts": True,
            "max_local_repair_calls": MAX_LOCAL_REPAIR_CALLS,
        },
    }
'''
    ENGINE.write_text(engine, encoding="utf-8")

runner = RUNNER.read_text(encoding="utf-8")
if RUNNER_MARKER not in runner:
    runner += r'''

# WRITER_COMPLIANCE_TRACE_V1
# Keep the same 1 full Writer + <=2 local repair budget. Only make the
# generation contract and diagnostics more explicit.
def _writer_response_format(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    if mode != "writer":
        return {"type": "json_object"}
    contracts = payload.get("scene_contracts") or []
    scene_count = len(contracts)
    if scene_count < 1 or scene_count != int(payload.get("target_scene_count") or 0):
        raise ValueError("writer scene schema must match unique narrative plan contracts")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "shorts_script",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "scenes": {
                        "type": "array",
                        "minItems": scene_count,
                        "maxItems": scene_count,
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "visual_goal": {"type": "string"},
                                "keyword": {"type": "string"},
                            },
                            "required": ["text", "visual_goal", "keyword"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "scenes"],
                "additionalProperties": False,
            },
        },
    }


def _default_call(payload: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    authorize_call(MODEL)
    if mode == "writer":
        instruction = (
            "Return JSON only with top-level keys title and scenes. "
            "Write exactly one scene for each scene_contract, in the same order; never invent extra slots. "
            "Each scene must contain text, visual_goal, and an English 2-7 word keyword. "
            "Treat reserved_claim_owners and every scene's semantic_purpose/allowed_claims/forbidden_claims/"
            "already_used_claims as authoritative. A reserved semantic claim may appear only in its owner scene. "
            "Do not paraphrase a prior mechanism/result/payoff into a later scene. "
            "If a scene has no distinct supported information beyond its semantic_purpose, keep it concise rather than adding filler. "
            "Keep locked_text exact. Use formal Korean narration (~습니다/~합니다; questions only ~까요?). "
            "For EVERY scene, keyword must use ASCII English words only. Preserve factual scope."
        )
    else:
        instruction = (
            "Return JSON only as {\"repairs\":[...]}. Repair ONLY the listed target scenes. "
            "Use duplicate_claim, owner_scene_index, required_role, must_replace_with, allowed_claims, forbidden_claims, "
            "and already_used_claims literally: remove the duplicate claim and replace it with new information for the target role. "
            "For locked scenes, NEVER change text; visual_goal and keyword may be repaired. "
            "Every keyword must be 2-7 ASCII English words. Use formal Korean and preserve factual scope."
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


def _writer_trace(attempt, plan, validation=None):
    reasons = list((validation or {}).get("reasons") or [])
    failed = list((validation or {}).get("failed_scene_indexes") or [])
    duplicated = []
    for reason in reasons:
        match = re.search(r"semantic claim ([A-Za-z0-9_+-]+) reserved for scene (\d+)", str(reason))
        if match:
            duplicated.append({"semantic_role": match.group(1), "owner_scene_index": int(match.group(2))})
        elif "payoff already reserved for scene" in str(reason):
            match = re.search(r"scene (\d+)", str(reason))
            duplicated.append({"semantic_role": "experience_payoff", "owner_scene_index": int(match.group(1)) if match else None})
    trace = {
        "attempt": int(attempt),
        "target_scene_count": int(plan.get("target_scene_count") or 0),
        "scene_roles": [str(item.get("role", "")) for item in plan.get("contracts") or []],
        "validation_failure_reason": reasons,
        "offending_scene_indexes": failed,
        "duplicated_semantic_roles": duplicated,
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
    validation = validate_script_v2(script, plan)
    _writer_trace(1, plan, validation if not validation["valid"] else None)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    script = repair_failed_scenes(script, plan, validation["failed_scene_indexes"])
    script = _normalize_script_contracts_without_api(script, plan)
    validation = validate_script_v2(script, plan)
    if validation["valid"]:
        script["script_engine_v2_calls"] = call_count
        return script

    for attempt in range(2, 2 + MAX_LOCAL_REPAIR_CALLS):
        indexes = validation["failed_scene_indexes"]
        payload = local_repair_payload(script, plan, indexes, validation["reasons"])
        allowed = {int(item["scene_index"]) for item in payload["targets"]}
        locked_text_indexes = {int(item["scene_index"]) for item in payload["targets"] if item.get("text_locked")}
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
        validation = validate_script_v2(script, plan)
        _writer_trace(attempt, plan, validation if not validation["valid"] else None)
        if validation["valid"]:
            script["script_engine_v2_calls"] = call_count
            return script

    raise RuntimeError(
        "Script Engine V2 validation failed within 3 calls: " + " | ".join(validation["reasons"])
    )
'''
    RUNNER.write_text(runner, encoding="utf-8")

print("✅ Writer Compliance Plan-First V1 applied; API/retry ceilings unchanged")
