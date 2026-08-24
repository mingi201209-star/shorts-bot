from content.script_engine_v2 import build_narrative_plan


def candidate(*, facts, visuals, topic="비행기 날개 끝 윙렛", angle="날개 끝 소용돌이를 줄이는 원리"):
    return {
        "topic": topic,
        "angle": angle,
        "core_question": "왜 날개 끝을 위로 꺾었을까요",
        "fact_check_focus": list(facts),
        "visual_proof": list(visuals),
        "micro_narrative": {
            "hook": "비행기 날개 끝은 위로 꺾여 있습니다",
            "reveal": "이 구조는 날개 끝 소용돌이를 줄입니다",
            "payoff": "결과적으로 불필요한 항력을 줄이는 데 도움이 됩니다",
        },
    }


medium = build_narrative_plan(
    candidate(
        facts=["날개 위아래 압력 차이", "날개 끝 와류"],
        visuals=["wingtip vortex", "winglet airflow"],
    )
)
assert medium["runtime_bucket"] == "50-60s", medium
assert medium["target_scene_count"] == 12, medium
assert len(medium["contracts"]) == 12, medium

long = build_narrative_plan(
    candidate(
        facts=["초기 설계", "설계 변화", "연료 효율"],
        visuals=["wingtip vortex", "winglet airflow"],
        topic="윙렛 설계 변화 역사",
        angle="초기 설계에서 현재 구조로 바뀐 이유",
    )
)
assert long["runtime_bucket"] == "55-60s", long
assert long["target_scene_count"] == 13, long
assert len(long["contracts"]) == 13, long

# Script Engine V2 must follow the retention contract rather than silently
# reintroducing a hard-coded scene ceiling that can diverge from future buckets.
assert medium["target_scene_count"] >= 12
assert long["target_scene_count"] >= 13

print("PASS: Script Engine V2 scene count follows retention v3 contract")
