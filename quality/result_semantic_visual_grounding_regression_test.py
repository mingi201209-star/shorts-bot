"""Regression for HUMAN-QA failures in spoiler result scenes.

Guards the generic contracts only: grounded result semantics must survive visual
fallback, and a generic aircraft wing must never opt into winglet explanation.
"""
from video.grounded_explanatory_visual import (
    explanatory_evidence_complete,
    explanatory_signature,
    generation_requirement,
    required_explanatory_groups,
)
from video.visual_explanation import _winglet_subject, plan_explanation

scene4 = {
    "keyword": "aircraft wing spoiler weight wheel",
    "text": "양력을 없애면 항공기 무게가 바퀴에 더 실리게 됩니다.",
    "visual_goal": "항공기 무게가 착륙 장치의 바퀴로 전달되는 모습을 표현합니다.",
}
scene5 = {
    "keyword": "aircraft wing spoiler braking effectiveness",
    "text": "이로 인해 바퀴 제동이 더 잘 작동해 착륙 후 지상 활주 거리가 줄어듭니다.",
    "visual_goal": "활주로에서 감속하는 항공기와 짧아지는 지상 활주 거리를 보여줍니다.",
}

assert set(required_explanatory_groups(scene4)) == {"load", "wheel"}
assert set(explanatory_signature(scene4)) == {"explain:load", "explain:wheel"}
assert "generic aircraft or wing shot is not enough" in generation_requirement(scene4)
assert explanatory_evidence_complete(scene4, {"visible_explanatory_groups": ["load"]})[0] is False
assert explanatory_evidence_complete(scene4, {"visible_explanatory_groups": ["load", "wheel"]})[0] is True

assert set(required_explanatory_groups(scene5)) == {"braking", "effect"}
assert set(explanatory_signature(scene5)) == {"explain:braking", "explain:effect"}
assert "generic flight" in generation_requirement(scene5)
assert explanatory_evidence_complete(scene5, {"visible_explanatory_groups": ["braking"]})[0] is False
assert explanatory_evidence_complete(scene5, {"visible_explanatory_groups": ["braking", "effect"]})[0] is True

# Run 34784063294 / 34786153210: `aircraft wing spoiler ...` was incorrectly
# classified as a winglet solely because `_winglet_subject` accepted the broad
# phrase `aircraft wing`, producing WINGLET_FLOW for a spoiler scene.
assert _winglet_subject(scene4) is False
assert _winglet_subject(scene5) is False
assert plan_explanation(scene4) is None
assert plan_explanation(scene5) is None

# Real winglet subjects retain the existing deterministic explanation path.
winglet = {
    "keyword": "aircraft wing winglet airflow",
    "text": "윙렛 주변의 공기 흐름을 보여줍니다.",
    "visual_goal": "날개 끝 윙렛과 흐름을 보여줍니다.",
}
assert _winglet_subject(winglet) is True
assert plan_explanation(winglet)["template"] == "WINGLET_FLOW"

# A single generic result word still cannot promote itself into a hard factual
# relation gate; the existing two-independent-group rule remains unchanged.
assert required_explanatory_groups({"keyword": "aircraft effectiveness"}) == []

print("RESULT SEMANTIC VISUAL GROUNDING REGRESSION: PASS")
