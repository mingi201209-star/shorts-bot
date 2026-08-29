"""Counterexamples for Run 33242742380 grounded causal Writer collapse."""
import importlib
import runpy


runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_role_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_contrast_hotfix.py", run_name="__main__")

import content.script_engine_v2 as engine
import content.script_engine_v2_runner as runner
from quality import script_engine_v2_grounded_claim_plan_regression_test as grounded_base

engine = importlib.reload(engine)
runner = importlib.reload(runner)


def _scene(text, keyword="aircraft mechanism detail"):
    return {
        "text": text,
        "visual_goal": "실제 구조와 작동 관계를 가까이 보여주는 장면입니다.",
        "keyword": keyword,
    }


def _candidate():
    return grounded_base.run_332398_candidate()


def _script(scene5_text):
    return {
        "title": "비행기 엔진 뒤 톱니의 이유",
        "scenes": [
            _scene("비행기 엔진 뒤는 톱니처럼 생겼습니다.", "aircraft jet engine chevron"),
            _scene("그런데 비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까요?", "jet engine chevron detail"),
            _scene("엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥 공기 흐름이 서로 만납니다.", "jet exhaust flow interface"),
            _scene("톱니 가장자리는 이 두 흐름이 섞이는 방식을 바꿉니다.", "chevron exhaust flow mixing"),
            _scene(scene5_text, "chevron gradual flow transition"),
            _scene("그 결과 셰브론의 주된 효과는 제트 소음을 줄이는 것입니다.", "jet engine noise reduction"),
        ],
    }


def assert_a_same_change_paraphrase_fails():
    plan = engine.build_narrative_plan(_candidate())
    bad = engine.apply_locked_scenes(
        _script("이 구조는 공기가 더 잘 섞이도록 합니다."), plan
    )
    validation = runner._combined_validation(bad, plan)
    assert validation["valid"] is False, validation
    assert 5 in validation["failed_scene_indexes"], validation


def assert_b_distinct_evidence_backed_state_passes():
    plan = engine.build_narrative_plan(_candidate())
    good = engine.apply_locked_scenes(
        _script("그래서 두 흐름 사이의 급격한 경계가 더 점진적인 전환으로 바뀝니다."),
        plan,
    )
    validation = runner._combined_validation(good, plan)
    assert validation["valid"] is True, validation

    scene5 = next(item for item in plan["contracts"] if item["index"] == 5)
    assert scene5["causal_role"] == "mechanism_transition"
    assert scene5["answer_target"].startswith("What new downstream state")
    assert scene5["previous_scene_owned_claim"] == "chevron_flow_mixing"
    assert scene5["must_not_answer_same_question_as_previous_scene"] is True
    assert scene5["required_state_delta_evidence_backed"] is True
    assert scene5["required_state_delta"]
    assert scene5["required_state_delta_terms"]
    assert scene5["forbidden_semantic_relation"] == (
        "restate_previous_owned_claim:chevron_flow_mixing"
    )


def assert_c_indistinct_evidence_collapses_to_compact_plan():
    claims = [
        grounded_base._claim(
            "input", "mechanism_input",
            "두 흐름이 경계에서 만납니다.",
            ["두 흐름이 경계에서 만납니다."],
        ),
        grounded_base._claim(
            "change", "mechanism_change",
            "구조가 두 흐름이 섞이는 방식을 바꿉니다.",
            ["구조가 두 흐름이 섞이는 방식을 바꿉니다."],
        ),
        # Deliberately no independently supported downstream state: this is
        # merely a second copy of the direct-change evidence.
        grounded_base._claim(
            "transition_copy", "mechanism_effect",
            "구조가 두 흐름이 섞이는 방식을 바꿉니다.",
            ["구조가 두 흐름이 섞이는 방식을 바꿉니다."],
        ),
        grounded_base._claim(
            "result", "result",
            "그 변화는 측정 가능한 소음을 줄입니다.",
            ["측정 가능한 소음을 줄입니다."],
        ),
    ]
    candidate = grounded_base._synthetic_candidate(
        "generic grounded flow device",
        "이 장치에는 특별한 가장자리가 있습니다.",
        "왜 이 가장자리가 필요할까요?",
        claims,
    )
    plan = engine.build_narrative_plan(candidate)
    assert plan["target_scene_count"] == 5, plan
    assert [item["claim_id"] for item in plan["grounded_claim_plan"]] == [
        "input", "change", "result"
    ]
    assert plan["collapsed_grounded_claims"] == [{
        "claim_id": "transition_copy",
        "claim_type": "mechanism_effect",
        "collapsed_into_claim_id": "change",
        "reason": "no evidence-backed downstream state delta",
    }]


def assert_d_distinct_multistep_chain_stays_expanded():
    claims = [
        grounded_base._claim("input_a", "mechanism_input", "초기 상태 A가 존재합니다.", ["초기 상태 A"]),
        grounded_base._claim("change_a", "mechanism_change", "대상이 상태 A를 직접 바꿉니다.", ["상태 A를 직접 바꿉니다"]),
        grounded_base._claim("step_a", "mechanism_step", "그 뒤 새로운 분포 B가 형성됩니다.", ["새로운 분포 B"]),
        grounded_base._claim("effect_a", "mechanism_effect", "분포 B는 경계 상태 C로 전환됩니다.", ["경계 상태 C"]),
        grounded_base._claim("result_a", "result", "상태 C는 관찰 가능한 결과 D를 만듭니다.", ["결과 D"]),
        grounded_base._claim("tradeoff_a", "tradeoff", "이 과정에는 제한 E가 있습니다.", ["제한 E"]),
    ]
    candidate = grounded_base._synthetic_candidate(
        "generic multi-step physical system",
        "이 구조에는 여러 단계가 있습니다.",
        "왜 이 구조는 여러 단계를 거칠까요?",
        claims,
    )
    plan = engine.build_narrative_plan(candidate)
    assert plan["target_scene_count"] == 8, plan
    assert len(plan["grounded_claim_plan"]) == 6
    assert plan["collapsed_grounded_claims"] == []


def assert_e_unsupported_expansion_still_fails():
    candidate = _candidate()
    plan = engine.build_narrative_plan(candidate)
    hostile = {
        "title": "비행기 엔진 뒤 톱니의 이유",
        "scenes": [
            _scene("비행기 엔진 뒤는 톱니처럼 생겼습니다."),
            _scene("그런데 비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까요?"),
            _scene("엔진 뒤에서는 뜨거운 배기와 차가운 바깥 흐름이 만납니다."),
            _scene("톱니는 두 흐름이 섞이는 방식을 바꾸면서 항력을 줄입니다."),
            _scene("두 흐름의 경계가 더 점진적으로 바뀌어 연료 효율이 향상됩니다."),
            _scene("그래서 소음이 줄고 비행 안정성도 증가합니다."),
        ],
    }
    hostile = engine.apply_locked_scenes(hostile, plan)
    validation = runner._combined_validation(hostile, plan)
    assert validation["valid"] is False, validation
    reasons = " | ".join(validation["reasons"])
    assert "unplanned factual claim" in reasons, reasons
    assert any(term in reasons for term in ("항력", "연료", "효율", "안정")), reasons


def assert_writer_and_repair_payload_contract():
    candidate = _candidate()
    plan = engine.build_narrative_plan(candidate)
    payload = engine.writer_payload(candidate, plan)
    scene5 = next(
        item for item in payload["causal_contrast_contract"]
        if item["scene_index"] == 5
    )
    assert scene5["owned_claim_id"] == "mixing_transition"
    assert scene5["previous_scene_owned_claim"] == "chevron_flow_mixing"
    assert scene5["required_state_delta"]
    assert payload["rules"]["must_not_answer_previous_scene_target"] is True

    duplicate = engine.apply_locked_scenes(
        _script("이 구조는 공기가 더 잘 섞이도록 합니다."), plan
    )
    reason = (
        "new-information contract: scene repeats semantic claim airflow_mixing "
        "reserved for scene 4"
    )
    repair = engine.local_repair_payload(duplicate, plan, [5], [reason])
    target = repair["targets"][0]
    assert target["answer_target"].startswith("What new downstream state")
    assert target["previous_scene_answer_target"].startswith("What does the subject directly change")
    assert target["previous_scene_owned_claim"] == "chevron_flow_mixing"
    assert target["required_state_delta"]
    assert target["required_state_delta_terms"]
    assert target["must_not_answer_same_question_as_previous_scene"] is True
    assert repair["rules"]["repair_must_answer_target_not_previous_target"] is True


def main():
    assert_a_same_change_paraphrase_fails()
    assert_b_distinct_evidence_backed_state_passes()
    assert_c_indistinct_evidence_collapses_to_compact_plan()
    assert_d_distinct_multistep_chain_stays_expanded()
    assert_e_unsupported_expansion_still_fails()
    assert_writer_and_repair_payload_contract()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("RUN 33242742380 GROUNDED CAUSAL CONTRAST REGRESSION: PASS")


if __name__ == "__main__":
    main()
