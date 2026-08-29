"""Run 33256014054 Scene 3 grounded explanatory visual-supply regression.

No network/model call is performed. The regression composes the same visual
contracts through #253/#254/#255/#256, then proves the Scene 3 relation nucleus
survives stock fallback, still generation/reuse, Vision evidence and explanation.
"""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Established subject/explanatory guards (#253/#254), including their false-
# positive corpus, run first on the pristine checkout and expose helpers below.
base = runpy.run_path(str(ROOT / "quality/run_33248013901_visual_anchor_regression_test.py"))
vd = base["vd"]
candidate = base["candidate"]
strengthened = base["strengthened"]

# Canonical opening supply (#255), still verifier + trusted parent propagation (#256).
import ci_canonical_visual_supply_contract_hotfix as canonical_supply  # noqa: E402
canonical_supply.main()
import ci_still_image_verifier_contract_hotfix as still_verifier  # noqa: E402
still_verifier.main()
import ci_grounded_explanatory_visual_supply_hotfix as explanatory_supply  # noqa: E402
explanatory_supply.main()

from video import grounded_explanatory_visual as gev  # noqa: E402
from video import hook_visual_dominance as dominance  # noqa: E402
from video import still_image_fallback as still  # noqa: E402
from video import visual_explanation as vx  # noqa: E402

SCENE3 = {
    "scene_id": 3,
    "role": "mechanism_input",
    "owned_claim_id": "flow_interface",
    "text": "원인의 첫 단서는 엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    "visual_goal": "배기 흐름과 주변 흐름이 만나는 경계를 보여준다.",
    "keyword": "jet engine flow interface",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
        "grounding_source": "trusted-fixture",
    },
}

SCENE2 = {
    "scene_id": 2,
    "role": "question",
    "text": "그런데 비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까요?",
    "visual_goal": "비행기 엔진의 구조",
    "keyword": "aircraft engine chevron airflow detail stage 2",
    "_canonical_visual_supply": dict(SCENE3["_canonical_visual_supply"]),
}


def vision_result(*, visible_components, explanatory_groups=(), passed=True):
    return {
        "pass": bool(passed),
        "target_subject": "jet engine rear flow",
        "subject_dominance": 9.0,
        "subject_visibility": 9.0,
        "action_match": 10.0,
        "competing_subject_risk": 1.0,
        "vertical_crop_subject_visible": True,
        "visible_components": list(visible_components),
        "visible_explanatory_groups": list(explanatory_groups),
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "reason": "deterministic mocked visible evidence",
    }


# Contract is exactly flow + interface, not flow alone.
assert gev.required_explanatory_groups(SCENE3) == ["flow", "interface"]
assert gev.required_explanatory_groups(SCENE2) == []  # lone airflow stays non-factual

original_eval = dominance.evaluate_hook_subject_dominance
try:
    # A. Subject + exhaust flow but no visible interface remains FAIL.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        visible_components=["aircraft", "engine", "exhaust flow", "airflow"],
        explanatory_groups=["flow"],
    )
    verified, evidence = still._verify_motion_clip(SCENE3, ROOT / "mock-scene3.mp4")
    assert verified is False, evidence
    assert evidence.get("missing_explanatory_groups") == ["interface"], evidence

    # B. Subject + flow + directly visible interface evidence can PASS.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        visible_components=["aircraft", "engine", "exhaust flow", "airflow", "boundary"],
        explanatory_groups=["flow", "interface"],
    )
    verified, evidence = still._verify_motion_clip(SCENE3, ROOT / "mock-scene3.mp4")
    assert verified is True, evidence
    assert evidence.get("missing_explanatory_groups") == [], evidence

    # K. #256 trusted parent-domain behavior remains unchanged for Scene 2.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        visible_components=["engine", "chevron", "airflow"], explanatory_groups=[]
    )
    verified, evidence = still._verify_motion_clip(SCENE2, ROOT / "mock-scene2.mp4")
    assert verified is True, evidence
    assert evidence.get("parent_domain_satisfied") == ["aircraft"], evidence

    # K2. That parent-domain exception cannot bypass Scene 3's interface evidence.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        visible_components=["aircraft", "engine", "chevron", "exhaust flow"],
        explanatory_groups=["flow"],
    )
    verified, evidence = still._verify_motion_clip(SCENE3, ROOT / "mock-scene3.mp4")
    assert verified is False, evidence
    assert "interface" in evidence.get("missing_explanatory_groups", []), evidence
finally:
    dominance.evaluate_hook_subject_dominance = original_eval

# C/D/E/F. #254 still controls stock/fallback acceptance.
scene3_query = strengthened(
    "jet engine flow interface", narration=SCENE3["text"], goal=SCENE3["visual_goal"]
)
for bad in (
    candidate(56001, "aircraft airplane aviation jet engine closeup detail"),
    candidate(56002, "aircraft jet engine exhaust airflow plume"),
    candidate(56003, "water fluid boundary interface junction meeting"),
):
    tier, _ = vd.general_scene_unknown_safe_tier(bad, "airplane engine detail")
    assert tier >= 5, (bad.get("id"), tier)

complete = candidate(56004, "aircraft jet engine exhaust airflow plume boundary interface meeting")
tier, label = vd.general_scene_unknown_safe_tier(complete, "airplane engine detail")
assert tier < 5, (tier, label)

# F. Lexical fallback may broaden, but authority still retains flow+interface.
fallbacks = vd._general_fallback_queries(scene3_query)
assert fallbacks, fallbacks
selection_contract = vd.get_current_visual_subject_anchor_contract()
required_from_contract = vd._required_explanatory_anchors(selection_contract)
assert required_from_contract == ["flow", "interface"], (fallbacks, selection_contract)
for fallback in fallbacks:
    tier, _ = vd.general_scene_unknown_safe_tier(complete, fallback)
    assert tier < 5, (fallback, tier)

# G. Still generation/reuse preserves both explanatory groups.
prompt = still._prompt(SCENE3).lower()
assert "flow" in prompt and "interface" in prompt and "single" in prompt, prompt
signature = still._anchor_signature(SCENE3)
assert "explain:flow" in signature and "explain:interface" in signature, signature
assert still._anchor_signature(SCENE2) != signature

# G2. VisualExplanation safely supports this grounded relation with zero API calls.
plan = vx.plan_explanation(SCENE3)
assert plan and plan.get("template") == "FLOW_INTERFACE", plan
assert vx.annotation_fact_safe(SCENE3, plan) is True
original_render = vx._render_clip
original_cached = vx._cached_verified_asset
try:
    vx._render_clip = lambda base_image, output_path, duration, plan: Path(output_path).write_bytes(b"deterministic")
    vx._cached_verified_asset = lambda scene: (None, None)
    vx.reset_visual_explanation_budget()
    result = vx.generate_visual_explanation_fallback(
        SCENE3,
        output_path=ROOT / "mock-flow-interface.mp4",
        duration=3.0,
        trigger_reason="run_33256014054_regression",
    )
    assert result is not None, result
    assert result.get("mode") == "EXPLANATORY_2D", result
    assert result.get("required_explanatory_groups") == ["flow", "interface"], result
    assert result.get("additional_llm_calls") == 0
    assert result.get("additional_vision_calls") == 0
finally:
    vx._render_clip = original_render
    vx._cached_verified_asset = original_cached
    (ROOT / "mock-flow-interface.mp4").unlink(missing_ok=True)

# H. Scene 4 #254 behavior remains: flow+mixing required in addition to subject.
strengthened(
    "jet engine chevron flow mixing",
    narration="톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    goal="제트 엔진 뒤 셰브론과 흐름 혼합을 보여준다.",
)
generic_chevron = candidate(56005, "aircraft jet engine nacelle nozzle chevron serrated closeup")
tier, _ = vd.general_scene_unknown_safe_tier(generic_chevron, "airplane engine chevron detail")
assert tier >= 5
mixing = candidate(56006, "aircraft jet engine nacelle nozzle chevron serrated exhaust airflow mixing blend")
tier, _ = vd.general_scene_unknown_safe_tier(mixing, "airplane engine chevron detail")
assert tier < 5

# I. Scene 5 #254 behavior remains: noise+reduction required.
strengthened(
    "jet engine noise reduction",
    narration="대표적인 결과는 제트 엔진 소음 감소입니다.",
    goal="제트 엔진과 소음 감소 결과를 보여준다.",
)
generic_aircraft = candidate(56007, "aircraft airplane aviation jet engine flight")
tier, _ = vd.general_scene_unknown_safe_tier(generic_aircraft, "airplane engine")
assert tier >= 5
noise_reduction = candidate(56008, "aircraft jet engine acoustic noise reduction quieter sound test")
tier, _ = vd.general_scene_unknown_safe_tier(noise_reduction, "airplane engine")
assert tier < 5

# J. The established #253/#254 false-positive corpus already executed at the top
# in its pristine-install state. Dedicated #255/#256 workflows run independently
# in CI so runtime installers are not re-applied to an already patched checkout.
print("RUN 33256014054 FLOW_INTERFACE GROUNDED VISUAL SUPPLY REGRESSION: PASS")
