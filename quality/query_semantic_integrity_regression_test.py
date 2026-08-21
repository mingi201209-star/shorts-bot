from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for hotfix in (
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py", "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py", "ci_query_semantic_integrity_hotfix.py",
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual_dominance as hvd
from video import video_downloader as vd
legacy = sg._LEGACY


def c(i, title, tags, pos):
    return {"id": i, "provider": "pixabay", "source_id": i,
            "url": f"https://cdn.test/{i}.mp4", "download_url": f"https://cdn.test/{i}.mp4",
            "source_url": f"https://test/{i}", "title": title, "tags": tags, "search_position": pos}

# A: compound aircraft+window anchor controls ranking, not WINDOW alone.
q = "airplane window rounded corner"
stained = c(1, "stained glass church window", "decorative window architecture church", 1)
airplane = c(2, "airplane flying", "aircraft exterior flight", 2)
cabin = c(3, "aircraft cabin passenger windows", "airplane cabin window passenger", 3)
detail = c(4, "aircraft window rounded corner detail", "airplane window rounded shape closeup", 4)
ranked = sorted([stained, airplane, cabin, detail], key=lambda x: vd.visual_specificity_decision(x, q)["level"])
assert [x["source_id"] for x in ranked] == [4, 3, 2, 1]
assert vd.choose_best_candidate([stained, airplane, cabin, detail], subject_filter_query=q)["source_id"] == 4

# B: cross-domain partial keyword overlap cannot enter direct/close tiers.
q2 = "aircraft window pressure mechanism"
flower = c(5, "flower with bee", "nature flower insect bee", 1)
lab = c(6, "laboratory pressure experiment", "laboratory pressure science", 2)
cabin2 = c(7, "airplane cabin windows", "aircraft cabin passenger window", 3)
detail2 = c(8, "aircraft window pressure detail", "airplane window pressure mechanism", 4)
for wrong in (flower, lab):
    assert vd.visual_specificity_decision(wrong, q2)["level"] >= 4
assert vd.choose_best_candidate([flower, lab, cabin2, detail2], subject_filter_query=q2)["source_id"] == 8

# C/D: scarcity keeps same-world fallback; if window is absent, generic aircraft remains bounded.
assert vd.choose_best_candidate([stained, cabin, airplane], subject_filter_query=q)["source_id"] == 3
fallback = vd.choose_best_candidate([airplane], subject_filter_query=q)
assert fallback is not None and fallback["source_id"] == 2
assert vd.visual_specificity_decision(airplane, q)["level"] == 4

# E: relaxation preserves AIRCRAFT+WINDOW until bounded same-world context.
ladder = vd.query_relaxation_ladder("airplane window rounded corner closeup")
assert ladder
for query in ladder:
    anchors = vd.extract_query_anchors(query)
    assert anchors == ["aircraft", "window"], (query, anchors)

# F: provider failure isolation remains behavioral in both directions.
orig_p, orig_x, orig_key = vd.search_pexels_candidates, vd.search_pixabay_candidates, vd.PIXABAY_API_KEY
try:
    def fail(*a, **k): raise RuntimeError("simulated")
    def px(*a, **k): return [c(77, "airplane window", "aircraft window", 1)]
    def pe(*a, **k): return [{"id": 88, "url": "https://cdn.test/88.mp4", "page_url": "https://pexels.com/video/airplane-window-88/", "search_position": 1}]
    vd.PIXABAY_API_KEY = "test"
    vd.search_pexels_candidates, vd.search_pixabay_candidates = fail, px
    assert vd.search_video_candidates("airplane window", per_page=3)[0]["provider"] == "pixabay"
    vd.search_pexels_candidates, vd.search_pixabay_candidates = pe, fail
    assert vd.search_video_candidates("airplane window", per_page=3)[0]["provider"] == "pexels"
finally:
    vd.search_pexels_candidates, vd.search_pixabay_candidates, vd.PIXABAY_API_KEY = orig_p, orig_x, orig_key

# G #20 behavior.
assert he._output_quality_is_declarative_hook("비행기 창문은 둥글게 만들어진다.")
assert hvd.HOOK_SUBJECT_VISIBILITY_MIN == 8.0
assert vd.current_narration_semantic_match(detail2, q2) > vd.current_narration_semantic_match(airplane, q2)
assert legacy.detect_information_density_issue([{"text":"같은 설명입니다."},{"text":"같은 설명입니다."}]) is not None

# H #21 retention behavior.
locked = {"reveal":"창문의 둥근 형태는 응력 집중을 줄인다", "payoff":"그래서 압력 하중이 모서리에 집중되지 않게 한다"}
progress = {"_candidate_retention": locked, "scenes":[
    {"text":"비행기 창문은 둥글게 만들어진다."}, {"text":"고도에서는 압력 차이가 커진다."},
    {"text":"모서리는 하중이 모일 수 있는 지점이다."}, {"text":"둥근 형태는 힘이 퍼지는 경로를 만든다."},
    {"text":"그래서 압력 하중이 모서리에 집중되지 않게 한다."}]}
assert legacy.validate_curiosity_retention(progress)[0]

# I #22 specificity behavior.
assert vd.visual_specificity_decision(detail, q)["level"] < vd.visual_specificity_decision(airplane, q)["level"]

# J #23 causality behavior.
feature = [{"text":"장점이 있습니다."},{"text":"또 도움이 됩니다."},{"text":"안전 역할도 합니다."}]
causal = [{"text":"압력 차이가 커집니다."},{"text":"모서리에 하중이 집중될 수 있습니다."},{"text":"그래서 창문을 둥글게 설계합니다."},{"text":"둥근 형태가 힘을 분산합니다."},{"text":"그 결과 하중 집중이 줄어듭니다."}]
assert legacy.design_causality_preference_score(causal) > legacy.design_causality_preference_score(feature)

print("PASS: query anchor A-E, provider F, #20 G, #21 H, #22 I, #23 J")
