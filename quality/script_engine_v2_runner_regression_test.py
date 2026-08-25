import subprocess
import sys

subprocess.run([sys.executable, "ci_script_v2_visual_goal_hotfix.py"], check=True)

from content.script_engine_v2 import build_narrative_plan, writer_payload
from content.script_engine_v2_runner import generate_script_v2, _writer_response_format


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
        # Run 32646866316: more than one scene survived writer/local-repair
        # with a missing or too-short visual_goal.
        scenes[3]["visual_goal"] = ""
        scenes[6]["visual_goal"] = "shot"
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

    plan = build_narrative_plan(item)
    writer_format = _writer_response_format(writer_payload(item, plan), mode="writer")
    scene_schema = writer_format["json_schema"]["schema"]["properties"]["scenes"]
    assert scene_schema["minItems"] == plan["target_scene_count"]
    assert scene_schema["maxItems"] == plan["target_scene_count"]
    assert _writer_response_format({}, mode="local_repair") == {"type": "json_object"}

    door_item = candidate()
    door_item["topic"] = "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유"
    door_item["micro_narrative"]["hook"] = (
        "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유는 무엇일까요?"
    )
    door_writer = lambda payload, *, mode: writer_script(door_item)
    door_script = generate_script_v2(door_item, call_fn=door_writer)
    assert door_script["scenes"][0]["text"] == (
        "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않습니다."
    )
    assert "무엇입니다" not in door_script["scenes"][0]["text"]

    calls = []

    def fake_call(payload, *, mode):
        calls.append(mode)
        if mode == "writer":
            return writer_script(item, missing_visual=True)
        raise AssertionError("missing/short visual_goal must not spend a local-repair API call")

    script = generate_script_v2(item, call_fn=fake_call)
    assert calls == ["writer"]
    assert script["script_engine_v2_calls"] == 1
    assert script["scenes"][0]["text"] == item["micro_narrative"]["hook"]
    assert script["scenes"][1]["text"].startswith("그런데")
    assert script["scenes"][1]["text"].endswith("있을까요?")
    assert script["scenes"][-2]["text"].endswith("줄입니다.")
    assert script["scenes"][-1]["text"].endswith("됩니다.")
    assert script["scenes"][2]["text"] == "날개 끝에서도 압력 차이가 유지됩니다."
    assert len(script["scenes"][3]["visual_goal"]) >= 8
    assert len(script["scenes"][6]["visual_goal"]) >= 8
    assert "airplane wing airflow stage 4" in script["scenes"][3]["visual_goal"]
    assert "airplane wing airflow stage 7" in script["scenes"][6]["visual_goal"]
    # Valid writer metadata must remain byte-for-byte unchanged.
    assert script["scenes"][2]["visual_goal"] == "show aviation mechanism stage 3 clearly"

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

    # Run 32785394904: the approved reveal used ~시킨다 and the writer leaked
    # the same reveal into the preceding unlocked scene. Repair both defects
    # deterministically without adding calls or changing the locked fact.
    counterexample = candidate()
    counterexample["micro_narrative"]["reveal"] = (
        "날개 끝이 위로 꺾이면 날개 위아래 압력 차가 끝단에서 강한 소용돌이를 만들고, "
        "이 형상이 그 흐름을 약화시킨다."
    )
    counterexample_calls = []

    def counterexample_call(payload, *, mode):
        counterexample_calls.append(mode)
        if mode != "writer":
            raise AssertionError("locked-ending/adjacent-dedupe fixture must not spend repair calls")
        generated = writer_script(counterexample)
        generated["scenes"][-3]["text"] = counterexample["micro_narrative"]["reveal"]
        return generated

    recovered = generate_script_v2(counterexample, call_fn=counterexample_call)
    assert counterexample_calls == ["writer"]
    assert recovered["scenes"][-2]["text"].endswith("약화시킵니다.")
    assert recovered["scenes"][-3]["text"] != recovered["scenes"][-2]["text"]

    # Run 32790524280: the locked payoff survived all bounded calls with the
    # non-formal ~위해서다 ending. Normalize style without changing its fact.
    payoff_counterexample = candidate()
    payoff_counterexample["micro_narrative"]["payoff"] = (
        "날개 끝이 위로 꺾여 있는 것은 날개 위아래의 압력 차가 날개 끝에서 강한 "
        "소용돌이를 만들어내고, 꺾인 형상이 그 소용돌이를 약화시켜 유도항력을 "
        "줄이기 위해서다."
    )
    payoff_calls = []

    def payoff_call(payload, *, mode):
        payoff_calls.append(mode)
        if mode != "writer":
            raise AssertionError("locked payoff fixture must not spend repair calls")
        return writer_script(payoff_counterexample)

    payoff_recovered = generate_script_v2(
        payoff_counterexample,
        call_fn=payoff_call,
    )
    assert payoff_calls == ["writer"]
    assert payoff_recovered["scenes"][-1]["text"].endswith("위해서입니다.")

    # Run 32844712758: the writer exhausted bounded repair with an unlocked
    # explanatory scene ending in ~해준다. Normalize this common plain ending
    # deterministically without spending another model call.
    haejunda_calls = []

    def haejunda_writer(payload, *, mode):
        haejunda_calls.append(mode)
        if mode != "writer":
            raise AssertionError("formal-ending fixture must not spend repair calls")
        generated = writer_script(item)
        generated["scenes"][2]["text"] = (
            "둥근 형태는 압력 분포를 고르게 만들어 더 잘 견딜 수 있게 해준다."
        )
        return generated

    haejunda_recovered = generate_script_v2(item, call_fn=haejunda_writer)
    assert haejunda_calls == ["writer"]
    assert haejunda_recovered["scenes"][2]["text"].endswith("해줍니다.")

    # Run 32846689908: a fixed landing-gear topic drifted into generic
    # efficiency/safety queries, so final visual semantic QA rejected Scenes 2-3.
    # Keep the concrete aircraft landing-gear anchor in every generated query.
    landing_gear_item = candidate()
    landing_gear_item["topic"] = "비행기 착륙장치는 접히게 만든다"
    landing_gear_item["micro_narrative"]["hook"] = (
        "비행기 착륙장치는 비행 중 동체 안으로 접힙니다."
    )
    landing_gear_calls = []

    def landing_gear_writer(payload, *, mode):
        landing_gear_calls.append(mode)
        if mode != "writer":
            raise AssertionError("landing-gear query lock must not spend repair calls")
        return writer_script(landing_gear_item)

    landing_gear_script = generate_script_v2(
        landing_gear_item,
        call_fn=landing_gear_writer,
    )
    assert landing_gear_calls == ["writer"]
    assert all(
        all(anchor in scene["keyword"].lower() for anchor in ("aircraft", "landing", "gear"))
        for scene in landing_gear_script["scenes"]
    )
    assert all("wing" not in scene["keyword"].lower() for scene in landing_gear_script["scenes"])

    failing_calls = []

    def structurally_invalid(payload, *, mode):
        failing_calls.append(mode)
        if mode == "writer":
            broken = writer_script(item)
            broken["scenes"] = broken["scenes"][:-1]
            return broken
        return {"repairs": []}

    try:
        generate_script_v2(item, call_fn=structurally_invalid)
    except (RuntimeError, ValueError) as exc:
        message = str(exc)
        assert "within 3 calls" in message or "scene count mismatch" in message
    else:
        raise AssertionError("V2 must still fail closed on non-local structural defects")
    assert failing_calls == ["writer"]

    print("PASS: Script Engine V2 bounded writer orchestration + Run 32646866316 visual_goal fixture")


if __name__ == "__main__":
    main()
