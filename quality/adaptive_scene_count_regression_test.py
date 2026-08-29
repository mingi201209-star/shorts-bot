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
for count in (5, 6, 7, 8, 10):
    valid, reason = runtime.validate_scenes([scene(i) for i in range(count)])
    assert valid, (count, reason)

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = normal_context
valid, reason = runtime.validate_scenes([scene(i) for i in range(10)])
assert not valid and "장면 수 부족" in reason, reason
valid, reason = runtime.validate_scenes([scene(i) for i in range(12)])
assert valid, reason

runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = design_context
valid, reason = sg.validate_scenes([scene(i) for i in range(5)])
assert valid, reason

assert hasattr(runtime, "_adaptive_scene_count_instruction")
instruction = runtime._adaptive_scene_count_instruction(design_context)
assert "보통 6~7 Scene" in instruction
assert "hard minimum이 아니다" in instruction
assert "5 Scene 이하도 허용" in instruction
assert "8 Scene 이상" in instruction
assert "무엇이 새 정보인지 답할 수 없으면" in instruction
assert "12~13 Scene" in runtime._adaptive_scene_count_instruction(normal_context)

duration = runtime._adaptive_duration_instruction(design_context)
assert "20~35초" in duration
assert "18~20초" in duration
assert "목표 시간을 채우려고" in duration

length = runtime._adaptive_length_instruction(design_context)
assert "목표 시간을 채우기 위해" in length
assert "설명이 끝났다면 즉시 종료" in length

source = (ROOT / "content" / "script_generator.py").read_text(encoding="utf-8")
assert "{_adaptive_scene_count_instruction(candidate)}" in source
assert "{_adaptive_length_instruction(candidate)}" in source
assert "전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다." not in source
assert "Retention Story V2" in (ROOT / "ci_adaptive_scene_count_hotfix.py").read_text(encoding="utf-8")

print("PASS: adaptive scene count treats 6-7 as preference and permits shorter complete design scripts")
