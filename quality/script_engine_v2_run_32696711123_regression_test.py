import subprocess
import sys

subprocess.run([sys.executable, "ci_script_v2_visual_goal_hotfix.py"], check=True)

from content.script_engine_v2 import build_narrative_plan
from content.script_engine_v2_runner import generate_script_v2


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾여 있는 이유",
        "angle": "윙렛과 유도항력",
        "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까?",
            "reveal": "윙렛은 날개 끝 소용돌이를 약하게 만들어 유도항력을 줄인다.",
            "payoff": "그래서 연료 효율을 높이는 데 도움이 된다.",
        },
        "fact_check_focus": ["압력 차이", "날개 끝 소용돌이", "유도항력"],
        "visual_proof": ["upturned winglet", "wingtip airflow"],
    }


def writer_response(item):
    plan = build_narrative_plan(item)
    scenes = []
    for contract in plan["contracts"]:
        idx = contract["index"]
        role = contract["role"]
        if role in ("phenomenon", "question", "reveal", "payoff"):
            text = "locked text placeholder"
        elif role == "causal_clue":
            text = ""  # Run 32696711123: scene 3 text missing
        elif role.startswith("mechanism_") and idx == 4:
            text = "이 변화는 날개 끝 공기의 흐름을 바꾼다."
        else:
            text = "날개 끝의 공기 흐름은 압력 차이와 연결됩니다."
        scenes.append({
            "text": text,
            "visual_goal": f"show winglet airflow mechanism stage {idx}",
            "keyword": f"winglet airflow stage {idx}",
        })
    return {"title": "윙렛의 이유", "scenes": scenes}


def main():
    item = candidate()
    calls = []

    def fake_call(payload, *, mode):
        calls.append(mode)
        if mode == "writer":
            return writer_response(item)
        # Even if local repair is requested, simulate the production model failing
        # to restore narration. Deterministic recovery must still converge safely.
        return {"repairs": []}

    script = generate_script_v2(item, call_fn=fake_call)
    assert script["script_engine_v2_calls"] <= 3
    assert script["scenes"][2]["text"]
    assert script["scenes"][2]["text"].endswith(("니다.", "입니다."))
    assert "바꾼다" not in script["scenes"][3]["text"]
    assert script["scenes"][3]["text"].endswith("바꿉니다.")
    assert script["scenes"][0]["text"] == "비행기 날개 끝이 위로 꺾여 있습니다."
    assert script["scenes"][-2]["text"].endswith("줄입니다.")
    assert script["scenes"][-1]["text"].endswith("됩니다.")
    print("PASS: Run 32696711123 missing-text + formal-ending terminal recovery")


if __name__ == "__main__":
    main()
