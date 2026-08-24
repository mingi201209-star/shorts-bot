from content.retention_structure import (
    RETENTION_STRUCTURE_VERSION,
    build_retention_plan,
    classify_runtime_bucket,
    density_prompt_contract,
    runtime_instruction,
)


def candidate(*, facts, visuals, text=""):
    return {
        "topic": text or "비행기 날개 끝 윙렛",
        "angle": "숨은 설계 이유",
        "core_question": "왜 이런 구조가 필요한가",
        "fact_check_focus": list(facts),
        "visual_proof": list(visuals),
        "micro_narrative": {
            "hook": "비행기 날개 끝은 위로 꺾여 있습니다",
            "core_question": "왜 날개 끝이 이렇게 생겼을까요",
            "reveal": "윙렛은 날개 끝 소용돌이를 줄이기 위한 구조입니다",
            "payoff": "작은 구조가 불필요한 항력을 줄이는 데 도움을 줍니다",
        },
    }


assert RETENTION_STRUCTURE_VERSION >= 3

rich = candidate(
    facts=["날개 위아래 압력 차이", "wingtip vortex", "induced drag"],
    visuals=["wingtip vortex visualization", "aircraft winglet closeup"],
    text="윙렛의 원리와 압력 차이 때문에 생기는 소용돌이의 결과",
)
assert classify_runtime_bucket(rich) == "50-60s"
rich_plan = build_retention_plan(rich)
assert rich_plan["min_seconds"] == 50
assert rich_plan["max_seconds"] == 60
assert 12 <= rich_plan["min_scenes"] <= rich_plan["max_scenes"]

long_form = candidate(
    facts=["초기 설계", "설계 변화", "효율 효과"],
    visuals=["old wing design", "modern winglet"],
    text="과거 설계가 어떻게 변화하고 발전했는지 역사와 설계 변화",
)
assert classify_runtime_bucket(long_form) == "55-60s"
long_plan = build_retention_plan(long_form)
assert long_plan["min_seconds"] == 55
assert long_plan["max_seconds"] == 60

thin = candidate(facts=["외형 관찰"], visuals=["winglet closeup"])
assert classify_runtime_bucket(thin) == "38-48s"
thin_plan = build_retention_plan(thin)
assert thin_plan["min_seconds"] == 38
assert thin_plan["max_seconds"] == 48

instruction = runtime_instruction(rich_plan)
assert "50~60초" in instruction
assert "반복" in instruction
assert "근거가 없는 사실은 만들지 않는다" in instruction

density = density_prompt_contract()
assert "현상→원인/제약→작동 원리→결과→현실적 의미" in density
assert "근거가 없는 역사, 사고, 수치, 효과" in density

print("PASS: one-minute retention contract preserves density and FACT safety")
