from content.script_engine_v2 import build_narrative_plan
from content.script_engine_v2_runner import generate_script_v2


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾인 이유",
        "angle": "윙렛과 유도항력",
        "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
            "reveal": "날개 끝 소용돌이를 약하게 만들어 유도항력을 줄입니다.",
            "payoff": "그래서 연료를 덜 쓰는 데 도움이 됩니다.",
        },
        "fact_check_focus": ["압력 차이", "날개 끝 소용돌이", "유도항력"],
        "visual_proof": ["윙렛", "날개 끝 공기 흐름"],
    }


def writer_script(item, *, missing_visual=False):
    plan = build_narrative_plan(item)
    scenes = []
    for contract in plan["contracts"]:
        index = contract["index"]
        role = contract["role"]
        if role == "phenomenon":
            text = "writer tried to replace hook"
        elif role == "question":
            text = "writer tried to replace question"
        elif role == "causal_clue":
            text = "날개 끝에서 서로 다른 흐름이 만나게 된다."
        elif role == "reveal":
            text = "writer tried to replace reveal"
        elif role == "payoff":
            text = "writer tried to replace payoff"
        else:
            text = "공기 흐름의 변화가 다음 힘의 변화로 이어집니다."
        scenes.append({
            "text": text,
            "visual_goal": "show the wing and airflow clearly",
            "keyword": f"airplane wing airflow {index}",
        })
    if missing_visual:
        scenes[3]["visual_goal"] = ""
    return {"title": "윙렛의 이유", "scenes": scenes}


def main():
    item = candidate()
    calls = []

    def fake_call(payload, *, mode):
        calls.append(mode)
        if mode == "writer":
            return writer_script(item, missing_visual=True)
        assert mode == "local_repair"
        targets = payload["targets"]
        assert [entry["scene_index"] for entry in targets] == [4]
        return {
            "repairs": [{
                "scene_index": 4,
                "visual_goal": "show wingtip vortex shrinking behind the wing",
            }]
        }

    script = generate_script_v2(item, call_fn=fake_call)
    assert calls == ["writer", "local_repair"]
    assert script["script_engine_v2_calls"] == 2
    assert script["scenes"][0]["text"] == item["micro_narrative"]["hook"]
    assert script["scenes"][1]["text"].startswith("그런데")
    assert script["scenes"][-2]["text"] == item["micro_narrative"]["reveal"]
    assert script["scenes"][-1]["text"] == item["micro_narrative"]["payoff"]
    assert script["scenes"][2]["text"].endswith("됩니다.")

    failing_calls = []

    def never_fix(payload, *, mode):
        failing_calls.append(mode)
        if mode == "writer":
            return writer_script(item, missing_visual=True)
        return {"repairs": []}

    try:
        generate_script_v2(item, call_fn=never_fix)
    except RuntimeError as exc:
        assert "within 3 calls" in str(exc)
    else:
        raise AssertionError("V2 must fail closed after bounded local repairs")
    assert failing_calls == ["writer", "local_repair", "local_repair"]

    print("PASS: Script Engine V2 bounded writer orchestration")


if __name__ == "__main__":
    main()
