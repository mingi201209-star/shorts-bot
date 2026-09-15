#!/usr/bin/env python3
"""Regression for Run 34847558126 Scene 5 observable-action classification."""
from video.hook_visual_dominance import requires_observable_action


def main():
    scene5 = {
        "text": "바퀴에 하중이 더 실리면서 제동 효과가 좋아지고 지상 활주 거리를 줄이는 데 도움을 줍니다.",
        "keyword": "aircraft spoiler braking landing rollout",
        "visual_goal": "Show the spoiler deployed after touchdown, transferring load to the wheels and visibly supporting braking during rollout.",
        "scene_role": "payoff",
        "claim_role": "primary_result",
        "owned_claim_id": "spoiler_braking_effectiveness",
    }
    assert requires_observable_action(scene5), "Run 34847558126 Scene 5 must require observable action"

    static_structure = {
        "text": "스포일러는 날개 윗면에 설치된 판입니다.",
        "keyword": "aircraft spoiler panel structure",
        "visual_goal": "Show the spoiler panel location on the wing.",
        "scene_role": "setup",
        "claim_role": "identity",
        "owned_claim_id": "spoiler_panel_identity",
    }
    assert not requires_observable_action(static_structure), "Static identity scene must remain eligible for still imagery"

    static_brake_structure = {
        "text": "브레이크 장치는 착륙장치 바퀴 안쪽에 있습니다.",
        "keyword": "aircraft wheel brake structure",
        "visual_goal": "Show the physical brake assembly location inside the wheel.",
        "scene_role": "setup",
        "claim_role": "identity",
        "owned_claim_id": "wheel_brake_structure",
    }
    assert not requires_observable_action(static_brake_structure), "Brake vocabulary alone must not force observable action"

    print("PASS: Scene 5 semantic action-required regression")


if __name__ == "__main__":
    main()
