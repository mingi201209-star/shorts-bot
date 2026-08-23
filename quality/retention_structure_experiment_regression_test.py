from content.retention_structure import (
    annotate_script,
    build_retention_plan,
    classify_runtime_bucket,
    validate_density,
    validate_first5_progression,
)


def candidate_simple():
    return {
        "topic": "비행기 창문에 작은 구멍이 있는 이유",
        "angle": "승객이 실제로 보는 작은 구조가 압력 균형에 쓰인다",
        "core_question": "왜 창문 아래쪽에 작은 구멍이 있을까?",
        "micro_narrative": {
            "hook": "비행기 창문에는 작은 구멍이 있습니다.",
            "core_question": "그런데 왜 일부러 뚫어둘까요?",
            "reveal": "구멍이 창문 층 사이의 압력을 조절합니다.",
            "payoff": "그래서 바깥쪽 창이 압력을 주로 버티게 됩니다.",
        },
        "fact_check_focus": ["창문 층 사이 압력 조절"],
        "visual_proof": ["창문 작은 구멍 근접 화면"],
    }


def candidate_medium():
    c = candidate_simple()
    c["topic"] = "비행기 날개가 흔들려도 버티는 구조"
    c["angle"] = "날개 구조와 힘 분산 원리"
    c["core_question"] = "날개는 왜 흔들려도 부러지지 않을까?"
    c["fact_check_focus"] = ["날개 구조", "힘 분산", "하중 변화"]
    c["visual_proof"] = ["날개 휨", "내부 구조", "비행 중 날개 움직임"]
    return c


def candidate_long():
    c = candidate_medium()
    c["topic"] = "여객기 창문이 둥글게 바뀐 역사와 설계 변화"
    c["angle"] = "과거 설계 실패 이후 응력 집중을 줄이는 방향으로 바뀐 과정"
    c["core_question"] = "왜 초기 설계에서 지금의 둥근 창문으로 바뀌었을까?"
    c["fact_check_focus"] = ["과거 설계", "응력 집중", "설계 변화", "결과"]
    return c


def good_scenes():
    return [
        {
            "text": "비행기 창문에는 작은 구멍이 있습니다.",
            "visual_goal": "창문 아래쪽 작은 구멍 초근접",
            "keyword": "airplane window breather hole",
            "retention_role": "phenomenon",
        },
        {
            "text": "그런데 왜 일부러 작은 구멍을 뚫어둘까요?",
            "visual_goal": "창문 작은 구멍을 가리키는 근접 화면",
            "keyword": "airplane window hole closeup",
            "retention_role": "question",
        },
        {
            "text": "첫 단서는 창문 여러 층 사이의 압력 차이입니다.",
            "visual_goal": "여러 겹 창문 사이 공기층 단면",
            "keyword": "aircraft window layer pressure",
            "retention_role": "causal_clue",
        },
        {
            "text": "작은 구멍은 중간층 안팎의 압력 차이를 천천히 맞춥니다.",
            "visual_goal": "작은 통로를 통한 공기 흐름",
            "keyword": "airplane window pressure vent",
            "retention_role": "",
        },
    ]


def test_runtime_router():
    assert classify_runtime_bucket(candidate_simple()) == "24-30s"
    assert classify_runtime_bucket(candidate_medium()) == "32-42s"
    assert classify_runtime_bucket(candidate_long()) == "45-55s"


def test_first5_contract():
    ok, reason = validate_first5_progression(good_scenes())
    assert ok, reason

    bad_role = good_scenes()
    bad_role[1] = dict(bad_role[1])
    bad_role[1]["retention_role"] = "consequence"
    ok, _ = validate_first5_progression(bad_role)
    assert not ok

    bad_question = good_scenes()
    bad_question[1] = dict(bad_question[1])
    bad_question[1]["text"] = "왜 일부러 작은 구멍을 뚫어두나요?"
    ok, _ = validate_first5_progression(bad_question)
    assert not ok


def test_density_rejects_repetition():
    scenes = good_scenes()
    duplicate = dict(scenes[-1])
    duplicate["text"] = scenes[-1]["text"]
    scenes.append(duplicate)
    ok, _ = validate_density(scenes)
    assert not ok


def test_annotation_is_observational():
    original = {"title": "x", "scenes": good_scenes()}
    plan = build_retention_plan(candidate_simple())
    annotated = annotate_script(original, plan)
    assert original.get("runtime_bucket") is None
    assert annotated["runtime_bucket"] == "24-30s"
    assert annotated["retention_structure"]["version"] == 2
    assert annotated["retention_structure"]["first5_contract"][1]["role"] == "question"
    assert annotated["retention_structure"]["first5_contract"][2]["role"] == "causal_clue"


def main():
    test_runtime_router()
    print("CASE A runtime routing: PASS")
    test_first5_contract()
    print("CASE B observation-question-causal first5: PASS")
    test_density_rejects_repetition()
    print("CASE C density redundancy gate: PASS")
    test_annotation_is_observational()
    print("CASE D retention metadata: PASS")
    print("RETENTION STRUCTURE EXPERIMENT REGRESSION: PASS")


if __name__ == "__main__":
    main()
