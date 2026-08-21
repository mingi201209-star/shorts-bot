from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for hotfix in (
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
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual as hv
from video import hook_visual_dominance as hvd
from video import video_downloader as vd
legacy = sg._LEGACY


def candidate(source_id, title, tags, position=1):
    return {
        "id": source_id,
        "provider": "pixabay",
        "source_id": source_id,
        "url": f"https://cdn.example.test/{source_id}.mp4",
        "download_url": f"https://cdn.example.test/{source_id}.mp4",
        "source_url": f"https://example.test/video/{source_id}",
        "title": title,
        "tags": tags,
        "search_position": position,
        "width": 1080,
        "height": 1920,
        "duration": 8,
    }


def reset_reuse_state():
    vd.USED_VIDEO_IDS.clear()
    vd._SAFE_REUSE_HISTORY.clear()
    vd._SAFE_REUSE_COUNTS.clear()
    vd._LAST_SAFE_REUSE_OFFSET = 0.0


query = "airplane window rounded corner"
wing = candidate(1, "airplane wing above clouds", "aircraft wing clouds", 1)
decorative = candidate(2, "decorative arched window", "window architecture decorative", 2)
cabin = candidate(3, "aircraft cabin passenger windows", "airplane cabin visible windows", 3)
detail = candidate(4, "aircraft window rounded detail", "airplane window rounded corner closeup", 4)

# CASE A: full concrete evidence outranks partial-domain/context candidates.
reset_reuse_state()
ranked = []
remaining = [wing, decorative, cabin, detail]
for _ in range(4):
    selected = vd.choose_best_candidate(remaining, subject_filter_query=query)
    ranked.append(selected["source_id"])
    remaining = [item for item in remaining if item["source_id"] != selected["source_id"]]
assert ranked == [4, 3, 1, 2], ranked

# CASE B: Hook generic wing cannot satisfy direct visual evidence when a visible window exists.
wing_scores, wing_total = hv._score_candidate(wing, {"keyword": query, "visual_goal": "aircraft window detail"})
detail_scores, detail_total = hv._score_candidate(detail, {"keyword": query, "visual_goal": "aircraft window detail"})
assert wing_scores["semantic_match"] <= 4.0
assert wing_scores["subject_visibility"] <= 4.0
assert not hv._passes_strict_gate({"scores": wing_scores, "total_score": wing_total})
assert detail_total > wing_total

# CASE C/D: one half of AIRCRAFT + WINDOW is insufficient for direct/close tier.
wing_evidence = vd.concrete_visual_evidence(wing, query)
window_evidence = vd.concrete_visual_evidence(decorative, query)
assert wing_evidence["detected"] == ["aircraft"]
assert window_evidence["detected"] == ["window"]
assert vd.visual_specificity_decision(wing, query)["level"] >= 4
assert vd.visual_specificity_decision(decorative, query)["level"] >= 4

# CASE E: fully relevant reuse beats unrelated filler under concrete scarcity.
reset_reuse_state()
vd._mark_candidate_used(detail)
unrelated = [
    candidate(10, "restaurant dining room", "restaurant people interior", 1),
    candidate(11, "fire smoke", "fire smoke flames", 2),
    candidate(12, "sunset sun", "sun nature sky", 3),
]
reused = vd.choose_best_candidate(unrelated, subject_filter_query=query)
assert reused.get("_safe_reuse") is True
assert reused["source_id"] == detail["source_id"]
vd._mark_candidate_used(reused)
assert vd.get_last_safe_reuse_offset() > 0.0

# CASE F: safe reuse is bounded and cannot repeat indefinitely.
second = vd.choose_best_candidate(unrelated, subject_filter_query=query)
assert second.get("_safe_reuse") is True
vd._mark_candidate_used(second)
third = vd.choose_best_candidate(unrelated, subject_filter_query=query)
assert not third.get("_safe_reuse", False)
assert vd._SAFE_REUSE_COUNTS[vd._safe_reuse_key(detail)] == vd._SAFE_REUSE_MAX

# CASE G: no exact/window evidence still permits same-domain contextual fallback.
reset_reuse_state()
generic_airplane = candidate(20, "airplane exterior in flight", "aircraft airplane flight", 1)
selected = vd.choose_best_candidate([generic_airplane], subject_filter_query=query)
assert selected is not None and selected["source_id"] == 20
assert vd.visual_specificity_decision(selected, query)["level"] == 4

# CASE H: #20 contracts remain active.
assert he._output_quality_is_declarative_hook("비행기 창문에는 작은 구멍이 있다.")
assert not he._output_quality_is_declarative_hook("비행기 창문 구멍은 뭘까요?")
assert hvd.HOOK_SUBJECT_VISIBILITY_MIN == 8.0
assert vd.current_narration_semantic_match(
    {"title": "airplane window condensation layers", "tags": "window condensation layers"},
    "airplane window condensation layers",
) > vd.current_narration_semantic_match(
    {"title": "airplane cockpit", "tags": "airplane cockpit pilot"},
    "airplane window condensation layers",
)
assert legacy.detect_information_density_issue([
    {"text": "압력 차이는 창문 여러 겹에 나뉘어 전달됩니다."},
    {"text": "압력 차이는 창문 여러 겹에 나뉘어 전달됩니다."},
]) is not None

# CASE I: #21 Curiosity Retention remains active.
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

# CASE J: #22 Visual Specificity still prefers the direct component.
assert vd.visual_specificity_decision(detail, query)["level"] < vd.visual_specificity_decision(wing, query)["level"]

# CASE K: #23 Design Causality still prefers causal explanation.
feature_list = [
    {"text": "압력 조절에 도움이 됩니다."},
    {"text": "결로에도 도움이 됩니다."},
    {"text": "안전에도 도움이 됩니다."},
]
causal = [
    {"text": "높은 고도에서는 기내와 외부 압력 차이가 커집니다."},
    {"text": "창문 구조가 이 압력 차이를 견뎌야 합니다."},
    {"text": "그래서 여러 겹의 창문 구조를 사용합니다."},
    {"text": "작은 구멍이 판 사이 압력을 조절합니다."},
    {"text": "그 결과 압력 하중 경로가 유지됩니다."},
]
assert legacy.design_causality_preference_score(causal) > legacy.design_causality_preference_score(feature_list)

# CASE L: #24 compound anchors and query relaxation stay intact.
assert vd.extract_query_anchors(query) == ["aircraft", "window"]
ladder = vd.query_relaxation_ladder(query)
assert ladder
for relaxed in ladder:
    anchors = vd.extract_query_anchors(relaxed)
    assert anchors == ["aircraft", "window"], (relaxed, anchors)
assert vd.candidate_anchor_compatibility(detail, query)["compatible"] is True
assert vd.candidate_anchor_compatibility(wing, query)["compatible"] is False

# CASE M: provider isolation remains bidirectional.
original_pexels = vd.search_pexels_candidates
original_pixabay = vd.search_pixabay_candidates
original_key = vd.PIXABAY_API_KEY
try:
    def fail(*args, **kwargs):
        raise RuntimeError("simulated provider failure")

    def healthy_pixabay(*args, **kwargs):
        return [candidate(77, "airplane window", "airplane window detail")]

    def healthy_pexels(*args, **kwargs):
        return [{
            "id": 88,
            "url": "https://cdn.example.test/88.mp4",
            "page_url": "https://pexels.com/video/airplane-window-88/",
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

print("PASS: concrete evidence A-D, bounded safe reuse E-F, scarcity G, #20-#24 H-L, provider isolation M")
