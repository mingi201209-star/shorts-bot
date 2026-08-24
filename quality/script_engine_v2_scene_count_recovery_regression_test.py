import subprocess
import sys

subprocess.run([sys.executable, "ci_script_v2_visual_goal_hotfix.py"], check=True)

from content.script_engine_v2 import build_narrative_plan
from content.script_engine_v2_runner import _recover_single_missing_middle_scene


def candidate():
    return {
        "topic": "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유",
        "angle": "객실 압력과 플러그 도어 구조",
        "core_question": "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유는 무엇일까요?",
        "micro_narrative": {
            "hook": "비행기 문은 비행 중 바깥쪽으로 바로 열리지 않습니다.",
            "core_question": "비행기 문이 비행 중 바깥쪽으로 바로 열리지 않는 이유는 무엇일까요?",
            "reveal": "객실 압력과 문 구조가 문을 프레임 쪽으로 더 단단히 누릅니다.",
            "payoff": "그래서 비행 중에는 문을 바깥쪽으로 바로 밀어 열기 어렵습니다.",
        },
        "fact_check_focus": ["객실 압력", "플러그 도어", "문 프레임"],
        "visual_proof": ["aircraft plug door", "door frame cross section"],
    }


def full_writer_scenes(plan):
    scenes = []
    for contract in plan["contracts"]:
        if contract.get("locked"):
            text = contract["locked_text"]
        else:
            text = f"이 단계에서는 객실 압력과 문 구조를 확인합니다."
        scenes.append({
            "text": text,
            "visual_goal": f"aircraft door mechanism scene {contract['index']}",
            "keyword": f"aircraft door mechanism {contract['index']}",
        })
    return scenes


def main():
    plan = build_narrative_plan(candidate())
    target = len(plan["contracts"])
    assert target >= 7

    full = full_writer_scenes(plan)

    # Production counterexample shape: exactly one middle beat is absent while
    # all immutable opening/closing anchors survived exactly as instructed.
    short = {"title": "door", "scenes": full[:5] + full[6:]}
    assert len(short["scenes"]) == target - 1
    recovered = _recover_single_missing_middle_scene(short, plan)
    assert len(recovered["scenes"]) == target
    assert recovered["scenes"][-2]["text"] == plan["contracts"][-2]["locked_text"]
    assert recovered["scenes"][-1]["text"] == plan["contracts"][-1]["locked_text"]
    reserved = recovered["scenes"][-3]
    assert reserved == {"text": "", "visual_goal": "", "keyword": ""}

    # If the missing scene could be a locked ending, do not guess.
    missing_payoff = {"title": "door", "scenes": full[:-1]}
    unchanged = _recover_single_missing_middle_scene(missing_payoff, plan)
    assert len(unchanged["scenes"]) == target - 1

    # More than one missing scene remains a structural failure.
    too_short = {"title": "door", "scenes": full[:-2]}
    unchanged = _recover_single_missing_middle_scene(too_short, plan)
    assert len(unchanged["scenes"]) == target - 2

    # Anchor drift also remains fail-closed.
    drifted = {"title": "door", "scenes": full[:5] + full[6:]}
    drifted["scenes"][0]["text"] = "다른 시작입니다."
    unchanged = _recover_single_missing_middle_scene(drifted, plan)
    assert len(unchanged["scenes"]) == target - 1

    print("PASS: target-1 Script V2 recovery is bounded by immutable narrative anchors")


if __name__ == "__main__":
    main()
