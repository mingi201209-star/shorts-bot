from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AI_VISUAL_FALLBACK_ENABLED"] = "false"
os.environ["AI_MAX_GENERATIONS_PER_VIDEO"] = "1"

HOTFIXES = (
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py", "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py", "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py", "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py", "ci_hook_fallback_quality_floor_hotfix.py",
    "ci_ai_visual_fallback_hotfix.py", "ci_ai_visual_mechanism_fallback_hotfix.py",
    "ci_causal_information_progression_hotfix.py", "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py", "ci_general_scene_visual_parity_hotfix.py",
)
for hotfix in HOTFIXES:
    subprocess.run([sys.executable, str(ROOT / hotfix)], cwd=ROOT, check=True)

from video import video_downloader as vd


def c(source_id, title, pos=1):
    return {
        "id": source_id, "source_id": source_id, "provider": "pexels",
        "url": f"https://cdn.test/{source_id}.mp4", "download_url": f"https://cdn.test/{source_id}.mp4",
        "source_url": f"https://pexels.test/{source_id}", "page_url": f"https://pexels.test/{source_id}",
        "title": title, "tags": title, "search_position": pos,
        "width": 1080, "height": 1920, "duration": 8.0,
    }


def reset():
    vd.USED_VIDEO_IDS.clear()
    vd._SAFE_REUSE_HISTORY.clear()
    vd._SAFE_REUSE_COUNTS.clear()
    vd._VISUAL_EVIDENCE_REGISTRY.clear()
    vd.get_last_safe_reuse_offset()


query = "aircraft cabin noise control mechanism"
mechanism = c(1, "aircraft cabin noise control mechanism microphone", 5)
cabin = c(2, "aircraft cabin interior passenger", 1)
butterfly = c(3, "butterfly flower nature", 1)
loading = c(4, "loading abstract graphic animation", 1)
nature = c(5, "forest nature sunlight", 1)

# A/B: actual general selector ranks semantic mechanism > domain context > unrelated UNKNOWN.
reset()
assert vd.general_scene_unknown_safe_tier(mechanism, query)[0] == 3
assert vd.general_scene_unknown_safe_tier(cabin, query)[0] == 4
assert vd.general_scene_unknown_safe_tier(butterfly, query)[0] >= 5
selected = vd.choose_best_candidate([butterfly, loading, nature, cabin, mechanism], subject_filter_query=query)
assert selected["id"] == 1, selected

# Run 32796378299: aircraft-domain drone/beach footage matched only 1/2
# anchors for a concrete wing query. Reject it upstream so retry/safe reuse can run.
reset()
wing_query = "aircraft wing wingtip vortex stage 7"
partial_wing = c(314643, "drone nature beach camera technology aircraft uav travel sea", 1)
assert vd.general_scene_unknown_safe_tier(partial_wing, wing_query)[0] >= 5
assert vd.choose_best_candidate([partial_wing], subject_filter_query=wing_query) is None

# Run 32938743453: Pixabay 3966 had matching aircraft/wing metadata, but
# sampled production frames showed almost only sunset sky with the subject
# reduced to an edge fragment. The exact known-bad asset must fail closed.
reset()
hidden_wing = dict(
    c(3966, "plane sky flight height aviation airplane wing sunset", 1),
    provider="pixabay",
)
assert vd.general_scene_unknown_safe_tier(hidden_wing, wing_query) == (
    5,
    "KNOWN_HIDDEN_SUBJECT_ASSET",
)
assert vd.choose_best_candidate([hidden_wing], subject_filter_query=wing_query) is None

# Run 32922000250: an aircraft/engine green-screen result is not evidence of
# the serrated chevron component. Fail closed unless metadata names that part.
reset()
chevron_query = "aircraft jet engine chevron noise stage 1"
generic_engine = c(
    14096,
    "flight plane aircraft jet engine green screen production",
    1,
)
assert vd.general_scene_unknown_safe_tier(generic_engine, chevron_query)[0] >= 5
assert vd.choose_best_candidate(
    [generic_engine],
    subject_filter_query=chevron_query,
) is None

reset()
chevron_detail = c(
    99,
    "aircraft jet engine chevron serrated nacelle closeup",
    1,
)
assert vd.general_scene_unknown_safe_tier(chevron_detail, chevron_query)[0] <= 4
assert vd.choose_best_candidate(
    [generic_engine, chevron_detail],
    subject_filter_query=chevron_query,
)["id"] == 99

# Production-like fetch_video path must also return the mechanism candidate, not nature/abstract.
reset()
orig_search, orig_key = vd.search_video_candidates, vd.PIXABAY_API_KEY
try:
    vd.PIXABAY_API_KEY = "test"
    vd.search_video_candidates = lambda *a, **k: [butterfly, loading, cabin, mechanism]
    url = vd.fetch_video(query)
    assert url == mechanism["url"], url
finally:
    vd.search_video_candidates, vd.PIXABAY_API_KEY = orig_search, orig_key

# C/D: same-anchor semantic-safe reuse beats cross-domain fresh UNKNOWN and stays bounded.
reset()
previous = c(6, "aircraft cabin noise control system", 2)
key = vd._safe_reuse_key(previous)
vd._SAFE_REUSE_HISTORY[key] = dict(previous)
vd._SAFE_REUSE_COUNTS[key] = 0
sel = vd.choose_best_candidate([butterfly], subject_filter_query=query)
assert sel["id"] == 6 and sel.get("_semantic_safe_reuse") is True, sel
assert vd.candidate_visible_component_evidence(sel, query)["state"] == "UNKNOWN"
vd._mark_candidate_used(sel); assert vd.get_last_safe_reuse_offset() == 0.75
sel = vd.choose_best_candidate([butterfly], subject_filter_query=query)
assert sel["id"] == 6
vd._mark_candidate_used(sel); assert vd.get_last_safe_reuse_offset() == 1.5
sel = vd.choose_best_candidate([butterfly], subject_filter_query=query)
assert sel is None, sel  # exhausted safe reuse must fail closed, never select cross-domain stock

# E: narration/query with no concrete/domain anchor keeps existing abstract path.
abstract_query = "sound wave abstract animation"
assert vd._general_scene_strengthening_applicable(abstract_query) is False

# F: #24 query relaxation retains known domain anchors instead of drifting to bare sound/frequency.
variants = vd.query_relaxation_ladder("aircraft cabin active noise control")
assert variants, variants
for variant in variants:
    words = set(vd.normalize_search_query(variant).split())
    assert ("aircraft" in words or "airplane" in words) and "cabin" in words, variants

# G/H: existing actual frame evidence wins; absent frame evidence remains UNKNOWN.
reset()
weak_metadata = c(7, "aircraft cabin interior", 4)
assert vd.candidate_visible_component_evidence(weak_metadata, query)["state"] == "UNKNOWN"
vd.register_visual_evidence(weak_metadata, visible_components=["aircraft", "cabin"], source="existing_frame_signal", definitive=True)
assert vd.candidate_visible_component_evidence(weak_metadata, query)["state"] == "TRUE"
assert vd.general_scene_unknown_safe_tier(weak_metadata, query)[0] == 1
unknown = c(8, "aircraft cabin noise control", 3)
assert vd.candidate_visible_component_evidence(unknown, query)["state"] == "UNKNOWN"

# I/J: provider failure isolation remains bidirectional.
orig_p, orig_x, orig_key = vd.search_pexels_candidates, vd.search_pixabay_candidates, vd.PIXABAY_API_KEY
try:
    def fail(*a, **k): raise RuntimeError("provider failure")
    def pix(*a, **k): return [dict(c(9, "aircraft cabin noise control"), provider="pixabay")]
    def pex(*a, **k): return [c(10, "aircraft cabin noise control")]
    vd.PIXABAY_API_KEY = "test"
    vd.search_pexels_candidates, vd.search_pixabay_candidates = fail, pix
    assert vd.search_video_candidates(query, per_page=3)[0]["provider"] == "pixabay"
    vd.search_pexels_candidates, vd.search_pixabay_candidates = pex, fail
    assert vd.search_video_candidates(query, per_page=3)[0]["provider"] == "pexels"
finally:
    vd.search_pexels_candidates, vd.search_pixabay_candidates, vd.PIXABAY_API_KEY = orig_p, orig_x, orig_key

# K-O: existing #24-#28 contracts remain active at their public behavior boundaries.
assert vd.extract_query_anchors("airplane window rounded corner") == ["aircraft", "window"]
window = c(11, "aircraft window rounded detail", 1)
assert vd.concrete_visual_evidence(window, "airplane window rounded corner")["complete"] is True
assert vd.candidate_visible_component_evidence(window, "airplane window rounded corner")["state"] == "UNKNOWN"
assert hasattr(vd, "safe_reuse_candidate") and vd._SAFE_REUSE_MAX == 2
assert hasattr(vd, "get_last_general_selection")  # #29 trace remains wired; AI stays OFF.

# P/#31: script production parity files are present but untouched by this visual hotfix.
main_yml = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in main_yml
assert "ci_script_production_parity_hotfix.py" in main_yml
assert "ci_script_production_parity_bridge_hotfix.py" in main_yml

print("PASS: general-scene visual parity A-P; UNKNOWN-safe selection, semantic-safe reuse, provider isolation; no Sora/API calls")
