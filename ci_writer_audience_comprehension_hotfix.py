from pathlib import Path

ENGINE_PATH = Path("content/script_engine_v2.py")
RUNNER_PATH = Path("content/script_engine_v2_runner.py")
MARKER = "# SCRIPT_V2_AUDIENCE_COMPREHENSION_V1"
RUNNER_MARKER = "# SCRIPT_V2_AUDIENCE_WRITER_GUIDANCE_V1"


def _patch_engine():
    text = ENGINE_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        return False

    block = r'''

# SCRIPT_V2_AUDIENCE_COMPREHENSION_V1
# Preserve factual/causal locks while allowing the existing Writer call to
# rewrite audience-facing wording. The question remains exact because it is the
# curiosity bridge; phenomenon/reveal/payoff keep semantic ownership, not exact
# phrasing, so a zero-domain viewer can be introduced to unfamiliar terms first.
_script_v2_audience_previous_build_narrative_plan = build_narrative_plan


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    plan = _script_v2_audience_previous_build_narrative_plan(candidate, approved_hook=approved_hook)
    for contract in plan.get("contracts") or []:
        if not isinstance(contract, dict):
            continue
        if not contract.get("locked"):
            contract["text_lock_mode"] = "open"
        elif str(contract.get("role") or "") == "question":
            contract["text_lock_mode"] = "exact"
        else:
            contract["text_lock_mode"] = "semantic"
    plan["audience_comprehension"] = {
        "assume_zero_domain_knowledge": True,
        "visual_referent_before_unfamiliar_term": True,
        "plain_language_before_technical_name": True,
        "consistent_primary_term_per_concept": True,
        "claim_mentioned_is_not_explained": True,
        "bridge_each_causal_step": True,
        "grounded_only": True,
        "no_padding": True,
        "fixed_duration_target": False,
    }
    return plan


_script_v2_audience_previous_apply_locked_scenes = apply_locked_scenes


def apply_locked_scenes(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    semantic_text = {}
    scenes = script.get("scenes") if isinstance(script, dict) else None
    contracts = plan.get("contracts") if isinstance(plan, dict) else None
    if isinstance(scenes, list) and isinstance(contracts, list):
        for contract in contracts:
            if not isinstance(contract, dict) or contract.get("text_lock_mode") != "semantic":
                continue
            index = int(contract.get("index") or 0) - 1
            if 0 <= index < len(scenes) and isinstance(scenes[index], dict):
                value = _text(scenes[index].get("text"))
                if value:
                    semantic_text[index] = value

    result = _script_v2_audience_previous_apply_locked_scenes(script, plan)
    result_scenes = result.get("scenes") or []
    for index, value in semantic_text.items():
        if 0 <= index < len(result_scenes) and isinstance(result_scenes[index], dict):
            role = str((contracts[index] if index < len(contracts) else {}).get("role") or "")
            result_scenes[index]["text"] = deterministic_scene_repair(value, role)
    result["scenes"] = result_scenes
    return result


_script_v2_audience_previous_writer_payload = writer_payload


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    payload = _script_v2_audience_previous_writer_payload(candidate, plan)
    rules = payload.setdefault("rules", {})
    rules.pop("compress_single_causal_chain", None)
    rules.update({
        "assume_zero_domain_knowledge": True,
        "visual_referent_before_unfamiliar_term": True,
        "plain_language_location_then_technical_name": True,
        "consistent_primary_term_per_concept": True,
        "claim_mentioned_is_not_explanation": True,
        "bridge_each_causal_step_for_a_general_viewer": True,
        "compress_without_skipping_causal_bridges": True,
        "grounded_explanation_only": True,
        "no_padding_or_repetition": True,
        "no_fixed_duration_target": True,
    })
    payload["audience_comprehension"] = dict(plan.get("audience_comprehension") or {})
    return payload


_script_v2_audience_previous_repair_failed_scenes = repair_failed_scenes


def repair_failed_scenes(script: Dict[str, Any], plan: Dict[str, Any], failed_scene_indexes: list[int]) -> Dict[str, Any]:
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    contracts = plan.get("contracts") or []
    by_index = {int(item["index"]): item for item in contracts if isinstance(item, dict)}
    for scene_index in failed_scene_indexes:
        contract = by_index.get(int(scene_index))
        index = int(scene_index) - 1
        if not contract or not (0 <= index < len(scenes)) or not isinstance(scenes[index], dict):
            continue
        if contract.get("text_lock_mode") == "exact":
            scenes[index]["text"] = _normalize_locked_narration(
                contract.get("locked_text", ""), contract.get("role", "")
            )
        else:
            scenes[index]["text"] = deterministic_scene_repair(
                scenes[index].get("text", ""), contract.get("role", "")
            )
        scenes[index]["role"] = contract.get("role", "")
    result["scenes"] = scenes
    return apply_locked_scenes(result, plan)


_script_v2_audience_previous_local_repair_payload = local_repair_payload


def local_repair_payload(script: Dict[str, Any], plan: Dict[str, Any], failed_scene_indexes: list[int], reasons: list[str]) -> Dict[str, Any]:
    payload = _script_v2_audience_previous_local_repair_payload(
        script, plan, failed_scene_indexes, reasons
    )
    contracts = {
        int(item["index"]): item
        for item in plan.get("contracts") or []
        if isinstance(item, dict)
    }
    for target in payload.get("targets") or []:
        if not isinstance(target, dict):
            continue
        contract = contracts.get(int(target.get("scene_index") or 0)) or {}
        if contract.get("text_lock_mode") == "semantic":
            target["text_locked"] = False
            target["source_locked_text"] = _text(contract.get("locked_text"))
            target["locked_text"] = ""
    payload["audience_comprehension"] = dict(plan.get("audience_comprehension") or {})
    return payload
'''
    ENGINE_PATH.write_text(text.rstrip() + block + "\n", encoding="utf-8")
    return True


def _patch_runner():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    if RUNNER_MARKER in text:
        return False

    old_writer = (
        '            "Keep locked_text exact. Use formal Korean narration (~습니다/~합니다; questions only ~까요?). "\n'
        '            "Use easy language. Do not reveal the final answer before reveal/payoff."\n'
    )
    new_writer = (
        '            "# SCRIPT_V2_AUDIENCE_WRITER_GUIDANCE_V1 "\n'
        '            "Respect scene_contracts text_lock_mode: exact means keep locked_text exact; semantic means preserve the locked factual/causal meaning while rewriting wording for clarity. "\n'
        '            "Use formal Korean narration (~습니다/~합니다; questions only ~까요?). "\n'
        '            "Assume the viewer has zero domain knowledge. For an unfamiliar technical term, first identify the visible feature in plain language and where it is, then give the technical name. "\n'
        '            "Choose one primary Korean term for the same physical concept and use it consistently. "\n'
        '            "For mechanism and result scenes, do not merely name claims: explain the grounded causal bridge a general viewer needs to understand why the next step follows. "\n'
        '            "Use only supplied facts for those bridges; do not invent mechanism detail. Be concise, but never compress away a necessary causal bridge, and never pad or repeat to increase runtime. "\n'
        '            "Do not reveal the final answer before reveal/payoff."\n'
    )
    if old_writer not in text:
        raise RuntimeError("audience comprehension writer instruction marker not found")
    text = text.replace(old_writer, new_writer, 1)

    # Local-repair wording has legitimately changed across prior Script V2
    # composition hotfixes. Patch the legacy wording only when it is still
    # present; do not fail production composition merely because an established
    # hotfix already replaced that secondary prompt. The audience contract is
    # carried in each repair payload regardless.
    old_repair = (
        '            "For locked scenes, NEVER change text; visual_goal and keyword may be repaired. "\n'
        '            "Every keyword must be 2-7 ASCII English words. Use formal Korean and preserve factual scope."\n'
    )
    new_repair = (
        '            "For targets with text_locked=true, NEVER change text; semantic-lock targets may rewrite wording but must preserve source_locked_text factual/causal meaning. "\n'
        '            "Keep one primary term per concept and restore any missing causal bridge without adding unsupported facts or padding. "\n'
        '            "Every keyword must be 2-7 ASCII English words. Use formal Korean and preserve factual scope."\n'
    )
    if old_repair in text:
        text = text.replace(old_repair, new_repair, 1)
    RUNNER_PATH.write_text(text, encoding="utf-8")
    return True


def main():
    engine_changed = _patch_engine()
    runner_changed = _patch_runner()
    if not engine_changed and not runner_changed:
        print("✅ Script V2 audience comprehension guidance already installed")
    else:
        print("✅ Script V2 audience comprehension guidance installed")

    # Compose the narrower Run 33691170895 guard independently; #275 itself is
    # unchanged and remains authoritative for audience-comprehension semantics.
    from ci_run_33691170895_term_visual_subject_hotfix import main as _patch_run_33691170895
    _patch_run_33691170895()


if __name__ == "__main__":
    main()
