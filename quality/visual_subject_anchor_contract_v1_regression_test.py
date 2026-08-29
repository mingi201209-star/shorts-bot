from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AI_VISUAL_FALLBACK_ENABLED"] = "false"

HOTFIXES = (
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_final_render_content_integrity_hotfix.py", "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py", "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py", "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py", "ci_hook_fallback_quality_floor_hotfix.py",
    "ci_ai_visual_fallback_hotfix.py", "ci_ai_visual_mechanism_fallback_hotfix.py",
    "ci_causal_information_progression_hotfix.py", "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py", "ci_general_scene_visual_parity_hotfix.py",
    "ci_final_visual_semantic_qa_hotfix.py",
)
for hotfix in HOTFIXES:
    subprocess.run([sys.executable, str(ROOT / hotfix)], cwd=ROOT, check=True)
anchor_hotfix = ROOT / "ci_visual_subject_anchor_contract_v1_hotfix.py"
if anchor_hotfix.exists():
    subprocess.run([sys.executable, str(anchor_hotfix)], cwd=ROOT, check=True)

from video import video_downloader as vd
from quality import final_visual_semantic_qa as fvs

NARRATION = "비행기 엔진 앞 소용돌이 무늬는 왜 그려져 있을까요?"
GOAL = "비행기 엔진 앞 소용돌이 무늬를 명확히 보여준다."


def candidate(source_id, metadata):
    return {
        "id": source_id,
        "source_id": source_id,
        "provider": "pixabay",
        "url": f"https://cdn.test/{source_id}.mp4",
        "download_url": f"https://cdn.test/{source_id}.mp4",
        "source_url": f"https://pixabay.test/{source_id}",
        "title": metadata,
        "tags": metadata,
        "search_position": 1,
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
    }


def strengthened(query, narration=NARRATION, goal=GOAL, visual_type="real_world_broll"):
    if not hasattr(vd, "enforce_visual_subject_anchor_query"):
        return vd.normalize_search_query(query)
    return vd.enforce_visual_subject_anchor_query(
        narration=narration,
        visual_goal=goal,
        query=query,
        visual_type=visual_type,
    )


# Run 33227410361 deterministic counterexamples. BEFORE, these generic queries
# have 0 required anchors and the wrong result is treated as compatible. AFTER,
# source context must restore aircraft/engine/spinner before selection.
fixtures = (
    ("engine design", candidate(2708, "red car automobile rotating studio engine design")),
    ("curious question", candidate(114894, "meerkat curious cute vigilant animal")),
    ("airflow effect", candidate(27228, "tv effect glitch distortion static noise")),
    ("fuel consumption", candidate(236, "rocket launch propulsion fuel nasa space")),
)

for original_query, wrong in fixtures:
    query = strengthened(original_query)
    anchors = vd.extract_query_anchors(query)
    assert "aircraft" in anchors, ("lost_domain_anchor", original_query, query, anchors)
    assert "engine" in anchors, ("lost_subject_anchor", original_query, query, anchors)
    assert "spinner" in anchors, ("lost_component_anchor", original_query, query, anchors)
    compatibility = vd.candidate_anchor_compatibility(wrong, query)
    assert compatibility["total"] >= 3, (original_query, query, compatibility)
    assert compatibility["compatible"] is False, (original_query, query, compatibility)
    assert vd.choose_best_candidate([wrong], subject_filter_query=query) is None, (original_query, query)

# A correct result remains selectable and complete.
correct = candidate(9001, "aircraft airplane turbofan jet engine spinner spiral closeup")
query = strengthened("engine design")
assert vd.candidate_anchor_compatibility(correct, query)["compatible"] is True
assert vd.choose_best_candidate([correct], subject_filter_query=query)["source_id"] == 9001

# Scene 4: narration requires the concrete subject even if visual_goal/query drift
# to a generic graph. This is validation/retrieval protection, not Writer repair.
scene4_query = strengthened(
    "performance graph",
    narration="핵심은 비행기 엔진 앞 소용돌이 무늬의 실제 사진입니다.",
    goal="엔진의 성능을 나타내는 그래프",
)
assert {"aircraft", "engine", "spinner"}.issubset(set(vd.extract_query_anchors(scene4_query)))
graph = candidate(20833, "performance graph line chart business statistics")
assert vd.choose_best_candidate([graph], subject_filter_query=scene4_query) is None

# Vacuous 0/0 PASS becomes an explicit fail-close.
missing = {
    "query": "engine design",
    "accepted": True,
    "anchor_matched": 0,
    "anchor_total": 0,
    "subject_anchor_contract_required": True,
    "required_subject_anchors": ["aircraft", "engine", "spinner"],
}
assert hasattr(fvs, "_missing_required_subject_anchor"), "vacuous 0/0 semantic PASS still has no fail-close"
assert fvs._missing_required_subject_anchor(missing) is True
assert missing.get("failure_reason") == "missing_required_subject_anchor"

# Negative regressions: generic/non-subject scenes remain generic and are not
# forced into the aviation domain.
for narration, goal, query in (
    ("분위기가 잠시 바뀝니다.", "soft atmospheric transition", "soft transition clouds"),
    ("수치는 계속 증가합니다.", "generic performance graph", "performance graph"),
):
    effective = strengthened(query, narration=narration, goal=goal)
    assert effective == vd.normalize_search_query(query), (query, effective)
    if hasattr(vd, "get_current_visual_subject_anchor_contract"):
        assert vd.get_current_visual_subject_anchor_contract()["required"] is False

# Already-specific aviation queries are preserved, not rewritten into a fixed
# spinner string. Existing Visual Explanation-style aircraft/window subjects stay valid.
wing_query = strengthened(
    "aircraft wing wingtip vortex",
    narration="비행기 날개 끝에서 소용돌이가 생깁니다.",
    goal="aircraft wingtip vortex closeup",
)
assert wing_query == "aircraft wing wingtip vortex", wing_query
window_query = strengthened(
    "aircraft window pressure mechanism",
    narration="비행기 창문은 압력 차이를 견뎌야 합니다.",
    goal="aircraft window pressure mechanism",
)
window = candidate(9002, "aircraft airplane window pressure mechanism closeup")
assert vd.choose_best_candidate([window], subject_filter_query=window_query) is not None

print("PASS: Visual Subject Anchor Contract V1 blocks Run 33227410361 false positives without forcing generic scenes")
