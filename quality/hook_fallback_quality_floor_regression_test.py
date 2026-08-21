from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HOTFIXES = (
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py", "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py", "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py", "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py", "ci_hook_fallback_quality_floor_hotfix.py",
)
for hotfix in HOTFIXES:
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual as hv
from video import hook_visual_dominance as hvd
from video import video_downloader as vd

legacy = sg._LEGACY
query = "airplane window rounded corner"

def c(source_id, title, pos=1):
    return {
        "id": source_id, "source_id": source_id, "provider": "pexels",
        "url": f"https://cdn.test/{source_id}.mp4", "title": title, "tags": title,
        "page_url": f"https://pexels.test/{source_id}", "search_position": pos,
        "width": 1080, "height": 1920, "duration": 8.0,
    }

wing = c(1, "airplane wing clouds", 1)
unknown_window = c(2, "aircraft cabin passenger window", 2)
verified_window = c(3, "aircraft window rounded detail close up", 3)
generic_airplane = c(4, "generic airplane exterior", 4)

# A/F: FALSE same-domain cannot beat UNKNOWN complete-anchor component candidate.
vd.register_visual_evidence(wing, visible_components=["aircraft"], source="frame", definitive=True)
cand, quality, _ = hv._choose_hook_fallback([
    {"candidate": wing, "total_score": 9.5},
    {"candidate": unknown_window, "total_score": 7.0},
], query)
assert cand["id"] == 2, (cand, quality)
assert quality["label"] == "COMPONENT_RELEVANT_FALLBACK", quality
assert quality["visual"]["state"] == "UNKNOWN", quality

# C: compound component context outranks generic airplane context.
cand, quality, _ = hv._choose_hook_fallback([
    {"candidate": generic_airplane, "total_score": 9.9},
    {"candidate": unknown_window, "total_score": 6.5},
], query)
assert cand["id"] == 2, (cand, quality)

# B/G: visually verified compatible reuse outranks fresh generic and remains bounded.
vd._SAFE_REUSE_HISTORY.clear(); vd._SAFE_REUSE_COUNTS.clear()
vd._SAFE_REUSE_HISTORY[vd._safe_reuse_key(verified_window)] = dict(verified_window)
vd._SAFE_REUSE_COUNTS[vd._safe_reuse_key(verified_window)] = 0
vd.register_visual_evidence(verified_window, visible_components=["aircraft", "window"], source="hook_dominance_vision", definitive=True)
cand, quality, _ = hv._choose_hook_fallback([{"candidate": wing, "total_score": 10.0}], query)
assert cand["id"] == 3 and quality["label"] == "VERIFIED_COMPATIBLE_REUSE", (cand, quality)
vd._mark_candidate_used(cand)
assert vd.get_last_safe_reuse_offset() == 0.75
cand, quality, _ = hv._choose_hook_fallback([{"candidate": wing, "total_score": 10.0}], query)
assert cand["id"] == 3
vd._mark_candidate_used(cand)
assert vd.get_last_safe_reuse_offset() == 1.5
cand, quality, _ = hv._choose_hook_fallback([{"candidate": wing, "total_score": 10.0}], query)
assert cand["id"] == 1, (cand, quality)  # reuse cap reached

# D: verified exact remains DIRECT_VERIFIED in actual Hook selection chain.
scene = {"text": "비행기 창문이 둥근 데는 이유가 있다.", "keyword": query, "visual_goal": "aircraft window rounded detail"}
orig_search = hv.search_video_candidates
orig_dom = hv.evaluate_hook_subject_dominance
try:
    hv.search_video_candidates = lambda *a, **k: [wing, verified_window]
    def dom(item, scene_item):
        visible = ["aircraft"] if item["id"] == 1 else ["aircraft", "window"]
        return {"pass": True, "subject_dominance": 9.0, "action_match": 10.0,
                "competing_subject_risk": 1.0, "vertical_crop_subject_visible": True,
                "action_required": False, "visible_components": visible,
                "reason": "frame observation", "frame_times": [0.0, 0.5, 1.5, 2.5]}
    hv.evaluate_hook_subject_dominance = dom
    url = hv.fetch_hook_pexels_video(scene)
    trace = hv.get_last_hook_selection()
    assert url == verified_window["url"] and trace["selection_mode"] == "DIRECT_VERIFIED", trace
    contract = hv.hook_render_contract(trace, render_start=0.0, render_duration=3.0, final_url=url)
    assert contract["render_contract_valid"] is True, contract
finally:
    hv.search_video_candidates = orig_search
    hv.evaluate_hook_subject_dominance = orig_dom

# E: no relevant candidate may fall to LAST_RESORT without pretending to be verified.
empty_cand, empty_quality, _ = hv._choose_hook_fallback([], query)
assert empty_cand is None and empty_quality is None
last = hv.record_last_resort_selection("https://cdn.test/last.mp4", scene, "no relevant candidates")
assert last["selection_mode"] == "LAST_RESORT" and last["visual_evidence"] == "UNKNOWN"

# H and #20-#27 preservation: core behavioral contracts remain active.
assert he._output_quality_is_declarative_hook("비행기 창문에는 이유가 있다.")
assert not he._output_quality_is_declarative_hook("비행기 창문은 왜 그럴까요?")
assert hvd.HOOK_SUBJECT_VISIBILITY_MIN == 8.0
assert vd.extract_query_anchors(query) == ["aircraft", "window"]
assert vd.candidate_visible_component_evidence(wing, query)["state"] == "FALSE"
assert vd.visual_specificity_decision(unknown_window, query)["visual_evidence_state"] == "UNKNOWN"
assert legacy.design_causality_preference_score([
    {"text":"압력 차이가 커집니다."},{"text":"구조가 견뎌야 합니다."},
    {"text":"그래서 여러 겹을 씁니다."},{"text":"구멍이 압력을 조절합니다."},{"text":"그 결과 하중을 유지합니다."},
]) > legacy.design_causality_preference_score([{"text":"안전에 도움됩니다."},{"text":"또 다른 역할도 합니다."}])

# Provider isolation remains bidirectional.
orig_p, orig_x, orig_key = vd.search_pexels_candidates, vd.search_pixabay_candidates, vd.PIXABAY_API_KEY
try:
    def fail(*a, **k): raise RuntimeError("provider failure")
    def pix(*a, **k): return [{"id":11,"provider":"pixabay","source_id":11,"url":"x","download_url":"x","source_url":"x","title":"aircraft window","tags":"aircraft window","search_position":1,"width":1080,"height":1920,"duration":8}]
    def pex(*a, **k): return [{"id":12,"url":"y","page_url":"y","search_position":1}]
    vd.PIXABAY_API_KEY = "test"
    vd.search_pexels_candidates, vd.search_pixabay_candidates = fail, pix
    assert vd.search_video_candidates("aircraft window", per_page=3)[0]["provider"] == "pixabay"
    vd.search_pexels_candidates, vd.search_pixabay_candidates = pex, fail
    assert vd.search_video_candidates("aircraft window", per_page=3)[0]["provider"] == "pexels"
finally:
    vd.search_pexels_candidates, vd.search_pixabay_candidates, vd.PIXABAY_API_KEY = orig_p, orig_x, orig_key

print("PASS: Hook fallback quality A-H, #20-#27 contracts, provider isolation")
