"""Run 33248013901 HUMAN visual-QA counterexamples.

The production Script/FACT/grounded keywords were correct, but retrieval accepted
lexical false positives (Unreal Engine gas stove, clock mechanism 'engine') and
explicit green-screen aircraft. Reuse the established V1 regression first, then
exercise the stricter compound physical identity contract.
"""
import runpy


base = runpy.run_path("quality/visual_subject_anchor_contract_v1_regression_test.py")
vd = base["vd"]
candidate = base["candidate"]
strengthened = base["strengthened"]


# Scene 3 LIVE query: 'jet' must preserve aviation domain, so a kitchen asset
# tagged only by the renderer name 'Unreal Engine' cannot satisfy the contract.
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


# Scene 4 LIVE query: chevron is a real component identity, not decorative text.
# A clock mechanism containing the lexical tokens engine/engineering must fail.
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


# Opening LIVE failure: generic aircraft/engine footage is not enough when the
# narration and visual goal explicitly name the tooth-like physical feature.
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


# Explicit unkeyed chroma stock must never be treated as real-world evidence.
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


# A genuinely matching physical subject remains selectable; no threshold was
# lowered and no extra retrieval/API budget is introduced.
correct = candidate(
    99901,
    "aircraft jet engine nacelle nozzle chevron serrated exhaust flow mixing closeup",
)
assert vd.candidate_anchor_compatibility(correct, scene4_query)["compatible"] is True
assert vd.choose_best_candidate([correct], subject_filter_query=scene4_query) is not None

print("RUN 33248013901 VISUAL ANCHOR REGRESSION: PASS")
