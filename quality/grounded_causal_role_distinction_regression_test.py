"""Deterministic regression for Run 33241229064 adjacent causal-claim collapse."""
import contextlib
import importlib
import io
import json
import runpy


# Reproduce the final Writer composition used by production.
runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_causal_role_hotfix.py", run_name="__main__")

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


def _run_332412_candidate():
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


def assert_plan_unchanged_and_roles_added():
    candidate = _run_332412_candidate()
    plan = engine.build_narrative_plan(candidate)
    claims = plan["grounded_claim_plan"]
    assert [item["claim_id"] for item in claims] == [
        "flow_interface",
        "chevron_flow_mixing",
        "mixing_transition",
        "noise_reduction",
    ]
    assert [item["owner_scene"] for item in claims] == [3, 4, 5, 6]
    assert plan["target_scene_count"] == 6

    by_scene = {int(item["index"]): item for item in plan["contracts"]}
    assert by_scene[3]["causal_role"] == "mechanism_input"
    assert by_scene[4]["causal_role"] == "mechanism_change"
    assert by_scene[5]["causal_role"] == "mechanism_transition"
    assert by_scene[5]["must_describe_new_downstream_state"] is True
    assert by_scene[6]["causal_role"] == "primary_result"

    payload = engine.writer_payload(candidate, plan)
    assert payload["rules"]["causal_roles_are_semantically_distinct"] is True
    assert payload["rules"]["adjacent_causal_scene_must_advance_state"] is True
    assert payload["rules"]["mechanism_transition_must_describe_downstream_state"] is True
    assert "facts" not in payload


def assert_run_332412_duplicate_still_fails_and_transition_passes():
    candidate = _run_332412_candidate()
    plan = engine.build_narrative_plan(candidate)

    duplicate = _script("이 구조는 공기가 더 잘 섞이도록 합니다.")
    duplicate = engine.apply_locked_scenes(duplicate, plan)
    duplicate_validation = runner._combined_validation(duplicate, plan)
    assert duplicate_validation["valid"] is False, duplicate_validation
    assert 5 in duplicate_validation["failed_scene_indexes"], duplicate_validation

    good = _script("그 결과 두 흐름 사이의 급격한 속도 차가 더 점진적인 전환으로 바뀝니다.")
    good = engine.apply_locked_scenes(good, plan)
    good_validation = runner._combined_validation(good, plan)
    assert good_validation["valid"] is True, good_validation


def assert_live_repair_feedback_is_structured():
    candidate = _run_332412_candidate()
    plan = engine.build_narrative_plan(candidate)
    duplicate = engine.apply_locked_scenes(
        _script("이 구조는 공기가 더 잘 섞이도록 합니다."),
        plan,
    )
    live_reason = (
        "new-information contract: scene repeats semantic claim airflow_mixing "
        "reserved for scene 4"
    )
    payload = engine.local_repair_payload(duplicate, plan, [5], [live_reason])
    target = payload["targets"][0]
    assert target["offending_scene"] == 5
    assert target["owner_scene"] == 4
    assert target["offending_claim"] == "airflow_mixing"
    assert target["required_owned_claim"] == "mixing_transition"
    assert target["owner_causal_role"] == "mechanism_change"
    assert target["required_causal_role"] == "mechanism_transition"
    assert target["must_describe_new_downstream_state"] is True
    assert "섞이는 방식을 바꿉니다" in target["owner_scene_text"]
    assert payload["rules"]["do_not_paraphrase_owner_scene"] is True
    assert payload["rules"]["downstream_state_required_when_flagged"] is True


def assert_trace_duplicate_fields_agree():
    candidate = _run_332412_candidate()
    plan = engine.build_narrative_plan(candidate)
    reason = (
        "new-information contract: scene repeats semantic claim airflow_mixing "
        "reserved for scene 4"
    )
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        runner._writer_trace(
            2,
            plan,
            {"reasons": [reason], "failed_scene_indexes": [5]},
        )
    line = next(
        item for item in stream.getvalue().splitlines()
        if item.startswith("[WRITER_COMPLIANCE_TRACE] ")
    )
    trace = json.loads(line.split(" ", 1)[1])
    assert trace["duplicate_claims"] == [reason], trace
    assert trace["validation_failure_reason"] == [reason], trace
    assert trace["offending_scene_indexes"] == [5], trace


def assert_unsupported_claim_guard_and_existing_grounded_contract():
    # Existing #244 fixture proves drag/fuel/stability/payoff expansion remain rejected
    # and the supported four-claim narration remains accepted.
    grounded_base.assert_run_332398_plan_and_rejection()
    grounded_base.assert_cross_topic_generalization()


def assert_long_grounded_chain_can_expand_without_policy_change():
    claims = [
        grounded_base._claim("input_a", "mechanism_input", "첫 조건 A가 존재합니다.", ["첫 조건 A"]),
        grounded_base._claim("change_a", "mechanism_change", "대상이 조건 A를 직접 바꿉니다.", ["조건 A를 직접 바꿉니다"]),
        grounded_base._claim("step_a", "mechanism_step", "그 변화 뒤 새로운 상태 B가 형성됩니다.", ["새로운 상태 B"]),
        grounded_base._claim("effect_a", "mechanism_effect", "상태 B는 다음 전환 C로 이어집니다.", ["전환 C"]),
        grounded_base._claim("result_a", "result", "전환 C는 관찰 가능한 결과 D를 만듭니다.", ["결과 D"]),
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


def main():
    assert_plan_unchanged_and_roles_added()
    assert_run_332412_duplicate_still_fails_and_transition_passes()
    assert_live_repair_feedback_is_structured()
    assert_trace_duplicate_fields_agree()
    assert_unsupported_claim_guard_and_existing_grounded_contract()
    assert_long_grounded_chain_can_expand_without_policy_change()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("GROUNDED CAUSAL ROLE DISTINCTION REGRESSION: PASS")


if __name__ == "__main__":
    main()
