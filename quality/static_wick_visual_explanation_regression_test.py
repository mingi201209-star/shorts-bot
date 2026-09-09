from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
hotfix = (ROOT / "ci_static_wick_visual_explanation_hotfix.py").read_text(encoding="utf-8")
handoff = (ROOT / "ci_static_wick_local_visual_handoff_hotfix.py").read_text(encoding="utf-8")
late = (ROOT / "ci_run_33981204957_flap_director_repair_hotfix.py").read_text(encoding="utf-8")

for claim, template in (
    ("static_charge_dissipation", "STATIC_WICK_DISCHARGE"),
    ("static_wick_location_identity", "STATIC_WICK_LOCATION"),
    ("radio_interference_reduction", "STATIC_WICK_RF_RESULT"),
):
    assert claim in hotfix, claim
    assert template in hotfix, template

assert "is_static_wick_explanation_scene(item)" in hotfix
assert "trusted_static_wick_explanation" in hotfix
assert "generic_stock_fail_close" in hotfix
assert "generate_visual_explanation_fallback" in hotfix
assert "source_asset_id" in hotfix
assert "protected_region" in hotfix

# Run 34339557592 proved that generating the deterministic explanation is not
# sufficient: the common download/prepare path can overwrite vertical_video_path
# before load_video_for_scene sees it. The bounded static-wick handoff must
# preserve the already-rendered local asset and leave unrelated scenes on the
# original download/vertical-preparation path.
assert "STATIC_WICK_LOCAL_VISUAL_HANDOFF_V1" in handoff
assert "is_static_wick_explanation_scene(item)" in handoff
assert "video_url == vertical_video_path" in handoff
assert "os.path.exists(vertical_video_path)" in handoff
assert "[STATIC_WICK_LOCAL_HANDOFF]" in handoff
assert "else:" in handoff
assert "download_video(" in handoff
assert "prepare_vertical_video(" in handoff
assert handoff.index("if _static_wick_local_visual_ready:") < handoff.index("download_video(")

# Exact trusted facts may fail closed against generic stock, but unrelated
# visual selection must delegate to the previous selector unchanged.
assert "return _static_wick_previous_choose_best_candidate(" in hotfix
assert "subject_filter_query=subject_filter_query" in hotfix

# The repair must not buy its way through Director or generation safeguards.
for source in (hotfix, handoff):
    for forbidden in (
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "MAX_TOPIC_REGENERATIONS =",
        "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO =",
        "DIRECTOR_THRESHOLD =",
        "explanatory_power_min =",
    ):
        assert forbidden not in source, forbidden

# Production wiring uses the already-proven late final-composition hook and
# installs the handoff only after the static-wick visual repair itself.
assert "ci_static_wick_visual_explanation_hotfix" in late
assert "_patch_static_wick_visual()" in late
assert "ci_static_wick_local_visual_handoff_hotfix" in late
assert "_patch_static_wick_local_handoff()" in late
assert late.index("_patch_static_wick_visual()") < late.index("_patch_static_wick_local_handoff()")

print("STATIC_WICK_VISUAL_EXPLANATION_REGRESSION_PASS")
