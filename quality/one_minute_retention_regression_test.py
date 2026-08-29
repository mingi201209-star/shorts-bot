import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


assert RETENTION_STRUCTURE_VERSION >= 4

rich = candidate(
    facts=["날개 위아래 압력 차이", "wingtip vortex", "induced drag"],
    visuals=["wingtip vortex visualization", "aircraft winglet closeup"],
    text="윙렛의 원리와 압력 차이 때문에 생기는 소용돌이의 결과",
)
assert classify_runtime_bucket(rich) == "24-35s"
rich_plan = build_retention_plan(rich)
assert rich_plan["min_seconds"] == 24
assert rich_plan["max_seconds"] == 35
assert 6 <= rich_plan["target_scene_count"] <= 8
assert "min_scenes" not in rich_plan and "max_scenes" not in rich_plan

long_form = candidate(
    facts=["초기 설계", "설계 변화", "효율 효과"],
    visuals=["old wing design", "modern winglet"],
    text="과거 설계가 어떻게 변화하고 발전했는지 역사와 설계 변화",
)
assert classify_runtime_bucket(long_form) == "30-42s"
long_plan = build_retention_plan(long_form)
assert long_plan["min_seconds"] == 30
assert long_plan["max_seconds"] == 42
assert long_plan["target_scene_count"] > rich_plan["target_scene_count"]

thin = candidate(facts=["외형 관찰"], visuals=["winglet closeup"])
assert classify_runtime_bucket(thin) == "20-28s"
thin_plan = build_retention_plan(thin)
assert thin_plan["min_seconds"] == 20
assert thin_plan["max_seconds"] == 28
assert thin_plan["target_scene_count"] == 6

instruction = runtime_instruction(rich_plan)
assert "24~35초" in instruction
assert "quota가 아니다" in instruction
assert "목표 시간을 채우려고" in instruction
assert "새 정보를 최소 하나" in instruction

density = density_prompt_contract()
assert "NEW INFORMATION" in density
assert "payoff는 마지막에 한 번" in density
assert "5~8 Scene, 20~35초" in density
assert "효율/성능/안정성" in density

print("PASS: former one-minute contract now enforces content-derived retention without padding")
