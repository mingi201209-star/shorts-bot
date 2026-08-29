"""Production counterexamples from Runs 33243842268 and 33244982236."""
import importlib
import runpy

runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_role_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_contrast_hotfix.py", run_name="__main__")
runpy.run_path("ci_live_script_blockers_hotfix.py", run_name="__main__")

import content.script_engine_v2 as engine
import content.script_engine_v2_runner as runner
import content.script_generator_router as router
from content.script_formal_endings import formalize_declarative_text
from quality import script_engine_v2_grounded_claim_plan_regression_test as grounded_base

engine = importlib.reload(engine)
runner = importlib.reload(runner)
router = importlib.reload(router)


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
    validation = runner._combined_validation(hostile, plan)
    assert validation["valid"] is False, validation
    reasons = " | ".join(validation["reasons"])
    assert "unplanned factual claim" in reasons, reasons


def assert_e_locked_scene1_uses_shared_formal_corpus():
    normalized = router._normalize_locked_candidate_narration(_candidate(_live_chevron_claims()))
    assert normalized["micro_narrative"]["hook"] == "비행기 엔진 뒤쪽의 톱니 모양이 눈에 띕니다."
    assert formalize_declarative_text("플랩이 펼쳐진다.") == "플랩이 펼쳐진다."


def main():
    assert_a_live_chevrons_collapse_to_five_scenes()
    assert_b_distinct_downstream_state_stays_separate()
    assert_c_distinct_multistep_grounding_keeps_eight_scenes()
    assert_d_unsupported_drag_fuel_stability_still_fail()
    assert_e_locked_scene1_uses_shared_formal_corpus()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("RUN 33244982236 MORPHOLOGY COLLAPSE REGRESSION: PASS")


if __name__ == "__main__":
    main()
