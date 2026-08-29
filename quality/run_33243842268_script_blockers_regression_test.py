"""Production counterexamples from Runs 33243842268, 33244982236, 33245676515, and 33246584198."""
import importlib
import runpy

runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_role_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_contrast_hotfix.py", run_name="__main__")
runpy.run_path("ci_live_script_blockers_hotfix.py", run_name="__main__")
runpy.run_path("ci_run_33245676515_script_contract_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_keyword_contract_hotfix.py", run_name="__main__")

import content.script_engine_v2 as engine
import content.script_engine_v2_runner as runner
import content.script_engine_v2_validation as validation
import content.script_generator_router as router
import content.retention_structure as retention
from content.script_formal_endings import formalize_declarative_text
from quality import script_engine_v2_grounded_claim_plan_regression_test as grounded_base

engine = importlib.reload(engine)
runner = importlib.reload(runner)
validation = importlib.reload(validation)
router = importlib.reload(router)
retention = importlib.reload(retention)


def _claim(claim_id, claim_type, evidence, scopes):
    return grounded_base._claim(claim_id, claim_type, evidence, scopes)


def _candidate(claims):
    candidate = grounded_base._synthetic_candidate(
        "jet engine nacelle/nozzle chevrons",
        "비행기 엔진 뒤쪽의 톱니 모양이 눈에 띈다.",
        "왜 비행기 엔진 뒤는 톱니처럼 생겼을까요?",
        claims,
    )
    candidate["topic"] = "비행기 엔진 뒤는 왜 톱니처럼 생겼을까"
    return candidate


def _live_chevron_claims():
    return [
        _claim("flow_interface", "mechanism_input", "Hot exhaust/core flow and cooler surrounding flow meet at the nozzle boundary.", ["The hot and cooler flows meet at the nozzle boundary."]),
        _claim("chevron_flow_mixing", "mechanism_change", "Chevron edges change how the two flows mix.", ["The chevrons change how the flow mixes."]),
        _claim("mixing_transition", "mechanism_effect", "The two flows mix more gradually across the boundary.", ["The two flows mix more gradually across the boundary."]),
        _claim("noise_reduction", "result", "The more gradual mixing reduces jet noise.", ["Chevron mixing reduces jet noise."]),
    ]


def assert_a_live_chevrons_collapse_to_five_scenes():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    assert plan["target_scene_count"] == 5, plan
    claims = plan["grounded_claim_plan"]
    assert [item["claim_id"] for item in claims] == ["flow_interface", "chevron_flow_mixing", "noise_reduction"], claims
    collapsed = plan["collapsed_grounded_claims"]
    assert len(collapsed) == 1, collapsed
    assert collapsed[0]["claim_id"] == "mixing_transition", collapsed
    assert collapsed[0]["collapsed_into_claim_id"] == "chevron_flow_mixing", collapsed
    assert "modifier-or-morphology-only delta" in collapsed[0]["semantic_reason"], collapsed
    change = next(item for item in claims if item["claim_id"] == "chevron_flow_mixing")
    assert "The two flows mix more gradually across the boundary." in change["allowed_paraphrase_scope"]
    result = next(item for item in claims if item["claim_id"] == "noise_reduction")
    assert result["owner_scene"] == 5, result


def assert_b_distinct_downstream_state_stays_separate():
    claims = [
        _claim("input", "mechanism_input", "A stream enters a narrow passage.", ["A stream enters the passage."]),
        _claim("change", "mechanism_change", "Guide vanes redirect the stream.", ["The vanes redirect the stream."]),
        _claim("transition", "mechanism_effect", "A separated recirculation zone forms downstream.", ["A downstream recirculation zone forms."]),
        _claim("result", "result", "The new flow state reduces measured pulsation.", ["Measured pulsation is reduced."]),
    ]
    plan = engine.build_narrative_plan(_candidate(claims))
    assert plan["target_scene_count"] == 6, plan
    assert [item["claim_id"] for item in plan["grounded_claim_plan"]] == ["input", "change", "transition", "result"]
    assert plan["collapsed_grounded_claims"] == []


def assert_c_distinct_multistep_grounding_keeps_eight_scenes():
    claims = [
        _claim("input_a", "mechanism_input", "Initial state A exists.", ["Initial state A"]),
        _claim("change_a", "mechanism_change", "The subject directly changes state A.", ["State A is directly changed."]),
        _claim("step_a", "mechanism_step", "A new distribution B forms.", ["New distribution B"]),
        _claim("effect_a", "mechanism_effect", "Distribution B creates state C.", ["Distinct state C"]),
        _claim("result_a", "result", "State C produces observable result D.", ["Observable result D"]),
        _claim("tradeoff_a", "tradeoff", "The process has supported limit E.", ["Supported limit E"]),
    ]
    plan = engine.build_narrative_plan(_candidate(claims))
    assert plan["target_scene_count"] == 8, plan
    assert len(plan["grounded_claim_plan"]) == 6


def _scene(text, keyword="aircraft mechanism detail"):
    return {"text": text, "visual_goal": "실제 구조와 작동 관계를 가까이 보여주는 장면입니다.", "keyword": keyword}


def assert_d_unsupported_drag_fuel_stability_still_fail():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    hostile = {"title": "비행기 엔진 뒤 톱니의 이유", "scenes": [
        _scene("비행기 엔진 뒤쪽의 톱니 모양이 눈에 띕니다."),
        _scene("왜 비행기 엔진 뒤는 톱니처럼 생겼을까요?"),
        _scene("엔진 뒤에서는 뜨거운 흐름과 더 차가운 흐름이 만납니다."),
        _scene("톱니는 흐름이 섞이는 방식을 바꾸고 항력을 줄여 연료 효율도 높입니다."),
        _scene("그 결과 제트 소음이 줄고 안정성도 증가합니다."),
    ]}
    hostile = engine.apply_locked_scenes(hostile, plan)
    validation_result = runner._combined_validation(hostile, plan)
    assert validation_result["valid"] is False, validation_result
    reasons = " | ".join(validation_result["reasons"])
    assert "unplanned factual claim" in reasons, reasons


def assert_e_locked_scene1_uses_shared_formal_corpus():
    normalized = router._normalize_locked_candidate_narration(_candidate(_live_chevron_claims()))
    assert normalized["micro_narrative"]["hook"] == "비행기 엔진 뒤쪽의 톱니 모양이 눈에 띕니다."
    assert formalize_declarative_text("플랩이 펼쳐진다.") == "플랩이 펼쳐진다."


def _compact_keyword_script(plan, keywords):
    texts = [
        "비행기 엔진 뒤쪽의 톱니 모양이 눈에 띕니다.",
        "그런데 왜 비행기 엔진 뒤는 톱니처럼 생겼을까요?",
        "뜨거운 배기 흐름과 더 차가운 공기의 차이가 노즐 경계에서 만납니다.",
        "톱니 가장자리는 두 흐름이 섞이는 방식을 바꿉니다.",
        "그 변화는 제트 소음을 줄이는 데 도움을 줍니다.",
    ]
    scenes = []
    for text, keyword, contract in zip(texts, keywords, plan["contracts"]):
        scenes.append({
            "text": text,
            "visual_goal": "jet engine chevron mechanism close view",
            "keyword": keyword,
            "role": contract["role"],
        })
    return {"title": "chevrons", "scenes": scenes}


def assert_f_run_33245676515_five_scene_keyword_variety_passes():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    script = _compact_keyword_script(plan, [
        "jet engine chevron",
        "jet engine nozzle",
        "jet engine exhaust core flow",
        "jet engine chevron flow mixing",
        "jet engine noise reduction",
    ])
    _, failures = validation.validate_scene_basics(script, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword variety too low" not in reasons, reasons
    assert "keyword not grounded" not in reasons, reasons
    assert "keyword missing canonical subject context" not in reasons, reasons


def assert_g_actual_keyword_collapse_still_fails():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    script = _compact_keyword_script(plan, ["jet engine chevron"] * 5)
    _, failures = validation.validate_scene_basics(script, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword variety too low" in reasons, reasons


def assert_h_unrelated_keyword_filler_still_fails():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    script = _compact_keyword_script(plan, [
        "jet engine chevron",
        "jet engine nozzle",
        "jet engine exhaust core flow",
        "jet engine innovative abstract novelty",
        "jet engine noise reduction",
    ])
    _, failures = validation.validate_scene_basics(script, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword not grounded in owned claim evidence" in reasons, reasons


def _first5_scenes(scene3_text):
    return [
        {"text": "엔진 뒤 톱니가 보입니다.", "visual_goal": "jet engine chevrons", "retention_role": "phenomenon"},
        {"text": "그런데 왜 이런 모양일까요?", "visual_goal": "jet engine nozzle", "retention_role": "question"},
        {"text": scene3_text, "visual_goal": "jet exhaust interface", "retention_role": "causal_clue"},
    ]


def assert_i_scene3_passive_state_without_causal_clue_fails():
    ok, reason = retention.validate_first5_progression(
        _first5_scenes("두 흐름은 노즐 경계에서 만납니다.")
    )
    assert ok is False, reason
    assert "explicit causal clue" in reason, reason


def assert_j_grounded_explicit_causal_clue_passes_and_writer_receives_contract():
    ok, reason = retention.validate_first5_progression(
        _first5_scenes("두 흐름의 속도 차이 때문에 노즐 경계의 조건이 달라집니다.")
    )
    assert ok is True, reason

    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    payload = engine.writer_payload(_candidate(_live_chevron_claims()), plan)
    scene3 = payload["scene_contracts"][2]
    assert scene3["causal_role"] == "mechanism_input", scene3
    assert scene3["must_explain_causal_relevance_to_next_claim"] is True, scene3
    assert scene3["next_owned_claim_id"] == "chevron_flow_mixing", scene3
    assert "causally relevant" in scene3["answer_target"], scene3


def assert_k_run_33246584198_normalizer_generates_claim_aware_keywords():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    raw = _compact_keyword_script(plan, ["aircraft mechanism detail"] * 5)
    normalized = runner._normalize_script_contracts_without_api(raw, plan)
    keywords = [scene["keyword"] for scene in normalized["scenes"]]
    factual = keywords[2:]
    assert len(set(factual)) == 3, keywords
    assert "flow" in factual[0] and "interface" in factual[0], factual
    assert "chevron" in factual[1] and "mixing" in factual[1], factual
    assert "noise" in factual[2] and "reduction" in factual[2], factual
    for keyword in factual:
        assert "jet" in keyword and "engine" in keyword, factual
    _, failures = validation.validate_scene_basics(normalized, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword variety too low" not in reasons, reasons
    assert "keyword not grounded" not in reasons, reasons
    assert "keyword missing canonical subject context" not in reasons, reasons


def assert_l_stage_only_decoration_does_not_count_as_diversity():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    script = _compact_keyword_script(plan, [
        "aircraft engine stage 1",
        "aircraft engine stage 2",
        "aircraft engine stage 3",
        "aircraft engine stage 4",
        "aircraft engine stage 5",
    ])
    _, failures = validation.validate_scene_basics(script, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword variety too low" in reasons, reasons


def assert_m_canonical_identity_without_claim_specific_term_fails():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    script = _compact_keyword_script(plan, [
        "jet engine chevron",
        "jet engine chevron",
        "jet engine chevron",
        "jet engine chevron",
        "jet engine chevron",
    ])
    _, failures = validation.validate_scene_basics(script, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword not grounded in owned claim evidence" in reasons, reasons


def assert_n_claim_term_without_canonical_context_fails():
    plan = engine.build_narrative_plan(_candidate(_live_chevron_claims()))
    script = _compact_keyword_script(plan, [
        "jet engine chevron",
        "jet engine nozzle",
        "exhaust core flow interface",
        "chevron flow mixing",
        "noise reduction",
    ])
    _, failures = validation.validate_scene_basics(script, plan)
    reasons = " | ".join(str(item.get("reason", "")) for item in failures)
    assert "keyword missing canonical subject context" in reasons, reasons


def assert_o_non_grounded_legacy_keyword_path_is_preserved():
    scene = {"keyword": "city bridge detail", "visual_goal": "city bridge close view"}
    contract = {"required_concepts": ["bridge structure"]}
    plan = {"topic": "도시 다리는 왜 이런 구조일까", "angle": "structure"}
    result = runner._deterministic_keyword(scene, contract, plan, 1)
    assert result == "city bridge detail", result


def main():
    assert_a_live_chevrons_collapse_to_five_scenes()
    assert_b_distinct_downstream_state_stays_separate()
    assert_c_distinct_multistep_grounding_keeps_eight_scenes()
    assert_d_unsupported_drag_fuel_stability_still_fail()
    assert_e_locked_scene1_uses_shared_formal_corpus()
    assert_f_run_33245676515_five_scene_keyword_variety_passes()
    assert_g_actual_keyword_collapse_still_fails()
    assert_h_unrelated_keyword_filler_still_fails()
    assert_i_scene3_passive_state_without_causal_clue_fails()
    assert_j_grounded_explicit_causal_clue_passes_and_writer_receives_contract()
    assert_k_run_33246584198_normalizer_generates_claim_aware_keywords()
    assert_l_stage_only_decoration_does_not_count_as_diversity()
    assert_m_canonical_identity_without_claim_specific_term_fails()
    assert_n_claim_term_without_canonical_context_fails()
    assert_o_non_grounded_legacy_keyword_path_is_preserved()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("RUN 33246584198 GROUNDED KEYWORD CONTRACT REGRESSION: PASS")


if __name__ == "__main__":
    main()
