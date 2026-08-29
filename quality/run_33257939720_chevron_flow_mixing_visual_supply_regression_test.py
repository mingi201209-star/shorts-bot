"""Run 33257939720 Scene 4 chevron-flow-mixing supply regression.

Zero network/model calls. This reproduces the first supply capability gap after
#257: complete subject + flow/mixing stock remains strict, the still budget stays
2, and deterministic VisualExplanation can supply only the owned grounded
mechanism-change without leaking Scene 5 noise reduction.
"""
from copy import deepcopy
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Start with the established #253/#254 false-positive corpus on pristine files.
base = runpy.run_path(str(ROOT / "quality/run_33248013901_visual_anchor_regression_test.py"))
vd = base["vd"]
candidate = base["candidate"]
strengthened = base["strengthened"]

# Compose the same runtime supply contracts used by #255/#256/#257.
import ci_canonical_visual_supply_contract_hotfix as canonical_supply  # noqa: E402
canonical_supply.main()
import ci_still_image_verifier_contract_hotfix as still_verifier  # noqa: E402
still_verifier.main()
import ci_grounded_explanatory_visual_supply_hotfix as explanatory_supply  # noqa: E402
explanatory_supply.main()

from video import grounded_explanatory_visual as gev  # noqa: E402
from video import still_image_fallback as still  # noqa: E402
from video import visual_explanation as vx  # noqa: E402

TRUSTED_SUPPLY = {
    "canonical_subject": "jet engine nacelle/nozzle chevrons",
    "identity_confidence": 0.98,
    "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
    "grounding_source": "trusted-run-33257939720-fixture",
}

SCENE4 = {
    "scene_id": 4,
    "role": "reveal",  # actual five-scene Script structural role
    "owned_claim_id": "chevron_flow_mixing",
    "text": "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    "visual_goal": "제트 엔진 뒤 셰브론과 두 흐름이 섞이는 관계를 보여준다.",
    "keyword": "jet engine chevron flow mixing",
    "_canonical_visual_supply": dict(TRUSTED_SUPPLY),
}

SCENE3 = {
    "scene_id": 3,
    "role": "causal_clue",
    "owned_claim_id": "flow_interface",
    "text": "원인의 첫 단서는 엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    "visual_goal": "배기 흐름과 주변 흐름이 만나는 경계를 보여준다.",
    "keyword": "jet engine flow interface",
    "_canonical_visual_supply": dict(TRUSTED_SUPPLY),
}

SCENE5 = {
    "scene_id": 5,
    "role": "payoff",
    "owned_claim_id": "noise_reduction",
    "text": "대표적인 결과는 제트 엔진 소음 감소입니다.",
    "visual_goal": "제트 엔진의 소음 감소 결과를 보여준다.",
    "keyword": "jet engine noise reduction",
    "_canonical_visual_supply": dict(TRUSTED_SUPPLY),
}

# Still capacity itself is untouched; the new supply exists after exhaustion.
assert still.STILL_IMAGE_MAX_PER_VIDEO == 2, still.STILL_IMAGE_MAX_PER_VIDEO

# A. Complete trusted subject + flow + mixing relation is eligible.
assert gev.subject_anchor_words(SCENE4) == ["aircraft", "engine", "chevron"]
assert gev.required_explanatory_groups(SCENE4) == ["flow", "mixing"]
assert gev.chevron_flow_mixing_supported(SCENE4) is True
plan4 = vx.plan_explanation(SCENE4)
assert plan4 and plan4.get("template") == "CHEVRON_FLOW_MIXING", plan4
assert plan4.get("required_subject_anchors") == ["aircraft", "engine", "chevron"], plan4
assert plan4.get("required_explanatory_groups") == ["flow", "mixing"], plan4
assert plan4.get("owned_claim_id") == "chevron_flow_mixing", plan4
assert plan4.get("forbidden_claim_ids") == ["noise_reduction"], plan4
assert vx.annotation_fact_safe(SCENE4, plan4) is True

# B. Same compound subject but flow only cannot opt in.
b = deepcopy(SCENE4)
b["keyword"] = "jet engine chevron exhaust flow"
assert gev.required_explanatory_groups(b) == []
assert gev.chevron_flow_mixing_supported(b) is False
assert vx.plan_explanation(b) is None

# C. Complete flow+mixing without chevron subject cannot opt in.
c = deepcopy(SCENE4)
c["keyword"] = "jet engine flow mixing"
assert gev.subject_anchor_words(c) == ["aircraft", "engine"]
assert gev.chevron_flow_mixing_supported(c) is False
assert vx.plan_explanation(c) is None

# D. Generic chevron closeup without the relation nucleus cannot opt in.
d = deepcopy(SCENE4)
d["keyword"] = "jet engine chevron serrated closeup"
assert gev.chevron_flow_mixing_supported(d) is False
assert vx.plan_explanation(d) is None

# E. Clock/cogwheel mixing-like diagram is rejected by physical subject identity.
e = deepcopy(SCENE4)
e["keyword"] = "clock cogwheel flow mixing"
assert gev.subject_anchor_words(e) == []
assert gev.chevron_flow_mixing_supported(e) is False

# F. Flow arrows around an unrelated machine/engine remain rejected.
f = deepcopy(SCENE4)
f["keyword"] = "machine engine chevron flow mixing"
assert "aircraft" not in gev.subject_anchor_words(f)
assert gev.chevron_flow_mixing_supported(f) is False

# G. No trusted grounding provenance means fail closed.
g = deepcopy(SCENE4)
g.pop("_canonical_visual_supply")
assert gev.trusted_grounding_present(g) is False
assert gev.chevron_flow_mixing_supported(g) is False
assert vx.plan_explanation(g) is None

# H. An explicit different owner can never use this template.
h = deepcopy(SCENE4)
h["owned_claim_id"] = "flow_interface"
assert gev.chevron_flow_mixing_supported(h) is False
assert vx.plan_explanation(h) is None

# I. Scene-5 result leakage makes the Scene-4 template ineligible.
for leaked in (
    "톱니 모양 셰브론은 흐름을 섞어 소음을 줄입니다.",
    "Chevron flow mixing improves fuel efficiency.",
    "Chevron flow mixing improves thrust performance.",
):
    item = deepcopy(SCENE4)
    item["text"] = leaked
    assert gev.chevron_flow_mixing_supported(item) is False, leaked
    assert vx.plan_explanation(item) is None, leaked

# Runtime form does not expose owned_claim_id; the deterministic grounded keyword
# plus post-Script trusted canonical supply is the equivalent trusted owner proof.
runtime_scene4 = deepcopy(SCENE4)
runtime_scene4.pop("owned_claim_id")
assert gev.chevron_flow_mixing_supported(runtime_scene4) is True
runtime_plan = vx.plan_explanation(runtime_scene4)
assert runtime_plan and runtime_plan.get("owned_claim_id") == "chevron_flow_mixing"

# Generate without calling a renderer/model; metadata must prove the complete
# deterministic nucleus and must not introduce the Scene-5 claim.
original_render = vx._render_clip
original_cached = vx._cached_verified_asset
try:
    vx._render_clip = lambda base_image, output_path, duration, plan: Path(output_path).write_bytes(b"deterministic")
    vx._cached_verified_asset = lambda scene: (None, None)
    vx.reset_visual_explanation_budget()
    result4 = vx.generate_visual_explanation_fallback(
        runtime_scene4,
        output_path=ROOT / "mock-chevron-flow-mixing.mp4",
        duration=4.0,
        trigger_reason="run_33257939720_regression",
    )
    assert result4 is not None, result4
    assert result4.get("mode") == "EXPLANATORY_2D", result4
    assert result4.get("template_type") == "CHEVRON_FLOW_MIXING", result4
    assert result4.get("required_subject_anchors") == ["aircraft", "engine", "chevron"], result4
    assert result4.get("anchor_matched") == result4.get("anchor_total") == 3, result4
    assert result4.get("required_explanatory_groups") == ["flow", "mixing"], result4
    assert result4.get("visible_explanatory_groups") == ["flow", "mixing"], result4
    assert result4.get("explanatory_anchor_matched") == result4.get("explanatory_anchor_total") == 2, result4
    assert result4.get("owned_claim_id") == "chevron_flow_mixing", result4
    assert result4.get("forbidden_claim_ids") == ["noise_reduction"], result4
    assert result4.get("additional_llm_calls") == 0, result4
    assert result4.get("additional_vision_calls") == 0, result4
finally:
    vx._render_clip = original_render
    vx._cached_verified_asset = original_cached
    (ROOT / "mock-chevron-flow-mixing.mp4").unlink(missing_ok=True)

# J. #257 FLOW_INTERFACE behavior remains intact.
assert gev.required_explanatory_groups(SCENE3) == ["flow", "interface"]
plan3 = vx.plan_explanation(SCENE3)
assert plan3 and plan3.get("template") == "FLOW_INTERFACE", plan3
assert plan3.get("required_subject_anchors") == ["aircraft", "engine"], plan3
assert plan3.get("required_explanatory_groups") == ["flow", "interface"], plan3
assert vx.annotation_fact_safe(SCENE3, plan3) is True

# K. Scene 5 remains owned by noise_reduction and never maps to Scene-4 template.
assert gev.required_explanatory_groups(SCENE5) == ["noise", "reduction"]
assert gev.chevron_flow_mixing_supported(SCENE5) is False
assert vx.plan_explanation(SCENE5) is None

# L. #254 stock semantics remain strict for the exact Run 33257939720 examples.
strengthened(
    SCENE4["keyword"], narration=SCENE4["text"], goal=SCENE4["visual_goal"]
)
flow_only = candidate(57901, "aircraft jet engine chevron serrated exhaust airflow plume")
tier, _ = vd.general_scene_unknown_safe_tier(flow_only, "airplane engine chevron detail")
assert tier >= 5, tier
missing_chevron = candidate(57902, "aircraft jet engine exhaust airflow mixing blend")
tier, _ = vd.general_scene_unknown_safe_tier(missing_chevron, "airplane engine chevron detail")
assert tier >= 5, tier
generic_chevron = candidate(57903, "aircraft jet engine nacelle nozzle chevron serrated closeup")
tier, _ = vd.general_scene_unknown_safe_tier(generic_chevron, "airplane engine chevron detail")
assert tier >= 5, tier
complete = candidate(57904, "aircraft jet engine nacelle nozzle chevron serrated exhaust airflow mixing blend")
tier, label = vd.general_scene_unknown_safe_tier(complete, "airplane engine chevron detail")
assert tier < 5, (tier, label)

print("RUN 33257939720 CHEVRON_FLOW_MIXING VISUAL SUPPLY REGRESSION: PASS")
