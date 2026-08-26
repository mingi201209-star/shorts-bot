from quality.final_visual_director import (
    director_qa, evaluate_candidate, infer_scene_role,
    select_best_valid_candidate, selective_repair_plan,
    MAX_DIRECTOR_RECOVERY_ROUNDS,
)


def scores(**kw):
    base = dict(semantic_match=9, explanatory_power=8, subject_prominence=8,
                mobile_clarity=9, hook_visual_strength=8, payoff_visual_strength=8,
                artifact_risk=1, obstruction_risk=1)
    base.update(kw); return base


# 1 generic aircraft B-roll cannot explain a wingtip-vortex mechanism.
assert not evaluate_candidate({"scores": scores(explanatory_power=3)}, "mechanism")["valid"]
# semantic relevance alone must not hide that hard failure.
assert evaluate_candidate({"scores": scores(semantic_match=9, explanatory_power=3)}, "mechanism")["failures"][0]["metric"] == "explanatory_power"

# Candidate competition chooses BEST valid, not first PASS.
a = {"id": "A", "scores": scores(explanatory_power=7.1, composition_quality=6)}
b = {"id": "B", "scores": scores(explanatory_power=8.8, composition_quality=8)}
assert select_best_valid_candidate([a, b], "mechanism")["id"] == "B"

# 2 repeated source across three scenes is a final-director failure.
repeat = [{"scene_index": i, "role": "setup", "source_id": "same-shot", "scores": scores()} for i in range(3)]
assert any(x["type"] == "repetition_risk" for x in director_qa(repeat)["issues"])

# 3 only the bad scene is selected for regeneration.
obs = [{"scene_index": i, "role": "setup", "source_id": str(i), "scores": scores()} for i in range(6)]
obs[3]["role"] = "mechanism"; obs[3]["scores"] = scores(explanatory_power=2)
plan = selective_repair_plan(director_qa(obs), 0)
assert plan["scene_indexes"] == [3]

# 4 subtitle obstruction relocates subtitle before regenerating video.
qa = director_qa([{"scene_index": 4, "role": "mechanism", "source_id": "x", "scores": scores(), "subtitle_obstruction": True}])
plan = selective_repair_plan(qa, 0)
assert plan["subtitle_only"] == [4] and plan["scene_indexes"] == []

# 5 AI structural artifact selects only that scene.
qa = director_qa([{"scene_index": 2, "role": "mechanism", "source_id": "ai", "scores": scores(ai_artifact_risk=9)}])
assert selective_repair_plan(qa, 0)["scene_indexes"] == [2]

# 6 distant/small Hook subject fails Hook hard floor.
assert not evaluate_candidate({"scores": scores(subject_prominence=3)}, "hook")["valid"]

# 7 generic transition may pass the relaxed explanatory floor.
assert evaluate_candidate({"scores": scores(explanatory_power=4.2, semantic_match=7)}, "transition")["valid"]

# 8 bounded Director recovery fails closed after two rounds.
failed = {"overall_pass": False, "issues": [{"scene_index": 1, "type": "semantic_match", "severity": "high"}]}
assert selective_repair_plan(failed, MAX_DIRECTOR_RECOVERY_ROUNDS)["status"] == "HOLD"

# Information-beat validation: changed claim with unchanged visual is flagged.
qa = director_qa([{"scene_index": 2, "role": "cause", "source_id": "x", "scores": scores(), "information_beat_changed": True, "same_visual_as_previous": True}])
assert any(x["type"] == "stale_information_beat" for x in qa["issues"])

# Role metadata can be inferred without changing script schema.
assert infer_scene_role({"text": "이 구조는 날개 끝 소용돌이를 줄입니다."}, 3, 8) == "mechanism"

print("VISUAL_QUALITY_V1_REGRESSION PASS")
