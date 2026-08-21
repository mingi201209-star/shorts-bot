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
    "ci_visible_evidence_provenance_hotfix.py",
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
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


def reset_state():
    vd.USED_VIDEO_IDS.clear()
    vd._SAFE_REUSE_HISTORY.clear()
    vd._SAFE_REUSE_COUNTS.clear()
    vd._VISUAL_EVIDENCE_REGISTRY.clear()
    vd._LAST_SAFE_REUSE_OFFSET = 0.0


query = "airplane window rounded corner"
wing_view = candidate(1, "airplane window view wing clouds", "aircraft window seat wing clouds", 1)
detail = candidate(2, "aircraft window rounded close up", "airplane window rounded frame detail", 2)
weak_metadata_visible = candidate(3, "travel interior detail", "passenger view", 3)
underwater = candidate(4, "underwater fish swimming", "ocean fish blue water", 4)
generic_airplane = candidate(5, "airplane exterior flight", "aircraft airplane sky", 5)

# CASE A: semantic WINDOW context cannot become WINDOW_VISIBLE when the frame signal says otherwise.
reset_state()
vd.register_visual_evidence(wing_view, visible_components=["aircraft"], source="hook_dominance_vision")
visual = vd.candidate_visible_component_evidence(wing_view, query)
assert visual["state"] == "FALSE", visual
assert visual["source"] == "hook_dominance_vision"
assert "window" not in visual["visible"]
assert vd.visual_specificity_decision(wing_view, query)["level"] >= 4

# CASE B: actual aircraft + window frame evidence permits concrete completeness.
vd.register_visual_evidence(detail, visible_components=["aircraft", "window"], source="hook_dominance_vision")
visual = vd.candidate_visible_component_evidence(detail, query)
assert visual["state"] == "TRUE", visual
assert set(visual["visible"]) == {"aircraft", "window"}
assert vd.visual_specificity_decision(detail, query)["level"] <= 3

# CASE C: weak metadata does not erase positive visual evidence or turn it into FALSE.
vd.register_visual_evidence(weak_metadata_visible, visible_components=["aircraft", "window"], source="hook_dominance_vision")
visual = vd.candidate_visible_component_evidence(weak_metadata_visible, query)
assert visual["state"] == "TRUE", visual
assert set(visual["visible"]) == {"aircraft", "window"}

# CASE D: Hook/concrete selection must prefer actually visible window over wing/cloud semantic-only footage.
selected = vd.choose_best_candidate([wing_view, detail], subject_filter_query=query)
assert selected["source_id"] == detail["source_id"], selected

# CASE E: UNKNOWN cannot outrank TRUE for concrete direct/close selection.
unknown = candidate(6, "aircraft window perfect rounded detail", "airplane window rounded closeup", 1)
true_candidate = candidate(7, "aircraft cabin passenger windows", "airplane cabin window visible", 2)
vd.register_visual_evidence(true_candidate, visible_components=["aircraft", "window"], source="hook_dominance_vision")
assert vd.candidate_visible_component_evidence(unknown, query)["state"] == "UNKNOWN"
assert vd.visual_specificity_decision(unknown, query)["level"] >= 4
selected = vd.choose_best_candidate([unknown, true_candidate], subject_filter_query=query)
assert selected["source_id"] == true_candidate["source_id"], selected

# CASE F: verified relevant safe reuse outranks semantic-only fresh wing/cloud candidate.
reset_state()
vd.register_visual_evidence(detail, visible_components=["aircraft", "window"], source="hook_dominance_vision")
vd._mark_candidate_used(detail)
semantic_only = candidate(8, "airplane window view wing clouds", "aircraft window wing clouds", 1)
reused = vd.choose_best_candidate([semantic_only], subject_filter_query=query)
assert reused.get("_safe_reuse") is True, reused
assert reused["source_id"] == detail["source_id"]

# CASE G: unrelated underwater visual cannot outrank verified aircraft-window reuse.
reused = vd.choose_best_candidate([underwater], subject_filter_query=query)
assert reused.get("_safe_reuse") is True, reused
assert reused["source_id"] == detail["source_id"]

# CASE H: with no visual evidence source, scarcity fallback still returns a same-domain candidate.
reset_state()
selected = vd.choose_best_candidate([generic_airplane], subject_filter_query=query)
assert selected is not None and selected["source_id"] == generic_airplane["source_id"]
assert vd.candidate_visible_component_evidence(selected, query)["state"] == "UNKNOWN"
assert vd.visual_specificity_decision(selected, query)["level"] >= 4

# Existing Hook visual source must remain actual-frame based and conservative.
normalized = hvd.normalize_dominance_result({
    "target_subject": "aircraft window",
    "subject_dominance": 9,
    "action_match": 10,
    "competing_subject_risk": 1,
    "vertical_crop_subject_visible": True,
    "visible_components": ["aircraft"],
    "reason": "wing/cloud view; window frame absent",
}, action_required=False)
assert normalized["visible_components"] == ["aircraft"]

# CASE I: #20 contracts remain behaviorally active.
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

# CASE J: #21 answer leakage remains rejected.
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

# CASE K/L/M/N: #22/#23/#24/#25 behavior remains intact.
reset_state()
vd.register_visual_evidence(detail, visible_components=["aircraft", "window"], source="hook_dominance_vision")
vd.register_visual_evidence(generic_airplane, visible_components=["aircraft"], source="hook_dominance_vision")
assert vd.visual_specificity_decision(detail, query)["level"] < vd.visual_specificity_decision(generic_airplane, query)["level"]
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
assert vd.extract_query_anchors(query) == ["aircraft", "window"]
for relaxed in vd.query_relaxation_ladder(query):
    assert vd.extract_query_anchors(relaxed) == ["aircraft", "window"]
assert vd.concrete_visual_evidence(detail, query)["complete"] is True
assert vd.concrete_visual_evidence(generic_airplane, query)["complete"] is False

# CASE O: provider failure isolation remains bidirectional.
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

print("PASS: visible provenance A-H, #20-#25 I-N, provider isolation O")
