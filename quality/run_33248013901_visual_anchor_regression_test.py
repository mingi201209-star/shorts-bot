"""Production HUMAN visual-QA counterexamples through Run 33976145878."""
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

# Run 33976145878: automated QA accepted generic aircraft/wing B-roll for a
# narration whose concrete subject was the trailing-edge flap. HUMAN QA of the
# final MP4 showed the flap itself was not established. The contract must carry
# aircraft + wing + flap, not silently collapse back to aircraft + wing.
flap_query = strengthened(
    "aircraft wing trailing edge high lift device",
    narration="플랩은 항공기 날개 뒤쪽에 붙는 고양력 장치입니다.",
    goal="항공기 날개 뒤쪽 플랩을 명확히 보여준다.",
)
flap_anchors = vd.extract_query_anchors(flap_query)
assert {"aircraft", "wing", "flap"}.issubset(set(flap_anchors)), (flap_query, flap_anchors)
if hasattr(vd, "get_current_visual_subject_anchor_contract"):
    flap_contract = vd.get_current_visual_subject_anchor_contract()
    assert set(flap_contract.get("required_anchors") or []) == {"aircraft", "wing", "flap"}, flap_contract

# Representative HUMAN-QA failure shapes from the successful production:
# passenger-window wing view and airport/taxiing aircraft. Domain/wing overlap
# is no longer enough when flap is the narrated concrete component.
generic_wing = candidate(99601, "aircraft airplane passenger window wing flight aviation")
airport_aircraft = candidate(99602, "commercial aircraft airplane taxiing airport runway airliner")
for wrong in (generic_wing, airport_aircraft):
    compatibility = vd.candidate_anchor_compatibility(wrong, flap_query)
    assert compatibility["total"] >= 3, (flap_query, compatibility)
    assert compatibility["compatible"] is False, (wrong, compatibility)
    assert vd.choose_best_candidate([wrong], subject_filter_query=flap_query) is None

actual_flap = candidate(
    99603,
    "aircraft airplane wing trailing-edge flap flaps deployed high lift closeup",
)
flap_compat = vd.candidate_anchor_compatibility(actual_flap, flap_query)
assert flap_compat["compatible"] is True, flap_compat
assert vd.choose_best_candidate([actual_flap], subject_filter_query=flap_query)["source_id"] == 99603

# A wing scene that does not name a flap keeps the established aircraft+wing
# contract; this change must not make every wing shot require a flap.
plain_wing_query = strengthened(
    "aircraft wing wingtip vortex",
    narration="비행기 날개 끝에서 소용돌이가 생깁니다.",
    goal="aircraft wingtip vortex closeup",
)
plain_wing_anchors = vd.extract_query_anchors(plain_wing_query)
assert "flap" not in plain_wing_anchors, plain_wing_anchors

print("RUN 33248013901 + 33249110048 + 33250343057 + 33976145878 VISUAL CONTRACT REGRESSION: PASS")
