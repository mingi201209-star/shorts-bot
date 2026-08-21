import importlib
import runpy


# Apply the same prerequisite order used by production before importing the module.
for hotfix in (
    "ci_design_causality_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
):
    runpy.run_path(hotfix, run_name="__main__")

sg = importlib.import_module("content.script_generator")


def scene(index):
    return {
        "text": f"비행기 창문 구조의 인과 단계 {index}를 설명합니다.",
        "visual_goal": f"비행기 창문 구조의 물리적 세부 요소 {index} 클로즈업",
        "keyword": f"airplane window detail {index}",
    }


# Isolate this regression from wording heuristics in the design classifier. The
# contract under test is routing: design context gets 8~13, normal context keeps 12~13.
sg.design_causality_applicable = lambda context: bool(context.get("_test_design"))
sg._SCRIPT_PARITY_ACTIVE_CONTEXT = {"_test_design": True}

valid, reason = sg.validate_scenes([scene(i) for i in range(8)])
assert valid, reason

valid, reason = sg.validate_scenes([scene(i) for i in range(7)])
assert not valid and "설계형 장면 수 부족" in reason, reason

valid, reason = sg.validate_scenes([scene(i) for i in range(10)])
assert valid, reason

sg._SCRIPT_PARITY_ACTIVE_CONTEXT = {"_test_design": False}
valid, reason = sg.validate_scenes([scene(i) for i in range(10)])
assert not valid and "장면 수 부족" in reason, reason

valid, reason = sg.validate_scenes([scene(i) for i in range(12)])
assert valid, reason

# Prompt policy must explicitly forbid padding a design script to 12 scenes.
assert "12 Scene을 채우기 위해" in sg._adaptive_scene_count_instruction({"_test_design": True})
assert "12~13 Scene" in sg._adaptive_scene_count_instruction({"_test_design": False})

print("PASS: adaptive design scene count preserves legacy non-design floor")
