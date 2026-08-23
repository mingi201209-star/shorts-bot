from copy import deepcopy


def _apply(payload, candidate):
    if not isinstance(payload, dict) or not isinstance(candidate, dict):
        return payload
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 4:
        return payload
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        return payload
    reveal = str(micro.get("reveal", "")).strip()
    payoff = str(micro.get("payoff", "")).strip()
    if isinstance(scenes[-2], dict) and reveal:
        scenes[-2]["text"] = reveal
    if isinstance(scenes[-1], dict) and payoff:
        scenes[-1]["text"] = payoff
    return payload


def main():
    candidate = {
        "micro_narrative": {
            "reveal": "압력 차이는 작은 통로를 통해 천천히 균형을 찾습니다.",
            "payoff": "그래서 구조 전체에 갑작스러운 압력 집중이 생기는 것을 줄입니다.",
        }
    }
    payload = {
        "title": "fixture",
        "scenes": [
            {"text": "hook", "visual_goal": "v1", "keyword": "airplane window detail"},
            {"text": "question", "visual_goal": "v2", "keyword": "airplane cabin window"},
            {"text": "body", "visual_goal": "v3", "keyword": "aircraft cabin pressure"},
            {"text": "wrong reveal", "visual_goal": "keep reveal visual", "keyword": "airplane window closeup"},
            {"text": "generic outro", "visual_goal": "keep payoff visual", "keyword": "aircraft window cabin"},
        ],
    }
    before = deepcopy(payload)
    result = _apply(payload, candidate)

    assert result["scenes"][-2]["text"] == candidate["micro_narrative"]["reveal"]
    assert result["scenes"][-1]["text"] == candidate["micro_narrative"]["payoff"]
    assert result["scenes"][-2]["visual_goal"] == before["scenes"][-2]["visual_goal"]
    assert result["scenes"][-2]["keyword"] == before["scenes"][-2]["keyword"]
    assert result["scenes"][-1]["visual_goal"] == before["scenes"][-1]["visual_goal"]
    assert result["scenes"][-1]["keyword"] == before["scenes"][-1]["keyword"]
    assert result["scenes"][0]["text"] == "hook"
    assert result["scenes"][1]["text"] == "question"
    print("✅ script closing lock regression passed")


if __name__ == "__main__":
    main()
