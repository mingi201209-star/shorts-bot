from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageChops


def assert_script_floor():
    from content import script_generator as sg

    bad = [
        {"text": "비행기 창문 모서리는 둥글게 되어 있습니다."},
        {"text": "그런데 비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?"},
    ]
    issue = sg._hq_opening_repeat_issue(bad)
    assert issue, "Run 34616204901 opening repetition must be rejected"

    good = [
        {"text": "비행기 창문은 네모가 아니라 모서리가 둥근 형태입니다."},
        {"text": "그 곡선은 동체에 걸리는 응력이 한곳에 몰리는 것을 줄입니다."},
    ]
    assert sg._hq_opening_repeat_issue(good) is None


def assert_window_stock_floor():
    from video import video_downloader as vd

    vd.extract_query_anchors = lambda query: (
        ["aircraft", "window"] if "window" in str(query).lower()
        else ["aircraft", "wing"]
    )
    vd._hq_previous_general_scene_unknown_safe_tier = lambda candidate, query: (4, "SAME_DOMAIN_CONTEXTUAL_UNKNOWN")
    vd.candidate_visible_component_evidence = lambda candidate, query: {"state": "UNKNOWN"}

    tier, label = vd.general_scene_unknown_safe_tier({}, "aircraft passenger window rounded corner")
    assert tier == 5
    assert label == "WINDOW_SUBJECT_REQUIRES_VISIBLE_PROOF"

    tier, label = vd.general_scene_unknown_safe_tier({}, "aircraft wing")
    assert (tier, label) == (4, "SAME_DOMAIN_CONTEXTUAL_UNKNOWN"), "non-window behavior must remain unchanged"

    vd._hq_previous_general_scene_unknown_safe_tier = lambda candidate, query: (1, "VISUALLY_VERIFIED_DIRECT")
    vd.candidate_visible_component_evidence = lambda candidate, query: {"state": "TRUE"}
    assert vd.general_scene_unknown_safe_tier({}, "aircraft passenger window") == (1, "VISUALLY_VERIFIED_DIRECT")


def _render_claim(ve, claim_id):
    profile = ve._hq_window_profile_for_claim(claim_id)
    assert profile, claim_id
    plan = {
        "template": "AIRCRAFT_WINDOW_STRESS_V1",
        "owned_claim_id": claim_id,
        "label": profile["label"],
        "active_side": profile["active"],
    }
    frame = Image.new("RGB", (ve.VIDEO_WIDTH, ve.VIDEO_HEIGHT), (0, 0, 0))
    return ve._draw_concept_panel(frame, plan, 0.55)


def assert_guided_comparison_render():
    from video import visual_explanation as ve

    claims = [
        "squarish_window_stress_concentration",
        "rounded_window_stress_distribution",
        "squarish_window_fatigue_rupture",
    ]
    profiles = [ve._hq_window_profile_for_claim(claim) for claim in claims]
    assert [item["active"] for item in profiles] == ["LEFT", "RIGHT", "LEFT"]
    assert len({item["action"] for item in profiles}) == 3
    assert len({item["label"] for item in profiles}) == 3

    frames = [_render_claim(ve, claim) for claim in claims]
    black = Image.new("RGB", (ve.VIDEO_WIDTH, ve.VIDEO_HEIGHT), (0, 0, 0))
    for frame in frames:
        bbox = ImageChops.difference(frame, black).getbbox()
        assert bbox is not None
        assert bbox[3] >= 1380, f"mobile explanation panel is still too small: bbox={bbox}"

    for left, right in zip(frames, frames[1:]):
        diff = ImageChops.difference(left, right)
        assert diff.getbbox() is not None, "owned claims must not render as the same visual state"
        changed = sum(1 for px in diff.convert("L").getdata() if px > 8)
        assert changed >= 25000, f"claim-specific presentations are not visually distinct enough: {changed}"


def assert_no_budget_relaxation():
    source = Path("ci_run_34616204901_human_quality_hotfix.py").read_text(encoding="utf-8")
    forbidden = (
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "MAX_TOPIC_REGENERATIONS =",
        "HOOK_MIN_SCORE =",
    )
    for marker in forbidden:
        assert marker not in source, f"quality hotfix must not relax budget/threshold: {marker}"


def main():
    assert_script_floor()
    assert_window_stock_floor()
    assert_guided_comparison_render()
    assert_no_budget_relaxation()
    print("PASS: Run 34616204901 Human Quality regression")


if __name__ == "__main__":
    main()
