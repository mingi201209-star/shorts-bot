"""Regression fixtures distilled from repeated production Script failures."""
from content.script_engine_v2 import build_narrative_plan, local_repair_payload, repair_failed_scenes

CANDIDATE = {
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


def script_with(plan, scene3, scene4):
    count = plan["target_scene_count"]
    texts = [CANDIDATE["micro_narrative"]["hook"], "그런데 왜 비행기 날개 끝은 위로 꺾여 있을까요?", scene3, scene4]
    while len(texts) < count - 2:
        texts.append("공기 흐름과 힘의 변화가 다음 단계로 이어집니다.")
    texts.extend([CANDIDATE["micro_narrative"]["reveal"], CANDIDATE["micro_narrative"]["payoff"]])
    return {"scenes": [{"text": text} for text in texts]}


def main():
    plan = build_narrative_plan(CANDIDATE)
    reveal_index = plan["target_scene_count"] - 1

    broken = script_with(plan, "날개 끝에서 서로 다른 공기가 만나게 된다.", "이 구조가 소용돌이를 줄여준다.")
    repaired = repair_failed_scenes(broken, plan, [3, 4])
    assert repaired["scenes"][2]["text"].endswith("됩니다.")
    assert "공기" in repaired["scenes"][2]["text"]
    assert repaired["scenes"][3]["text"].endswith("줄여줍니다.")

    missing_clue = script_with(plan, "두 부분이 서로 만나게 된다.", "이 구조가 소용돌이를 줄여준다.")
    repaired_clue = repair_failed_scenes(missing_clue, plan, [3])
    assert repaired_clue["scenes"][2]["text"].startswith("원인의 첫 단서는 ")
    assert repaired_clue["scenes"][2]["text"].endswith("됩니다.")

    tampered = script_with(plan, "압력 차이가 생깁니다.", "소용돌이가 감소시킨다.")
    tampered["scenes"][0]["text"] = "왜 꺾였을까요?"
    tampered["scenes"][reveal_index - 1]["text"] = "정답을 바꾼다."
    repaired2 = repair_failed_scenes(tampered, plan, [1, 4, reveal_index])
    assert repaired2["scenes"][0]["text"] == CANDIDATE["micro_narrative"]["hook"]
    assert repaired2["scenes"][3]["text"].endswith("감소시킵니다.")
    assert repaired2["scenes"][reveal_index - 1]["text"] == CANDIDATE["micro_narrative"]["reveal"]

    payload = local_repair_payload(repaired2, plan, [1, 3, 4, reveal_index], ["scene 3 lacks causal clue", "scene 4 speech style"])
    targets = payload["targets"]
    assert [item["scene_index"] for item in targets] == [1, 3, 4, reveal_index]
    assert targets[0]["text_locked"] is True
    assert targets[0]["locked_text"] == CANDIDATE["micro_narrative"]["hook"]
    assert targets[1]["text_locked"] is False
    assert targets[-1]["text_locked"] is True
    assert targets[-1]["locked_text"] == CANDIDATE["micro_narrative"]["reveal"]
    assert payload["rules"]["locked_scene_text_is_immutable"] is True
    assert payload["rules"]["metadata_on_locked_scenes_may_be_repaired"] is True
    assert payload["rules"]["max_local_repair_calls"] == 2
    assert payload["rules"]["do_not_rewrite_other_scenes"] is True
    print("PASS: Script Engine V2 production failure fixtures")


if __name__ == "__main__":
    main()
