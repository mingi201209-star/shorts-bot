import importlib
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for hotfix in (
    "ci_design_causality_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
):
    runpy.run_path(str(ROOT / hotfix), run_name="__main__")

sg = importlib.reload(importlib.import_module("content.script_generator"))


def scene(index):
    return {
        "text": f"비행기 창문 구조의 인과 단계 {index}를 설명합니다.",
        "visual_goal": f"비행기 창문 구조의 물리적 세부 요소 {index} 클로즈업",
        "keyword": f"airplane window detail {index}",
    }


design_context = {
    "topic": "비행기 창문 설계 구조",
    "angle": "왜 이런 구조로 설계됐는가",
    "core_question": "이 구조는 어떻게 압력 차이를 견디는가",
}
normal_context = {
    "topic": "철새의 이동 현상",
    "angle": "계절별 이동 관찰",
    "core_question": "철새는 언제 이동하는가",
}

runtime = getattr(sg, "_SCRIPT_PARITY_RUNTIME", None) or getattr(sg, "_LEGACY", None)
assert runtime is not None, "production compatibility runtime missing"
assert getattr(runtime.validate_scenes, "_adaptive_scene_count_v3", False), (
    "adaptive validator not installed on production runtime"
)

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = design_context
for count in (6, 7, 8, 10):
    valid, reason = runtime.validate_scenes([scene(i) for i in range(count)])
    assert valid, (count, reason)
valid, reason = runtime.validate_scenes([scene(i) for i in range(5)])
assert not valid and "설계형 장면 수 부족" in reason, reason

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = normal_context
valid, reason = runtime.validate_scenes([scene(i) for i in range(10)])
assert not valid and "장면 수 부족" in reason, reason
valid, reason = runtime.validate_scenes([scene(i) for i in range(12)])
assert valid, reason

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = design_context
valid, reason = sg.validate_scenes([scene(i) for i in range(6)])
assert valid, reason

assert hasattr(runtime, "_adaptive_scene_count_instruction")
instruction = runtime._adaptive_scene_count_instruction(design_context)
assert "보통 6~8 Scene" in instruction
assert "새 정보가 실제로 필요하면" in instruction
assert "12~13 Scene" in runtime._adaptive_scene_count_instruction(normal_context)
assert "25~35초" in runtime._adaptive_duration_instruction(design_context)

source = (ROOT / "content" / "script_generator.py").read_text(encoding="utf-8")
assert "{_adaptive_scene_count_instruction(candidate)}" in source
assert "RETENTION STORY V1" in source

print("PASS: adaptive scene count allows dense 6-8 scene design shorts without forcing compression")
