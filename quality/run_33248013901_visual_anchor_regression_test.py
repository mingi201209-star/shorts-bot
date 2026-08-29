"""Run 33248013901 + 33249110048 HUMAN visual-QA counterexamples.

The production Script/FACT/grounded keywords were correct, but retrieval accepted
lexical false positives and then Run 33249110048 proved specificity-ladder
fallback queries could bypass the original Scene subject contract. Reuse the
established V1 regression first, then exercise compound identity, chroma, and
fallback inheritance.
"""
import runpy


base = runpy.run_path("quality/visual_subject_anchor_contract_v1_regression_test.py")
vd = base["vd"]
candidate = base["candidate"]
strengthened = base["strengthened"]


scene3_query = strengthened(
    "jet engine flow interface",
    narration="엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    goal="엔진 뒤에서 두 흐름이 만나는 경계를 보여준다.",
)
scene3_anchors = set(vd.extract_query_anchors(scene3_query))
assert {"aircraft", "engine"}.issubset(scene3_anchors), (scene3_query, scene3_anchors)
gas_stove = candidate(
    342972,
    "gas stove gas hob cooktop kitchen appliance 3d render blender render unreal engine",
)
assert vd.candidate_anchor_compatibility(gas_stove, scene3_query)["compatible"] is False
assert vd.choose_best_candidate([gas_stove], subject_filter_query=scene3_query) is None


scene4_query = strengthened(
    "jet engine chevron flow mixing",
    narration="톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    goal="제트 엔진 뒤 셰브론과 배기 흐름 혼합을 가까이 보여준다.",
)
scene4_anchors = set(vd.extract_query_anchors(scene4_query))
assert {"aircraft", "engine", "chevron"}.issubset(scene4_anchors), (scene4_query, scene4_anchors)
clock = candidate(
    4939,
    "clock mechanism watch macro machinery engineering industry engine cogwheel clockwork",
)
assert vd.candidate_anchor_compatibility(clock, scene4_query)["compatible"] is False
assert vd.choose_best_candidate([clock], subject_filter_query=scene4_query) is None


opening_query = strengthened(
    "airflow detail stage 1",
    narration="비행기 엔진 뒤는 톱니처럼 생겼습니다.",
    goal="비행기 엔진 뒤 톱니 모양 배기구를 명확하게 보여준다.",
)
opening_anchors = set(vd.extract_query_anchors(opening_query))
assert {"aircraft", "engine", "chevron"}.issubset(opening_anchors), (opening_query, opening_anchors)
generic_aircraft = candidate(
    15271,
    "aircraft flight plane airplane aviation flying engine cloud sky",
)
assert vd.candidate_anchor_compatibility(generic_aircraft, opening_query)["compatible"] is False
assert vd.choose_best_candidate([generic_aircraft], subject_filter_query=opening_query) is None


scene5_query = strengthened(
    "jet engine noise reduction",
    narration="이 혼합 변화의 대표적인 결과는 제트 엔진 소음 감소입니다.",
    goal="제트 엔진과 소음 감소 결과를 실제 항공 장면으로 보여준다.",
)
green_aircraft = candidate(
    14096,
    "flight plane airplane jet aircraft engine speed green screen blue screen",
)
tier, label = vd.general_scene_unknown_safe_tier(green_aircraft, scene5_query)
assert tier >= 6, (tier, label)
assert label == "EXPLICIT_CHROMA_STOCK_REJECTED", (tier, label)


correct = candidate(
    99901,
    "aircraft jet engine nacelle nozzle chevron serrated exhaust flow mixing closeup",
)
assert vd.candidate_anchor_compatibility(correct, scene4_query)["compatible"] is True
assert vd.choose_best_candidate([correct], subject_filter_query=scene4_query) is not None


# Run 33249110048: the original Scene contract must survive the entire
# specificity ladder. Fallback query wording must not weaken 3 required anchors.
fallback_query = "airplane engine chevron detail"
engine_only = candidate(99101, "engine turbine machinery detail")
aircraft_engine = candidate(99102, "aircraft airplane aviation jet engine detail")
full_subject = candidate(99103, "aircraft airplane jet engine nacelle nozzle chevron serrated detail")

for partial, expected_match in ((engine_only, 1), (aircraft_engine, 2)):
    compat = vd.candidate_anchor_compatibility(partial, opening_query)
    assert compat["matched"] == expected_match and compat["total"] == 3, compat
    tier, label = vd.general_scene_unknown_safe_tier(partial, fallback_query)
    assert tier >= 5, (expected_match, tier, label)
    assert label == "REQUIRED_SUBJECT_ANCHOR_INCOMPLETE", (expected_match, tier, label)

compat = vd.candidate_anchor_compatibility(full_subject, opening_query)
assert compat["matched"] == 3 and compat["total"] == 3, compat
tier, label = vd.general_scene_unknown_safe_tier(full_subject, fallback_query)
assert tier < 5, (tier, label)

fallback_green = candidate(
    99104,
    "aircraft airplane jet engine nacelle nozzle chevron serrated green screen chroma key",
)
tier, label = vd.general_scene_unknown_safe_tier(fallback_green, fallback_query)
assert tier >= 6, (tier, label)
assert label == "EXPLICIT_CHROMA_STOCK_REJECTED", (tier, label)

print("RUN 33248013901 + 33249110048 VISUAL ANCHOR REGRESSION: PASS")
