"""Production HUMAN visual-QA counterexamples through Run 33250343057."""
import runpy


base = runpy.run_path("quality/visual_subject_anchor_contract_v1_regression_test.py")
vd = base["vd"]
candidate = base["candidate"]
strengthened = base["strengthened"]

# Existing lexical false positives stay rejected.
scene3_query = strengthened(
    "jet engine flow interface",
    narration="엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    goal="엔진 뒤에서 두 흐름이 만나는 경계를 보여준다.",
)
gas_stove = candidate(342972, "gas stove kitchen appliance 3d render unreal engine")
assert vd.choose_best_candidate([gas_stove], subject_filter_query=scene3_query) is None

scene4_query = strengthened(
    "jet engine chevron flow mixing",
    narration="톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    goal="제트 엔진 뒤 셰브론과 배기 흐름 혼합을 가까이 보여준다.",
)
clock = candidate(4939, "clock mechanism machinery engineering engine cogwheel clockwork")
assert vd.choose_best_candidate([clock], subject_filter_query=scene4_query) is None

# #253 subject identity inheritance remains strict on fallback queries.
opening_query = strengthened(
    "airflow detail stage 1",
    narration="비행기 엔진 뒤는 톱니처럼 생겼습니다.",
    goal="비행기 엔진 뒤 톱니 모양 배기구를 명확하게 보여준다.",
)
fallback_opening = "airplane engine chevron detail"
for partial in (
    candidate(99101, "engine turbine machinery detail"),
    candidate(99102, "aircraft airplane aviation jet engine detail"),
):
    tier, _ = vd.general_scene_unknown_safe_tier(partial, fallback_opening)
    assert tier >= 5

full_subject = candidate(99103, "aircraft airplane jet engine nacelle nozzle chevron serrated detail")
tier, _ = vd.general_scene_unknown_safe_tier(full_subject, fallback_opening)
assert tier < 5

fallback_green = candidate(99104, "aircraft jet engine nacelle nozzle chevron green screen chroma key")
tier, label = vd.general_scene_unknown_safe_tier(fallback_green, fallback_opening)
assert tier >= 6 and label == "EXPLICIT_CHROMA_STOCK_REJECTED"

# Run 33250343057: physical identity alone must not satisfy an explanatory Scene.
# Scene 3: generic airplane+engine 2/2 but no flow/interface evidence -> FAIL.
scene3_query = strengthened(
    "jet engine flow interface",
    narration="엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    goal="엔진 뒤에서 두 흐름이 만나는 경계를 보여준다.",
)
fallback_scene3 = "airplane engine detail"
generic_engine = candidate(15271, "aircraft airplane aviation jet engine closeup detail")
tier, label = vd.general_scene_unknown_safe_tier(generic_engine, fallback_scene3)
assert tier >= 5 and label == "REQUIRED_EXPLANATORY_ANCHOR_MISSING", (tier, label)
flow_evidence = candidate(99501, "aircraft jet engine exhaust airflow plume boundary interface closeup")
tier, label = vd.general_scene_unknown_safe_tier(flow_evidence, fallback_scene3)
assert tier < 5, (tier, label)

# Scene 4: generic jet engine is not enough; chevron identity plus flow/mixing evidence is.
scene4_query = strengthened(
    "jet engine chevron flow mixing",
    narration="톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    goal="제트 엔진 뒤 셰브론과 배기 흐름 혼합을 가까이 보여준다.",
)
fallback_scene4 = "airplane engine chevron detail"
generic_chevron = candidate(99502, "aircraft jet engine nacelle nozzle chevron serrated closeup")
tier, label = vd.general_scene_unknown_safe_tier(generic_chevron, fallback_scene4)
assert tier >= 5 and label == "REQUIRED_EXPLANATORY_ANCHOR_MISSING", (tier, label)
mixing_evidence = candidate(99503, "aircraft jet engine nacelle nozzle chevron serrated exhaust airflow mixing plume")
tier, label = vd.general_scene_unknown_safe_tier(mixing_evidence, fallback_scene4)
assert tier < 5, (tier, label)

# Scene 5: generic aircraft/engine cannot stand in for noise-reduction evidence.
scene5_query = strengthened(
    "jet engine noise reduction",
    narration="이 혼합 변화의 대표적인 결과는 제트 엔진 소음 감소입니다.",
    goal="제트 엔진과 소음 감소 결과를 실제 항공 장면으로 보여준다.",
)
fallback_scene5 = "airplane engine"
generic_aircraft = candidate(99504, "aircraft airplane aviation jet engine flight")
tier, label = vd.general_scene_unknown_safe_tier(generic_aircraft, fallback_scene5)
assert tier >= 5 and label == "REQUIRED_EXPLANATORY_ANCHOR_MISSING", (tier, label)
noise_evidence = candidate(99505, "aircraft jet engine acoustic noise reduction quieter exhaust test")
tier, label = vd.general_scene_unknown_safe_tier(noise_evidence, fallback_scene5)
assert tier < 5, (tier, label)

print("RUN 33248013901 + 33249110048 + 33250343057 VISUAL CONTRACT REGRESSION: PASS")
