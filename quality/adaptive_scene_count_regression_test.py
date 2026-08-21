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

# Production parity may delegate to _LEGACY. The regression must prove the
# adaptive validator is installed there, not merely on the exported module.
runtime = getattr(sg, "_SCRIPT_PARITY_RUNTIME", None) or getattr(sg, "_LEGACY", None)
assert runtime is not None, "production compatibility runtime missing"
assert getattr(runtime.validate_scenes, "_adaptive_scene_count_v2", False), (
    "adaptive validator not installed on production runtime"
)

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = design_context
valid, reason = runtime.validate_scenes([scene(i) for i in range(8)])
assert valid, reason
valid, reason = runtime.validate_scenes([scene(i) for i in range(7)])
assert not valid and "설계형 장면 수 부족" in reason, reason
valid, reason = runtime.validate_scenes([scene(i) for i in range(10)])
assert valid, reason

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = normal_context
valid, reason = runtime.validate_scenes([scene(i) for i in range(10)])
assert not valid and "장면 수 부족" in reason, reason
valid, reason = runtime.validate_scenes([scene(i) for i in range(12)])
assert valid, reason

# Exported direct caller must route to the same production runtime contract.
runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = design_context
valid, reason = sg.validate_scenes([scene(i) for i in range(8)])
assert valid, reason

assert "12 Scene을 채우기 위해" in sg._adaptive_scene_count_instruction(design_context)
assert "12~13 Scene" in sg._adaptive_scene_count_instruction(normal_context)

print("PASS: adaptive scene count installed on production compatibility runtime")
