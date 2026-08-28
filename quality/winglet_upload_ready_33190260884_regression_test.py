from content.winglet_visual_beat_recovery import recover_unsupported_winglet_visual_beat
from quality.budget_guard import get_budget_status, reset_budget


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾여 있는 이유",
        "angle": "윙렛이 날개 끝 공기 흐름과 유도항력에 미치는 영향",
        "core_question": "왜 비행기 날개 끝을 위로 꺾어 놓았을까요?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "왜 비행기 날개 끝을 위로 꺾어 놓았을까요?",
            "reveal": "날개 끝 소용돌이를 줄이기 위한 설계입니다.",
            "payoff": "유도항력을 줄여 연료 효율을 높입니다.",
        },
        "fact_check_focus": ["윙렛과 유도항력의 관계"],
        "visual_proof": ["윙렛 주변의 공기 흐름"],
    }


def script():
    scenes = [
        {"text": "비행기 날개 끝이 위로 꺾여 있습니다.", "visual_goal": "비행기 날개 끝의 모습", "keyword": "aircraft wing design stage 1"},
        {"text": "그런데 왜 비행기 날개 끝을 위로 꺾어 놓았을까요?", "visual_goal": "비행기 날개 끝을 바라보는 모습", "keyword": "aircraft wing question about stage 2"},
        {"text": "원인의 첫 단서는 날개 끝이 위로 꺾인 모습은 비행기의 성능에 영향을 미칩니다.", "visual_goal": "비행기 비행 중의 모습", "keyword": "aircraft wing performance impact stage 3"},
        {"text": "이 디자인은 공기의 흐름을 개선합니다.", "visual_goal": "공기가 날개 주위를 흐르는 모습", "keyword": "aircraft wing airflow improvement stage 4"},
        {"text": "비행기 날개 끝의 꺾임은 소음 감소에도 도움을 줍니다.", "visual_goal": "비행기 소음 감소를 나타내는 그래픽", "keyword": "aircraft wing noise reduction stage 5"},
        {"text": "윙렛은 비행기의 안정성을 높입니다.", "visual_goal": "윙렛과 비행 안정성", "keyword": "aircraft wing increased stability stage 6"},
        {"text": "날개 끝의 꺾임은 연료 효율성에 긍정적인 영향을 미칩니다.", "visual_goal": "윙렛과 연료 효율", "keyword": "aircraft wing fuel efficiency stage 7"},
        {"text": "비행기 날개 끝의 디자인은 강한 소용돌이를 줄입니다.", "visual_goal": "윙렛과 날개 끝 소용돌이", "keyword": "aircraft wing vortex reduction stage 8"},
        {"text": "날개 끝이 위로 꺾여 있는 디자인은 날개 위아래의 압력 차로 인해 발생하는 강한 소용돌이를 완화시키기 위해 설계되었습니다.", "visual_goal": "윙렛 설계 목적", "keyword": "aircraft wing design purpose stage 9"},
        {"text": "이로 인해 유도항력이 줄어들어 비행기의 연료 효율성이 향상됩니다.", "visual_goal": "윙렛 효율 개선 결과", "keyword": "aircraft wing efficiency improvement stage 10"},
    ]
    return {"title": "비행기 날개 끝의 비밀", "script_engine_v2_calls": 1, "scenes": scenes}


def main():
    reset_budget()
    before = get_budget_status()
    repaired = recover_unsupported_winglet_visual_beat(script(), candidate())
    after = get_budget_status()

    first = repaired["scenes"][0]
    third = repaired["scenes"][2]

    assert first["text"] == "비행기 날개 끝이 위로 꺾여 있습니다."
    assert first["visual_goal"] == "비행기 날개 끝의 윙렛을 선명하게 보여주는 근접 모습"
    assert first["keyword"] == "airplane wing winglet closeup stage 1"
    assert "winglet" in first["keyword"]

    assert third["text"] == "위로 꺾인 날개 끝은 공기 흐름을 바꿔 비행 성능에 영향을 줍니다."
    assert third["visual_goal"] == "윙렛 주변에서 달라지는 날개 끝 공기 흐름"
    assert third["keyword"] == "airplane wing winglet airflow stage 3"
    assert "원인의 첫 단서는" not in third["text"]
    assert "모습은" not in third["text"]

    assert repaired["winglet_upload_repair"]["source_run"] == 33190260884
    assert repaired["script_engine_v2_calls"] == 1
    assert before["calls"] == after["calls"] == 0
    assert before["cost_usd"] == after["cost_usd"] == 0.0

    print("✅ Winglet upload-ready Run 33190260884 regression PASS")


if __name__ == "__main__":
    main()
