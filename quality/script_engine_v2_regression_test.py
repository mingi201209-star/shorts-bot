from content.script_engine_v2 import (
    MAX_SCRIPT_API_CALLS,
    apply_locked_scenes,
    build_narrative_plan,
    writer_payload,
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

    bad = candidate()
    bad["micro_narrative"]["hook"] = "왜 날개 끝이 꺾여 있을까요?"
    try:
        build_narrative_plan(bad)
    except ValueError as exc:
        assert "observable statement" in str(exc)
    else:
        raise AssertionError("question Hook must be rejected before writer call")

    print("PASS: Script Engine V2 adaptive deterministic narrative plan")


if __name__ == "__main__":
    main()
