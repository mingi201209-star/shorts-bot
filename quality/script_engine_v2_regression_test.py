from content.script_engine_v2 import (
    MAX_SCRIPT_API_CALLS,
    apply_locked_scenes,
    build_narrative_plan,
    writer_payload,
)
from content.script_engine_v2_runner import (
    _deterministic_keyword,
    _formalize_common_ending,
)


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾인 이유",
        "angle": "윙렛이 유도항력을 줄이는 원리",
        "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
            "reveal": "날개 끝의 소용돌이를 약하게 만들어 유도항력을 줄입니다.",
            "payoff": "그래서 같은 비행에서도 연료를 덜 쓰는 데 도움이 됩니다.",
        },
        "fact_check_focus": ["wingtip vortex", "induced drag", "pressure difference"],
        "visual_proof": ["upturned winglet", "wingtip airflow"],
    }


def main():
    item = candidate()
    plan = build_narrative_plan(item)
    contracts = plan["contracts"]
    count = plan["target_scene_count"]

    assert _formalize_common_ending(
        "둥근 모서리는 압력이 창문 모서리에 고르게 분산되도록 돕는다."
    ).endswith("돕습니다.")
    assert _formalize_common_ending(
        "응력이 분산되어 특정 지점에 집중되지 않는다."
    ).endswith("집중되지 않습니다.")
    assert plan["api_call_budget"] == 3 == MAX_SCRIPT_API_CALLS
    assert 7 <= count <= 13
    assert len(contracts) == count
    assert [c["role"] for c in contracts[:3]] == [
        "phenomenon", "question", "causal_clue"
    ]
    assert contracts[-2]["role"] == "reveal"
    assert contracts[-1]["role"] == "payoff"
    assert contracts[0]["locked_text"].endswith("있습니다.")
    assert contracts[1]["locked_text"].startswith("그런데")
    assert contracts[-2]["locked"] is True
    assert contracts[-1]["locked"] is True

    payload = writer_payload(item, plan)
    assert payload["rules"]["do_not_change_locked_text"] is True
    assert payload["rules"]["max_total_api_calls"] == 3
    assert payload["target_scene_count"] == count

    generated = {
        "scenes": [
            {"text": f"writer scene {i}"}
            for i in range(1, count + 1)
        ]
    }
    locked = apply_locked_scenes(generated, plan)
    assert locked["scenes"][0]["text"] == item["micro_narrative"]["hook"]
    assert locked["scenes"][1]["text"].startswith("그런데")
    assert locked["scenes"][-2]["text"] == item["micro_narrative"]["reveal"]
    assert locked["scenes"][-1]["text"] == item["micro_narrative"]["payoff"]
    assert locked["scenes"][2]["text"] == "writer scene 3"

    production_counterexample = candidate()
    production_counterexample["micro_narrative"]["hook"] = (
        "왜 비행기 날개 위 작은 판은 착륙할 때 올라올까요?"
    )
    repaired = build_narrative_plan(production_counterexample)
    assert repaired["contracts"][0]["locked_text"] == (
        "비행기 날개 위 작은 판은 착륙할 때 올라옵니다."
    )

    what_question = candidate()
    what_question["topic"] = "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유"
    what_question["micro_narrative"]["hook"] = (
        "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유는 무엇일까?"
    )
    repaired_what = build_narrative_plan(what_question)
    assert repaired_what["contracts"][0]["locked_text"] == (
        "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않습니다."
    )

    fixed_topic_question = candidate()
    fixed_topic_question["topic"] = (
        "제트 엔진 뒤 톱니 모양 셰브론은 뜨거운 배기와 찬 공기를 "
        "섞어 소음을 줄입니다"
    )
    fixed_topic_question["micro_narrative"]["hook"] = (
        "왜 제트 엔진 뒤 톱니 모양 셰브론이 소음을 줄일까?"
    )
    repaired_fixed_topic = build_narrative_plan(fixed_topic_question)
    assert repaired_fixed_topic["contracts"][0]["locked_text"] == (
        fixed_topic_question["topic"] + "."
    )

    geolkka_question = candidate()
    geolkka_question["core_question"] = (
        "왜 제트 엔진 뒤에 톱니 모양 셰브론이 있는 걸까?"
    )
    geolkka_question["micro_narrative"]["core_question"] = (
        geolkka_question["core_question"]
    )
    repaired_geolkka = build_narrative_plan(geolkka_question)
    assert repaired_geolkka["contracts"][1]["locked_text"] == (
        "그런데 왜 제트 엔진 뒤에 톱니 모양 셰브론이 있는 걸까요?"
    )

    unsupported = candidate()
    unsupported["micro_narrative"]["hook"] = "왜 날개가 움직이나요?"
    try:
        build_narrative_plan(unsupported)
    except ValueError as exc:
        assert "observable statement" in str(exc)
    else:
        raise AssertionError("unsupported question Hook must still fail closed")

    wheel_plan = {
        "topic": "비행기 바퀴는 착륙 전에 미리 돌지 않는다",
        "angle": "착륙 바퀴 작동 원리",
    }
    for generic_keyword in ("fixed wheels", "design safety", "mechanism explanation"):
        anchored = _deterministic_keyword(
            {"keyword": generic_keyword, "visual_goal": generic_keyword},
            {"required_concepts": []},
            wheel_plan,
            4,
        )
        assert anchored.startswith("aircraft landing gear wheel ")
        assert 4 <= len(anchored.split()) <= 7

    chevron_plan = {
        "topic": (
            "제트 엔진 뒤 톱니 모양 셰브론은 뜨거운 배기와 찬 공기를 "
            "섞어 소음을 줄입니다"
        ),
        "angle": "제트 엔진 셰브론 작동 원리",
    }
    for cross_domain_keyword in (
        "chevron design",
        "mixing air",
        "noise reduction",
        "air contact",
        "environmental impact",
    ):
        anchored = _deterministic_keyword(
            {
                "keyword": cross_domain_keyword,
                "visual_goal": cross_domain_keyword,
            },
            {"required_concepts": []},
            chevron_plan,
            5,
        )
        assert anchored.startswith("aircraft jet engine chevron ")
        assert 4 <= len(anchored.split()) <= 7

    print("PASS: Script Engine V2 adaptive deterministic narrative plan")


if __name__ == "__main__":
    main()
