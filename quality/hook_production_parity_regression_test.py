from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HOTFIXES = (
    "ci_hotfix.py",
    "ci_novelty_budget_hotfix.py",
    "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py",
    "ci_first5_retention_tts_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py",
    "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py",
    "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py",
    "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py",
)

for hotfix in HOTFIXES:
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual as hv
from video import hook_visual_dominance as hvd
from video import video_downloader as vd

legacy = sg._LEGACY


def candidate(source_id, slug, *, title=None, tags=None, position=1):
    return {
        "id": source_id,
        "source_id": source_id,
        "provider": "pexels",
        "url": f"https://cdn.example.test/{source_id}.mp4",
        "page_url": f"https://www.pexels.com/video/{slug}-{source_id}/",
        "title": title or slug.replace("-", " "),
        "tags": tags or slug.replace("-", " "),
        "search_position": position,
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
    }


scene = {
    "text": "비행기 창문이 둥근 데는 이유가 있다.",
    "keyword": "airplane window rounded corner",
    "visual_goal": "aircraft window rounded detail close-up",
    "hook_experiment": {"selected": True},
}

wing = candidate(
    101,
    "airplane-window-view-wing-clouds",
    title="airplane window view wing clouds",
    tags="airplane window view wing clouds",
    position=1,
)
window = candidate(
    102,
    "aircraft-window-rounded-detail-close-up",
    title="aircraft window rounded detail close up",
    tags="aircraft airplane window rounded detail",
    position=2,
)

original_search = hv.search_video_candidates
original_dominance = hv.evaluate_hook_subject_dominance


def dominance(candidate_item, scene_item):
    visible = ["aircraft"] if candidate_item["id"] == 101 else ["aircraft", "window"]
    return {
        "pass": True,
        "target_subject": "aircraft window",
        "subject_dominance": 9.0,
        "action_match": 10.0,
        "competing_subject_risk": 1.0,
        "vertical_crop_subject_visible": True,
        "action_required": False,
        "visible_components": visible,
        "reason": "production-like mocked frame observation",
        "frame_times": [0.0, 0.5, 1.5, 2.5],
    }

try:
    # CASE A/B: metadata says window for both, but actual visual FALSE cannot beat TRUE.
    hv.search_video_candidates = lambda *args, **kwargs: [wing, window]
    hv.evaluate_hook_subject_dominance = dominance
    selected_url = hv.fetch_hook_pexels_video(scene)
    trace = hv.get_last_hook_selection()
    assert selected_url == window["url"], trace
    assert trace["candidate_id"] == "pexels:102", trace
    assert trace["selection_mode"] == "DIRECT_VERIFIED", trace
    assert trace["visual_evidence"] == "TRUE", trace
    assert trace["visible_components"] == ["aircraft", "window"], trace

    # CASE D: identity/provenance survives selection to the exact render contract helper.
    render = hv.hook_render_contract(
        trace, render_start=0.0, render_duration=3.2, final_url=selected_url
    )
    assert render["render_contract_valid"] is True, render
    assert render["candidate_id"] == trace["candidate_id"], render
    assert render["provenance"] == "hook_dominance_vision", render
    assert render["vision_segment"]["start"] == render["render_segment"]["start"] == 0.0, render

    # CASE E: verified evidence cannot remain verified across a temporal-start mismatch.
    mismatch = hv.hook_render_contract(
        trace, render_start=3.0, render_duration=3.2, final_url=selected_url
    )
    assert mismatch["render_contract_valid"] is False, mismatch
    assert mismatch["contract_violation"] is True, mismatch
    assert mismatch["selection_mode"] == "UNVERIFIED_CONTEXTUAL_FALLBACK", mismatch

    # CASE C/F: strict failure cannot re-enter DIRECT_VERIFIED through fallback.
    hv.search_video_candidates = lambda *args, **kwargs: [wing]
    fallback_url = hv.fetch_hook_pexels_video(scene)
    fallback_trace = hv.get_last_hook_selection()
    assert fallback_url == wing["url"], fallback_trace
    assert fallback_trace["candidate_id"] == "pexels:101", fallback_trace
    assert fallback_trace["visual_evidence"] == "FALSE", fallback_trace
    assert fallback_trace["selection_mode"] == "UNVERIFIED_CONTEXTUAL_FALLBACK", fallback_trace
    fallback_render = hv.hook_render_contract(
        fallback_trace, render_start=0.0, render_duration=3.2, final_url=fallback_url
    )
    assert fallback_render["render_contract_valid"] is True, fallback_render
    assert fallback_render["selection_mode"] == "UNVERIFIED_CONTEXTUAL_FALLBACK", fallback_render

    # CASE G: a false/unknown DIRECT_VERIFIED state is a render-contract violation.
    forged = dict(fallback_trace)
    forged["selection_mode"] = "DIRECT_VERIFIED"
    forged["vision_segment"] = {"start": 0.0, "end": 2.7}
    forged_result = hv.hook_render_contract(
        forged, render_start=0.0, render_duration=3.2, final_url=fallback_url
    )
    assert forged_result["render_contract_valid"] is False, forged_result
    assert forged_result["contract_violation"] is True, forged_result

finally:
    hv.search_video_candidates = original_search
    hv.evaluate_hook_subject_dominance = original_dominance

# H: #20 declarative Hook, visibility and direct semantic-match behavior remains.
assert he._output_quality_is_declarative_hook("비행기 창문에는 작은 구멍이 있다.")
assert not he._output_quality_is_declarative_hook("비행기 창문 구멍은 뭘까요?")
assert hvd.HOOK_SUBJECT_VISIBILITY_MIN == 8.0
assert vd.current_narration_semantic_match(
    {"title": "airplane window condensation layers", "tags": "airplane window layers"},
    "airplane window condensation layers",
) > vd.current_narration_semantic_match(
    {"title": "airplane cockpit", "tags": "airplane cockpit pilot"},
    "airplane window condensation layers",
)

# I: #21 answer leakage and valid clue progression remain behaviorally enforced.
locked = {
    "reveal": "작은 구멍은 창문 사이 압력을 단계적으로 조절한다",
    "payoff": "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다",
}
leak = {
    "_candidate_retention": locked,
    "scenes": [{"text": text} for text in (
        "비행기 창문에는 작은 구멍이 있다.",
        "작은 구멍은 창문 사이 압력을 단계적으로 조절한다.",
        "창문은 여러 겹이다.",
        "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
    )],
}
ok, reason = legacy.validate_curiosity_retention(leak)
assert not ok and "answer leakage" in reason

progression = {
    "_candidate_retention": locked,
    "scenes": [{"text": text} for text in (
        "비행기 창문에는 작은 구멍이 있다.",
        "이 구멍은 바깥 공기를 들이는 통로가 아니다.",
        "비행기 창문은 한 장이 아니라 여러 겹이다.",
        "고도가 올라가면 안팎의 압력 차이가 커진다.",
        "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
    )],
}
ok, reason = legacy.validate_curiosity_retention(progression)
assert ok, reason

# J/K/L/M/N: #22-#26 layered behavior remains intact.
assert vd.visual_specificity_decision(window, scene["keyword"])["level"] <= 3 or vd.visual_specificity_decision(window, scene["keyword"])["visual_evidence_state"] == "UNKNOWN"
assert legacy.design_causality_preference_score([
    {"text": "높은 고도에서는 압력 차이가 커집니다."},
    {"text": "창문 구조가 이 차이를 견뎌야 합니다."},
    {"text": "그래서 여러 겹 구조를 사용합니다."},
    {"text": "작은 구멍이 판 사이 압력을 조절합니다."},
    {"text": "그 결과 하중 경로가 유지됩니다."},
]) > legacy.design_causality_preference_score([
    {"text": "압력에 도움이 됩니다."},
    {"text": "안전에도 도움이 됩니다."},
    {"text": "또 다른 역할도 합니다."},
])
assert vd.extract_query_anchors(scene["keyword"]) == ["aircraft", "window"]
assert vd.concrete_visual_evidence(wing, scene["keyword"])["complete"] is True
vd.register_visual_evidence(wing, visible_components=["aircraft"], source="regression_frame", definitive=True)
assert vd.candidate_visible_component_evidence(wing, scene["keyword"])["state"] == "FALSE"

# O/P: provider isolation remains bidirectional.
original_pexels = vd.search_pexels_candidates
original_pixabay = vd.search_pixabay_candidates
original_key = vd.PIXABAY_API_KEY
try:
    def fail(*args, **kwargs):
        raise RuntimeError("simulated provider failure")

    def healthy_pixabay(*args, **kwargs):
        return [{
            "id": 501,
            "provider": "pixabay",
            "source_id": 501,
            "url": "https://cdn.example.test/pixabay501.mp4",
            "download_url": "https://cdn.example.test/pixabay501.mp4",
            "source_url": "https://pixabay.com/videos/501/",
            "title": "airplane window",
            "tags": "airplane window",
            "search_position": 1,
            "width": 1080,
            "height": 1920,
            "duration": 8,
        }]

    def healthy_pexels(*args, **kwargs):
        return [{
            "id": 502,
            "url": "https://cdn.example.test/pexels502.mp4",
            "page_url": "https://pexels.com/video/airplane-window-502/",
            "search_position": 1,
        }]

    vd.PIXABAY_API_KEY = "regression-key"
    vd.search_pexels_candidates = fail
    vd.search_pixabay_candidates = healthy_pixabay
    pool = vd.search_video_candidates("airplane window", per_page=3)
    assert len(pool) == 1 and pool[0].get("provider") == "pixabay"

    vd.search_pexels_candidates = healthy_pexels
    vd.search_pixabay_candidates = fail
    pool = vd.search_video_candidates("airplane window", per_page=3)
    assert len(pool) == 1 and pool[0].get("provider") == "pexels"
finally:
    vd.search_pexels_candidates = original_pexels
    vd.search_pixabay_candidates = original_pixabay
    vd.PIXABAY_API_KEY = original_key

print("PASS: production-path Hook parity A-G, #20-#26 H-N, provider isolation O-P")
