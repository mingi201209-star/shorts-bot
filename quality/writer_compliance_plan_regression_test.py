"""Run 33239180275 counterexample: plan-first Writer compliance."""
import importlib
import runpy


# Apply the production installer when this focused regression is run standalone.
runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")

import content.script_engine_v2 as engine
import content.script_engine_v2_runner as runner

engine = importlib.reload(engine)
runner = importlib.reload(runner)


def short_candidate():
    return {
        "topic": "엔진 뒤 가장자리에 반복된 톱니가 있는 이유",
        "angle": "고속 흐름과 주변 흐름이 만나는 경계",
        "core_question": "왜 엔진 뒤 가장자리는 톱니처럼 보일까?",
        "fact_check_focus": [
            "고속 배기 흐름과 주변 공기의 속도 차이가 큽니다.",
            "톱니 가장자리가 두 흐름이 섞이는 방식을 바꿉니다.",
            "이 설계의 대표적인 결과는 소음 감소입니다.",
        ],
        "visual_proof": [
            "엔진 뒤 가장자리의 반복된 톱니 형태",
            "배기 흐름과 주변 공기가 만나는 경계",
        ],
        "micro_narrative": {
            "hook": "엔진 뒤 가장자리는 톱니처럼 보입니다.",
            "core_question": "왜 엔진 뒤 가장자리는 톱니처럼 보일까?",
            "reveal": "톱니 가장자리는 배기와 주변 공기의 혼합을 바꿔 소음을 줄입니다.",
            "payoff": "그래서 엔진 주변 소음을 낮추는 데 쓰입니다.",
        },
    }


def long_candidate():
    return {
        "topic": "오랜 기간 여러 단계로 바뀐 복합 설계의 역사와 원리",
        "angle": "변화 단계와 서로 다른 물리적 제약",
        "core_question": "왜 이 설계는 여러 단계로 바뀌었을까?",
        "fact_check_focus": [
            "초기 구조에는 첫 번째 제약이 있었습니다.",
            "두 번째 단계에서는 압력 차를 다르게 처리했습니다.",
            "세 번째 단계에서는 하중 전달 경로가 바뀌었습니다.",
            "네 번째 단계에서는 재료 배치가 달라졌습니다.",
            "다섯 번째 단계에서는 작동 순서가 달라졌습니다.",
        ],
        "visual_proof": [
            "초기 구조의 형상 차이",
            "두 번째 구조의 연결부",
            "세 번째 구조의 하중 경로",
            "네 번째 구조의 재료 배치",
            "다섯 번째 구조의 작동 단계",
        ],
        "specific_observation": "과거 구조와 현재 구조의 형상이 다릅니다.",
        "constraint": "각 시대에 해결해야 할 제약이 달랐습니다.",
        "tradeoff": "한 제약을 줄이면 다른 부담이 생겼습니다.",
        "micro_narrative": {
            "hook": "과거와 현재의 구조는 모양이 다릅니다.",
            "core_question": "왜 이 설계는 여러 단계로 바뀌었을까?",
            "reveal": "각 변화는 서로 다른 제약을 해결하기 위한 설계 변경이었습니다.",
            "payoff": "그래서 현재 형상에는 여러 시대의 선택이 함께 남아 있습니다.",
        },
    }


def assert_short_plan_contract():
    candidate = short_candidate()
    plan = engine.build_narrative_plan(candidate)
    assert 5 <= plan["target_scene_count"] <= 7, plan
    roles = [item["role"] for item in plan["contracts"]]
    assert roles[:3] == ["phenomenon", "question", "causal_clue"], roles
    assert len(roles) == len(plan["contracts"]) == plan["target_scene_count"]

    owner = plan["reserved_claim_owners"].get("noise_reduction")
    assert owner is not None, plan["reserved_claim_owners"]
    for contract in plan["contracts"]:
        index = int(contract["index"])
        if index == owner:
            continue
        assert "noise_reduction" in contract["forbidden_claims"], contract
        assert "noise_reduction" not in contract["allowed_claims"], contract

    payload = engine.writer_payload(candidate, plan)
    assert payload["target_scene_count"] == len(payload["scene_contracts"])
    assert payload["rules"]["use_each_reserved_claim_only_in_owner_scene"] is True
    schema = runner._writer_response_format(payload, mode="writer")
    scenes_schema = schema["json_schema"]["schema"]["properties"]["scenes"]
    assert scenes_schema["minItems"] == scenes_schema["maxItems"] == len(plan["contracts"])
    return plan


def assert_repair_feedback(plan):
    scenes = []
    for _contract in plan["contracts"]:
        scenes.append({
            "text": "새 정보를 설명합니다.",
            "visual_goal": "구조의 실제 변화를 가까이 보여줍니다.",
            "keyword": "aircraft engine detail",
        })
    owner = int(plan["reserved_claim_owners"]["noise_reduction"])
    offending = 4 if owner != 4 else 3
    reason = f"new-information contract: scene repeats semantic claim noise_reduction reserved for scene {owner}"
    payload = engine.local_repair_payload(
        {"scenes": scenes},
        plan,
        [offending],
        [reason],
    )
    target = payload["targets"][0]
    assert target["scene_index"] == offending
    assert target["duplicate_claim"] == "noise_reduction"
    assert target["owner_scene_index"] == owner
    assert target["required_role"] == plan["contracts"][offending - 1]["role"]
    assert target["must_replace_with"] == plan["contracts"][offending - 1]["semantic_purpose"]
    assert "noise_reduction" in target["forbidden_claims"]


def assert_payoff_owner_unique():
    candidate = short_candidate()
    candidate["micro_narrative"]["payoff"] = "그래서 승객 주변 환경의 소음 부담을 줄여 더 편안하게 느끼게 합니다."
    plan = engine.build_narrative_plan(candidate)
    owners = plan["reserved_claim_owners"]
    if "experience_payoff" in owners:
        payoff_owner = owners["experience_payoff"]
        assert payoff_owner == plan["target_scene_count"]
        for contract in plan["contracts"][:-1]:
            assert "experience_payoff" in contract["forbidden_claims"]


def assert_distinct_mechanisms_and_long_topics():
    plan = engine.build_narrative_plan(long_candidate())
    assert plan["target_scene_count"] >= 8, plan["target_scene_count"]
    mechanisms = [item for item in plan["contracts"] if item["role"].startswith("mechanism_")]
    assert len(mechanisms) >= 2
    purposes = [item["semantic_purpose"] for item in mechanisms]
    assert len(set(purposes)) == len(purposes), purposes


def main():
    short_plan = assert_short_plan_contract()
    assert_repair_feedback(short_plan)
    assert_payoff_owner_unique()
    assert_distinct_mechanisms_and_long_topics()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2

    # Keep the Run 33239832517 grounded-claim counterexample on the existing
    # Script Engine V2 regression surface; no workflow/bridge is added.
    runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")
    from quality.script_engine_v2_grounded_claim_plan_regression_test import main as grounded_claim_main
    grounded_claim_main()

    print("WRITER COMPLIANCE PLAN-FIRST REGRESSION: PASS")


if __name__ == "__main__":
    main()
