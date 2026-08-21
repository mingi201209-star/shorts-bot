import importlib
import runpy
import sys
from pathlib import Path


# GitHub Actions executes this file from quality/, so ensure the repository root
# is importable before loading content.script_generator.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Apply the same prerequisite order used by production before importing the module.
for hotfix in (
    "ci_design_causality_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
):
    runpy.run_path(str(ROOT / hotfix), run_name="__main__")

# A prerequisite hotfix may import script_generator before the later file patches
# are written. Reload once so this in-process regression observes the same final
# on-disk module that production imports after applying the hotfix chain.
sg = importlib.reload(importlib.import_module("content.script_generator"))


def scene(index):
    return {
        "text": f"비행기 창문 구조의 인과 단계 {index}를 설명합니다.",
        "visual_goal": f"비행기 창문 구조의 물리적 세부 요소 {index} 클로즈업",
        "keyword": f"airplane window detail {index}",
    }


# Exercise the real production classifier and parity context rather than a
# test-only monkeypatch, because compatibility layers may delegate to _LEGACY.
# The contract under test is routing: design context gets 8~13, normal keeps 12~13.
design_context = {
    "topic": "비행기 창문 설계 구조",
    "angle": "왜 이런 구조로 설계됐는가",
    "core_question": "이 구조는 어떻게 압력 차이를 견디는가",
}
sg._SCRIPT_PARITY_ACTIVE_CONTEXT = design_context

valid, reason = sg.validate_scenes([scene(i) for i in range(8)])
assert valid, reason

valid, reason = sg.validate_scenes([scene(i) for i in range(7)])
assert not valid and "설계형 장면 수 부족" in reason, reason

valid, reason = sg.validate_scenes([scene(i) for i in range(10)])
assert valid, reason

sg._SCRIPT_PARITY_ACTIVE_CONTEXT = {
    "topic": "철새의 이동 현상",
    "angle": "계절별 이동 관찰",
    "core_question": "철새는 언제 이동하는가",
}
valid, reason = sg.validate_scenes([scene(i) for i in range(10)])
assert not valid and "장면 수 부족" in reason, reason

valid, reason = sg.validate_scenes([scene(i) for i in range(12)])
assert valid, reason

# Prompt policy must explicitly forbid padding a design script to 12 scenes.
assert "12 Scene을 채우기 위해" in sg._adaptive_scene_count_instruction(design_context)
assert "12~13 Scene" in sg._adaptive_scene_count_instruction({
    "topic": "철새의 이동 현상",
    "angle": "계절별 이동 관찰",
    "core_question": "철새는 언제 이동하는가",
})

print("PASS: adaptive design scene count preserves legacy non-design floor")
