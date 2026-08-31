"""Run 33367370350 deterministic explanatory asset lineage regression.

Zero network/model calls. Reproduces the LIVE false hard-repeat where three
semantically distinct deterministic explanatory renders shared the legacy
`deterministic-winglet-template-v1` source_asset_id.
"""
from copy import deepcopy
import inspect
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Compose the established #257/#258/#266 explanatory visual architecture.
runpy.run_path(str(ROOT / "quality/run_33248013901_visual_anchor_regression_test.py"))

import ci_canonical_visual_supply_contract_hotfix as canonical_supply  # noqa: E402
canonical_supply.main()
import ci_still_image_verifier_contract_hotfix as still_verifier  # noqa: E402
still_verifier.main()
import ci_noise_reduction_result_visual_hotfix as noise_supply  # noqa: E402
noise_supply.main()

from quality import visual_diversity_preflight as diversity  # noqa: E402
from video import visual_explanation as vx  # noqa: E402

TRUSTED_SUPPLY = {
    "canonical_subject": "jet engine nacelle/nozzle chevrons",
    "identity_confidence": 0.98,
    "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
    "grounding_source": "trusted-run-33367370350-fixture",
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

EXPECTED_TEMPLATES = ["FLOW_INTERFACE", "CHEVRON_FLOW_MIXING", "NOISE_REDUCTION_RESULT"]
plans = [vx.plan_explanation(scene) for scene in (SCENE3, SCENE4, SCENE5)]
assert [plan.get("template") for plan in plans] == EXPECTED_TEMPLATES, plans
assert all(vx.annotation_fact_safe(scene, plan) for scene, plan in zip((SCENE3, SCENE4, SCENE5), plans))

# A. Exact Run 33367370350 counterexample: different deterministic renders must
# have different stable asset identities, and Visual Diversity must PASS.
original_render = vx._render_clip
original_cached = vx._cached_verified_asset
outputs = [ROOT / f"mock-run-33367370350-{n}.mp4" for n in (3, 4, 5)]
try:
    vx._render_clip = lambda base_image, output_path, duration, plan: Path(output_path).write_bytes(b"deterministic")
    vx._cached_verified_asset = lambda scene: (None, None)
    vx.reset_visual_explanation_budget()
    results = [
        vx.generate_visual_explanation_fallback(
            scene,
            output_path=output,
            duration=4.0,
            trigger_reason="run_33367370350_regression",
        )
        for scene, output in zip((SCENE3, SCENE4, SCENE5), outputs)
    ]
finally:
    vx._render_clip = original_render
    vx._cached_verified_asset = original_cached
    for output in outputs:
        output.unlink(missing_ok=True)

assert all(results), results
assert [result.get("template_type") for result in results] == EXPECTED_TEMPLATES
asset_ids = [result.get("source_asset_id") for result in results]
assert len(set(asset_ids)) == 3, asset_ids
assert all(value.startswith("deterministic-explanatory:") for value in asset_ids), asset_ids
assert "deterministic-winglet-template-v1" not in asset_ids
assert len({result.get("source_id") for result in results}) == 3, results

scenes_exact = [
    {"role": "setup", "text": "scene 1"},
    {"role": "setup", "text": "scene 2"},
    SCENE3,
    SCENE4,
    SCENE5,
]
lineage_exact = []
for scene_index, result in zip((2, 3, 4), results):
    lineage_exact.append({
        "scene_index": scene_index,
        "mode": result["mode"],
        "provider": result["provider"],
        "source_id": result["source_id"],
        "source_asset_id": result["source_asset_id"],
        "template_type": result["template_type"],
    })
exact = diversity.evaluate_visual_diversity(scenes_exact, lineage_exact)
assert exact["pass"] is True, exact
assert exact["hard_repeat_count"] == 3, exact


def assert_same_asset_repeat_detected(scene, result, label):
    repeated_scenes = [deepcopy(scene), deepcopy(scene), deepcopy(scene)]
    lineage = []
    # E: source_id changes cannot bypass a shared underlying asset identity.
    for idx in range(3):
        lineage.append({
            "scene_index": idx,
            "mode": result["mode"],
            "provider": result["provider"],
            "source_id": f"{result['source_id']}-instance-{idx}",
            "source_asset_id": result["source_asset_id"],
            "template_type": result["template_type"],
        })
    check = diversity.evaluate_visual_diversity(repeated_scenes, lineage)
    assert check["pass"] is False, (label, check)
    high = [g for g in check["repetition_groups"] if g.get("severity") == "high"]
    assert len(high) == 1, (label, check)
    assert high[0]["asset_id"] == result["source_asset_id"], (label, high)
    assert high[0]["hard_repeat_count"] == 3, (label, high)


# B/C/D. Every established deterministic template still detects true reuse.
for scene, result, label in zip((SCENE3, SCENE4, SCENE5), results, EXPECTED_TEMPLATES):
    assert_same_asset_repeat_detected(scene, result, label)

# F. Scene index is not part of deterministic asset identity.
for plan in plans:
    assert vx._deterministic_explanatory_asset_id(plan) == vx._deterministic_explanatory_asset_id(deepcopy(plan))

# G. Identity is deterministic provenance, not a random/nonce/time/scene key.
identity_source = inspect.getsource(vx._deterministic_explanatory_asset_id).lower()
for forbidden in ("uuid", "random", "time.time", "timestamp", "scene_index", "scene id", "scene_id"):
    assert forbidden not in identity_source, (forbidden, identity_source)

# H. Existing non-deterministic physical lineage semantics remain untouched.
assert vx._explanatory_asset_id("verified-still-asset-42", plans[0]) == "verified-still-asset-42"
assert diversity.physical_asset_identity({
    "physical_signature": "stock-file-sha256-abc",
    "source_asset_id": "stock-provider-id",
    "source_id": "stock-instance-id",
}) == "stock-file-sha256-abc"
assert diversity.physical_asset_identity({
    "source_asset_id": "reused-verified-asset-7",
    "source_id": "different-instance",
}) == "reused-verified-asset-7"
assert diversity.physical_asset_identity({
    "source_asset_id": "still-asset-9",
    "source_id": "still-instance-9",
}) == "still-asset-9"

# I. Hard-repeat threshold is unchanged.
assert diversity.HARD_REPEAT_COUNT == 3, diversity.HARD_REPEAT_COUNT

# J. Existing capability-exhausted policy is unchanged: a true 3x raw repeat
# with zero repair allowance still fails closed and marks exhausted.
raw_scenes = [
    {"role": "mechanism", "text": "same physical asset beat a"},
    {"role": "mechanism", "text": "same physical asset beat b"},
    {"role": "mechanism", "text": "same physical asset beat c"},
]
raw_lineage = [
    {
        "scene_index": idx,
        "mode": "RAW_STOCK",
        "provider": "stock",
        "source_id": f"raw-instance-{idx}",
        "source_asset_id": "same-raw-physical-asset",
    }
    for idx in range(3)
]
raw_result = diversity.evaluate_visual_diversity(raw_scenes, raw_lineage)
assert raw_result["pass"] is False, raw_result
assert diversity.plan_bounded_diversity_repair(raw_result, raw_scenes, max_repairs=0) == []
assert raw_result["capability_exhausted"] is True, raw_result

print("RUN 33367370350 DETERMINISTIC EXPLANATORY ASSET LINEAGE REGRESSION: PASS")
