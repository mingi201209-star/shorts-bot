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
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual_dominance as hvd
from video import video_downloader as vd
legacy = sg._LEGACY


def candidate(source_id, title, tags, position):
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
    }


# CASE A: exact small-window subject must beat broad airplane footage.
a_flying = candidate(1, "airplane flying in sky", "aircraft airplane flight", 1)
a_exact = candidate(2, "airplane window small hole close up", "aircraft window hole detail", 2)
a_selected = vd.choose_best_candidate(
    [a_flying, a_exact],
    subject_filter_query="airplane window small hole",
)
assert a_selected["source_id"] == 2
assert vd.visual_specificity_decision(a_exact, "airplane window small hole")["level"] == 1
assert vd.visual_specificity_decision(a_flying, "airplane window small hole")["level"] >= 4

# CASE B: window/layer explanatory visual must beat clouds and generic cabin.
b_clouds = candidate(3, "clouds in blue sky", "cloud ambient nature", 1)
b_cabin = candidate(4, "airplane cabin passengers", "aircraft cabin interior", 2)
b_layers = candidate(5, "aircraft window layers", "airplane window layers pane", 3)
b_selected = vd.choose_best_candidate(
    [b_clouds, b_cabin, b_layers],
    subject_filter_query="airplane window layers",
)
assert b_selected["source_id"] == 5
assert vd.visual_specificity_decision(b_clouds, "airplane window layers")["level"] == 5

# CASE C: metaphorical/ambient visuals cannot beat direct mechanism footage.
c_jelly = candidate(6, "jellyfish floating", "jellyfish animal ocean", 1)
c_ink = candidate(7, "ink liquid swirl", "abstract ink liquid fluid", 2)
c_network = candidate(8, "abstract pressure network", "abstract network particles pressure", 3)
c_direct = candidate(9, "aircraft pressure valve", "aircraft pressure valve mechanism", 4)
c_selected = vd.choose_best_candidate(
    [c_jelly, c_ink, c_network, c_direct],
    subject_filter_query="aircraft pressure valve mechanism",
)
assert c_selected["source_id"] == 9
for abstract_candidate in (c_jelly, c_ink, c_network):
    assert vd.visual_specificity_decision(
        abstract_candidate,
        "aircraft pressure valve mechanism",
    )["level"] == 5

# CASE D: scarcity remains bounded; generic contextual fallback is allowed.
d_generic = candidate(10, "airplane exterior", "airplane aircraft flight", 1)
d_airport = candidate(11, "airport runway", "airport aircraft runway", 2)
d_selected = vd.choose_best_candidate(
    [d_generic, d_airport],
    subject_filter_query="aircraft winglet",
)
assert d_selected is not None
assert vd.visual_specificity_decision(d_selected, "aircraft winglet")["level"] == 4

# CASE E: provider failure isolation works in both directions.
original_pexels = vd.search_pexels_candidates
original_pixabay = vd.search_pixabay_candidates
original_key = vd.PIXABAY_API_KEY
try:
    def failing_provider(*args, **kwargs):
        raise RuntimeError("simulated provider failure")

    def healthy_pixabay(*args, **kwargs):
        return [candidate(77, "airplane window", "airplane window detail", 1)]

    def healthy_pexels(*args, **kwargs):
        return [{
            "id": 88,
            "url": "https://cdn.example.test/88.mp4",
            "page_url": "https://pexels.com/video/airplane-window-88/",
            "search_position": 1,
        }]

    vd.PIXABAY_API_KEY = "regression-key"
    vd.search_pexels_candidates = failing_provider
    vd.search_pixabay_candidates = healthy_pixabay
    pool = vd.search_video_candidates("airplane window", per_page=3)
    assert len(pool) == 1 and pool[0].get("provider") == "pixabay"

    vd.search_pexels_candidates = healthy_pexels
    vd.search_pixabay_candidates = failing_provider
    pool = vd.search_video_candidates("airplane window", per_page=3)
    assert len(pool) == 1 and pool[0].get("provider") == "pexels"
finally:
    vd.search_pexels_candidates = original_pexels
    vd.search_pixabay_candidates = original_pixabay
    vd.PIXABAY_API_KEY = original_key

# CASE F: #20 behavior contracts remain active.
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
filler = [
    {"text": "압력 차이는 창문 여러 겹에 나뉘어 전달됩니다."},
    {"text": "압력 차이는 창문 여러 겹에 나뉘어 전달됩니다."},
]
assert legacy.detect_information_density_issue(filler) is not None

# CASE G: #21 retention behavior remains active.
locked = {
    "reveal": "작은 구멍은 창문 사이 압력을 단계적으로 조절한다",
    "payoff": "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다",
}

def retention_result(texts):
    return {
        "_candidate_retention": locked,
        "scenes": [{"text": text} for text in texts],
    }

leak = retention_result([
    "비행기 창문에는 작은 구멍이 있다.",
    "작은 구멍은 창문 사이 압력을 단계적으로 조절한다.",
    "창문은 여러 겹이다.",
    "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
])
ok, reason = legacy.validate_curiosity_retention(leak)
assert not ok and "answer leakage" in reason

progression = retention_result([
    "비행기 창문에는 작은 구멍이 있다.",
    "이 구멍은 바깥 공기를 들이는 통로가 아니다.",
    "비행기 창문은 한 장이 아니라 여러 겹이다.",
    "고도가 올라가면 안팎의 압력 차이가 커진다.",
    "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
])
ok, reason = legacy.validate_curiosity_retention(progression)
assert ok, reason

tease = retention_result([
    "비행기 창문에는 작은 구멍이 있다.",
    "이 구멍에는 중요한 비밀이 숨어 있다.",
    "이 구멍에는 중요한 비밀이 숨어 있다.",
    "창문은 여러 겹이다.",
    "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
])
ok, reason = legacy.validate_curiosity_retention(tease)
assert not ok and "repeated tease" in reason

# Production chain remains bounded and unchanged except for this appended hotfix.
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
chain = (
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py",
    "ci_visual_specificity_hotfix.py",
)
positions = [workflow.index(item) for item in chain]
assert positions == sorted(positions)
assert "SHORTS_TOPIC: ${{ inputs.topic }}" in workflow
assert "SHORTS_CANDIDATE_SCOPE: ${{ inputs.candidate_scope }}" in workflow

print("PASS: visual specificity A/B/C/D, provider isolation E, #20 contracts F, #21 retention G")
