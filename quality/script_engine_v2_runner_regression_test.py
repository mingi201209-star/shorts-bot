from content.script_engine_v2 import build_narrative_plan
from content.script_engine_v2_runner import generate_script_v2


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾인 이유",
        "angle": "윙렛과 유도항력",
        "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까?",
            "reveal": "날개 끝의 소용돌이를 약하게 만들어 유도항력을 줄인다.",
            "payoff": "그래서 같은 비행에서도 연료를 덜 쓰는 데 도움이 된다.",
        },
        "fact_check_focus": ["압력 차이", "날개 끝 소용돌이", "유도항력"],
        "visual_proof": ["upturned winglet", "wingtip airflow"],
    }


MIDDLE_TEXTS = (
    "날개 끝에서도 압력 차이가 유지된다.",
    "높은 압력의 공기가 날개 끝 바깥쪽으로 움직입니다.",
    "끝을 돌아 나온 공기가 뒤쪽에서 회전하기 시작합니다.",
    "이 회전 흐름은 날개가 받는 힘의 방향을 바꿉니다.",
    "윙렛 구조는 끝부분 공기의 이동을 조절합니다.",
    "소용돌이가 약해지면 불필요한 저항도 줄어듭니다.",
    "같은 양력을 만들 때 필요한 에너지가 달라집니다.",
    "그 결과 순항 효율이 더 좋아집니다.",
)


def writer_script(item, *, missing_visual=False):
    plan = build_narrative_plan(item)
    scenes = []
    middle_index = 0
    for contract in plan["contracts"]:
        index = contract["index"]
        role = contract["role"]
        if role == "phenomenon":
            text = "writer tried to replace hook"
        elif role == "question":
            text = "writer tried to replace question"
        elif role == "causal_clue":
            text = MIDDLE_TEXTS[0]
            middle_index = 1
        elif role == "reveal":
            text = "writer tried to replace reveal"
        elif role == "payoff":
            text = "writer tried to replace payoff"
        else:
            text = MIDDLE_TEXTS[middle_index % len(MIDDLE_TEXTS)]
            middle_index += 1
        scenes.append({
            "text": text,
            "visual_goal": f"show aviation mechanism stage {index} clearly",
            "keyword": f"airplane wing airflow stage {index}",
        })
    if missing_visual:
        scenes[3]["visual_goal"] = ""
    return {"title": "윙렛의 이유", "scenes": scenes}


def production_shape_writer(item):
    """Distill Run 32640117196: aliases + Korean keywords on locked scenes."""
    plan = build_narrative_plan(item)
    scenes = []
    for contract in plan["contracts"]:
        index = contract["index"]
        role = contract["role"]
        text = MIDDLE_TEXTS[(index - 1) % len(MIDDLE_TEXTS)]
        scene = {
            "narration": text,
            "visual_description": f"show winglet airflow mechanism stage {index}",
            "search_query": f"winglet airflow stage {index}",
        }
        if role in ("phenomenon", "question", "reveal", "payoff"):
            scene["search_query"] = "윙렛 공기 흐름"
        scenes.append(scene)
    return {"result": {"title": "윙렛의 이유", "scenes": scenes}}


def latest_production_shape_writer(writer_payload):
    """Distill Run 32641375844 after candidate-opening normalization."""
    scenes = []
    for contract in writer_payload["scene_contracts"]:
        index = contract["index"]
        scenes.append({
            "narration": MIDDLE_TEXTS[(index - 1) % len(MIDDLE_TEXTS)],
            "visual_description": f"show winglet airflow mechanism stage {index}",
            "search_query": "윙렛 공기 흐름",
        })
    return {"result": {"title": "윙렛의 이유", "scenes": scenes}}


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
    assert script["scenes"][1]["text"].endswith("있을까요?")
    assert script["scenes"][-2]["text"].endswith("줄입니다.")
    assert script["scenes"][-1]["text"].endswith("됩니다.")
    assert script["scenes"][2]["text"] == "날개 끝에서도 압력 차이가 유지됩니다."

    production_calls = []

    def production_call(payload, *, mode):
        production_calls.append(mode)
        if mode == "writer":
            return production_shape_writer(item)
        repairs = []
        for target in payload["targets"]:
            repairs.append({
                "scene_index": target["scene_index"],
                "keyword": f"winglet airflow detail {target['scene_index']}",
            })
        return {"repairs": repairs}

    production_script = generate_script_v2(item, call_fn=production_call)
    assert production_script["script_engine_v2_calls"] <= 3
    assert production_script["scenes"][0]["text"] == item["micro_narrative"]["hook"]
    assert production_script["scenes"][1]["text"].endswith("있을까요?")
    assert production_script["scenes"][-2]["text"].endswith("줄입니다.")
    assert production_script["scenes"][-1]["text"].endswith("됩니다.")
    assert all(any(ch.isascii() and ch.isalpha() for ch in scene["keyword"]) for scene in production_script["scenes"])

    latest_item = candidate()
    latest_item["topic"] = "비행기 날개 끝의 윙렛은 왜 위로 꺾여 있을까"
    latest_item["micro_narrative"]["hook"] = (
        "비행기 날개 끝의 윙렛이 위로 꺾여 있는 모습은 흔히 볼 수 있지만, 그 이유는 무엇일까?"
    )
    latest_item["micro_narrative"]["reveal"] = (
        "윙렛은 날개 끝에서 발생하는 압력 차로 인한 강한 소용돌이를 약화시키기 위해 "
        "위로 꺾여 있으며, 이로 인해 유도항력이 줄어든다."
    )
    latest_item["micro_narrative"]["payoff"] = (
        "결과적으로, 이 설계는 유도항력을 줄여 비행기의 연료 효율성을 높인다."
    )
    latest_item["visual_proof"] = ["윙렛", "날개 끝 공기 흐름"]
    latest_calls = []

    def latest_call(payload, *, mode):
        latest_calls.append(mode)
        if mode == "writer":
            return latest_production_shape_writer(payload)
        return {
            "repairs": [
                {"scene_index": target["scene_index"], "keyword": "윙렛 공기 흐름"}
                for target in payload["targets"]
            ]
        }

    latest_script = generate_script_v2(latest_item, call_fn=latest_call)
    assert latest_script["script_engine_v2_calls"] <= 3
    assert latest_script["scenes"][0]["text"] == "비행기 날개 끝의 윙렛이 위로 꺾여 있는 모습은 흔히 볼 수 있습니다."
    assert "무엇입니다" not in latest_script["scenes"][0]["text"]
    assert latest_script["scenes"][-2]["text"].endswith("유도항력이 줄어듭니다.")
    assert latest_script["scenes"][-1]["text"].endswith("연료 효율성을 높입니다.")
    assert all(any(ch.isascii() and ch.isalpha() for ch in scene["keyword"]) for scene in latest_script["scenes"])
    assert len({scene["keyword"] for scene in latest_script["scenes"]}) >= max(6, len(latest_script["scenes"]) // 2)

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

    print("PASS: Script Engine V2 bounded writer orchestration + production failure fixture")


if __name__ == "__main__":
    main()
