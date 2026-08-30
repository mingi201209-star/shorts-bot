"""Run 33307762835 Scene 5 noise-reduction result visual supply regression.

Zero network/model calls. This reproduces the first LIVE supply gap after #265,
#257 and #258 passed: stock stays strict, still budget stays 2, and only the
trusted primary-result claim may use deterministic NOISE_REDUCTION_RESULT.
"""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_canonical_visual_supply_contract_hotfix as canonical_supply  # noqa: E402
canonical_supply.main()
import ci_still_image_verifier_contract_hotfix as still_verifier  # noqa: E402
still_verifier.main()
import ci_noise_reduction_result_visual_hotfix as noise_supply  # noqa: E402
noise_supply.main()

from video import grounded_explanatory_visual as gev  # noqa: E402
from video import still_image_fallback as still  # noqa: E402
from video import visual_explanation as vx  # noqa: E402

TRUSTED_SUPPLY = {
    "canonical_subject": "jet engine nacelle/nozzle chevrons",
    "identity_confidence": 0.98,
    "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
    "grounding_source": "trusted-run-33307762835-fixture",
}

SCENE5 = {
    "scene_id": 5,
    "role": "payoff",
    "causal_role": "primary_result",
    "owned_claim_id": "noise_reduction",
    "text": "이 혼합 변화의 대표적인 결과는 제트 엔진 소음 감소입니다.",
    "visual_goal": "소음 감소의 효과",
    "keyword": "jet engine noise reduction",
    "_canonical_visual_supply": dict(TRUSTED_SUPPLY),
}

SCENE3 = {
    "scene_id": 3,
    "role": "causal_clue",
    "owned_claim_id": "flow_interface",
    "text": "뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    "visual_goal": "두 흐름이 만나는 경계",
    "keyword": "jet engine flow interface",
    "_canonical_visual_supply": dict(TRUSTED_SUPPLY),
}

SCENE4 = {
    "scene_id": 4,
    "role": "reveal",
    "owned_claim_id": "chevron_flow_mixing",
    "text": "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    "visual_goal": "셰브론 주변의 흐름 혼합 변화",
    "keyword": "jet engine chevron flow mixing",
    "_canonical_visual_supply": dict(TRUSTED_SUPPLY),
}

assert still.STILL_IMAGE_MAX_PER_VIDEO == 2, still.STILL_IMAGE_MAX_PER_VIDEO

# A. Exact trusted primary result: engine subject + noise + qualitative reduction.
assert gev.subject_anchor_words(SCENE5) == ["aircraft", "engine"]
assert gev.required_explanatory_groups(SCENE5) == ["noise", "reduction"]
assert gev.noise_reduction_result_supported(SCENE5) is True
plan5 = vx.plan_explanation(SCENE5)
assert plan5 and plan5.get("template") == "NOISE_REDUCTION_RESULT", plan5
assert plan5.get("scene_role") == "result", plan5
assert plan5.get("owned_claim_id") == "noise_reduction", plan5
assert plan5.get("causal_role") == "primary_result", plan5
assert plan5.get("required_subject_anchors") == ["aircraft", "engine"], plan5
assert plan5.get("required_explanatory_groups") == ["noise", "reduction"], plan5
assert "chevron_flow_mixing" in plan5.get("forbidden_claim_ids", []), plan5
assert vx.annotation_fact_safe(SCENE5, plan5) is True

# Runtime equivalent: private claim id/causal role may be absent, but the locked
# payoff role + exact grounded keyword + trusted canonical profile remains enough.
runtime_scene5 = deepcopy(SCENE5)
runtime_scene5.pop("owned_claim_id")
runtime_scene5.pop("causal_role")
assert gev.noise_reduction_result_supported(runtime_scene5) is True
assert vx.plan_explanation(runtime_scene5).get("template") == "NOISE_REDUCTION_RESULT"

# B. Generic aircraft only.
b = deepcopy(SCENE5)
b["keyword"] = "aircraft exterior"
assert gev.noise_reduction_result_supported(b) is False
assert vx.plan_explanation(b) is None

# C. Engine only, no noise representation/relation.
c = deepcopy(SCENE5)
c["keyword"] = "jet engine detail"
assert gev.noise_reduction_result_supported(c) is False
assert vx.plan_explanation(c) is None

# D. Speaker/sound icon only; no engine subject.
d = deepcopy(SCENE5)
d["keyword"] = "speaker sound noise reduction"
assert "engine" not in gev.subject_anchor_words(d)
assert gev.noise_reduction_result_supported(d) is False
assert vx.plan_explanation(d) is None

# E. Noise present but no reduction relationship.
e = deepcopy(SCENE5)
e["keyword"] = "jet engine acoustic noise"
assert gev.required_explanatory_groups(e) == []
assert gev.noise_reduction_result_supported(e) is False

# F. Reduction relationship but no engine subject.
f = deepcopy(SCENE5)
f["keyword"] = "acoustic noise reduction"
assert gev.required_explanatory_groups(f) == ["noise", "reduction"]
assert gev.noise_reduction_result_supported(f) is False

# G. Invented quantitative dB claims are never eligible.
g = deepcopy(SCENE5)
g["text"] = "셰브론 적용 뒤 소음이 10 dB 감소합니다."
assert gev.noise_reduction_result_supported(g) is False
assert vx.plan_explanation(g) is None

# H. Unowned fuel/drag/stability/thrust/performance expansion stays closed.
for expansion in (
    "fuel efficiency", "drag reduction", "stability improvement",
    "thrust improvement", "performance improvement",
    "연료 효율", "항력 감소", "안정성 향상", "추력 향상", "성능 향상",
):
    h = deepcopy(SCENE5)
    h["text"] = f"제트 엔진 소음 감소와 {expansion} 결과입니다."
    assert gev.noise_reduction_result_supported(h) is False, expansion
    assert vx.plan_explanation(h) is None, expansion

# I. Scene 4 mixing mechanism cannot be re-owned/re-explained by Scene 5.
i = deepcopy(SCENE5)
i["text"] = "셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿔 소음을 줄입니다."
assert gev.noise_reduction_result_supported(i) is False
assert vx.plan_explanation(i) is None

wrong_role = deepcopy(SCENE5)
wrong_role["causal_role"] = "mechanism_change"
assert gev.noise_reduction_result_supported(wrong_role) is False

wrong_owner = deepcopy(SCENE5)
wrong_owner["owned_claim_id"] = "chevron_flow_mixing"
assert gev.noise_reduction_result_supported(wrong_owner) is False

no_grounding = deepcopy(SCENE5)
no_grounding.pop("_canonical_visual_supply")
assert gev.noise_reduction_result_supported(no_grounding) is False

# Generate zero-call local result metadata without invoking ffmpeg/PIL rendering.
original_render = vx._render_clip
original_cached = vx._cached_verified_asset
try:
    vx._render_clip = lambda base_image, output_path, duration, plan: Path(output_path).write_bytes(b"deterministic")
    vx._cached_verified_asset = lambda scene: (None, None)
    vx.reset_visual_explanation_budget()
    result5 = vx.generate_visual_explanation_fallback(
        runtime_scene5,
        output_path=ROOT / "mock-noise-reduction.mp4",
        duration=4.0,
        trigger_reason="run_33307762835_regression",
    )
    assert result5 is not None, result5
    assert result5.get("mode") == "EXPLANATORY_2D", result5
    assert result5.get("template_type") == "NOISE_REDUCTION_RESULT", result5
    assert result5.get("required_subject_anchors") == ["aircraft", "engine"], result5
    assert result5.get("anchor_matched") == result5.get("anchor_total") == 2, result5
    assert result5.get("required_explanatory_groups") == ["noise", "reduction"], result5
    assert result5.get("visible_explanatory_groups") == ["noise", "reduction"], result5
    assert result5.get("explanatory_anchor_matched") == result5.get("explanatory_anchor_total") == 2, result5
    assert result5.get("owned_claim_id") == "noise_reduction", result5
    assert "chevron_flow_mixing" in result5.get("forbidden_claim_ids", []), result5
    assert result5.get("additional_llm_calls") == 0, result5
    assert result5.get("additional_vision_calls") == 0, result5
finally:
    vx._render_clip = original_render
    vx._cached_verified_asset = original_cached
    (ROOT / "mock-noise-reduction.mp4").unlink(missing_ok=True)

# J. #257 FLOW_INTERFACE remains unchanged.
plan3 = vx.plan_explanation(SCENE3)
assert plan3 and plan3.get("template") == "FLOW_INTERFACE", plan3
assert vx.annotation_fact_safe(SCENE3, plan3) is True

# K. #258 CHEVRON_FLOW_MIXING remains unchanged and still forbids Scene 5 result.
plan4 = vx.plan_explanation(SCENE4)
assert plan4 and plan4.get("template") == "CHEVRON_FLOW_MIXING", plan4
assert plan4.get("owned_claim_id") == "chevron_flow_mixing", plan4
assert plan4.get("forbidden_claim_ids") == ["noise_reduction"], plan4
assert vx.annotation_fact_safe(SCENE4, plan4) is True

# Template source itself contains no invented numeric dB claim and does not draw
# any Scene-4 flow/mixing mechanism arrows for this result-only branch.
hotfix_source = (ROOT / "ci_noise_reduction_result_visual_hotfix.py").read_text(encoding="utf-8")
assert "10 dB" not in hotfix_source and "20 dB" not in hotfix_source
assert "NOISE_REDUCTION_RESULT" in hotfix_source
assert "additional_llm_calls" not in hotfix_source  # inherited metadata stays zero

print("RUN 33307762835 NOISE_REDUCTION_RESULT VISUAL SUPPLY REGRESSION: PASS")
