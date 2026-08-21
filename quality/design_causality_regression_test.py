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
    "ci_design_causality_hotfix.py",
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual_dominance as hvd
from video import video_downloader as vd
legacy = sg._LEGACY


def scene(text, visual_goal="airplane window structural detail", keyword="airplane window detail"):
    return {"text": text, "visual_goal": visual_goal, "keyword": keyword}


design_context = {
    "topic": "비행기 창문의 작은 구멍은 왜 이런 구조로 설계됐을까",
    "angle": "창문 구조와 작은 구멍의 기능",
    "core_question": "왜 비행기 창문에 작은 구멍이 있는가",
    "fact_check_focus": ["창문은 여러 겹이다", "작은 구멍은 판 사이 압력 관계를 조절한다"],
    "micro_narrative": {
        "hook": "비행기 창문에는 작은 구멍이 있다.",
        "core_question": "이 구멍은 무슨 역할을 하는가",
        "reveal": "작은 구멍은 판 사이 압력 관계를 조절한다",
        "payoff": "압력 하중이 설계된 구조에 걸리도록 돕는다",
    },
}

# CASE A: flat benefit enumeration fails for a design topic.
feature_list = [
    scene("이 구멍은 압력 조절에도 도움이 됩니다."),
    scene("결로를 줄이는 데도 도움이 됩니다."),
    scene("안전에도 도움이 됩니다."),
]
a = legacy.design_causality_assessment(feature_list, design_context)
assert a["applicable"] and not a["pass"] and "benefit enumeration" in a["reason"]

# CASE B: verified causal chain passes.
causal = [
    scene("높은 고도에서는 기내와 외부의 압력 차이가 커집니다."),
    scene("창문 구조는 이 압력 하중을 견뎌야 합니다."),
    scene("그래서 창문을 여러 겹으로 사용합니다."),
    scene("작은 구멍이 판 사이 압력 관계를 조절합니다."),
    scene("그 결과 압력을 담당하는 구조가 유지됩니다."),
]
b = legacy.design_causality_assessment(causal, design_context)
assert b["pass"] and b["causal_stage_count"] >= 4
assert legacy.design_causality_preference_score(causal, design_context) > legacy.design_causality_preference_score(feature_list, design_context)

# CASE C/D: a missing constraint is not invented; FUNCTION-only evidence cannot support DESIGN INTENT.
function_only = dict(design_context)
function_only["fact_check_focus"] = ["작은 구멍은 판 사이 압력 관계를 조절한다"]
function_only["micro_narrative"] = {
    "hook": "비행기 창문에는 작은 구멍이 있다.",
    "core_question": "이 구멍은 무슨 역할을 하는가",
    "reveal": "작은 구멍은 판 사이 압력 관계를 조절한다",
    "payoff": "판 사이 압력 관계를 조절한다",
}
function_script = [scene("작은 구멍은 판 사이 압력 관계를 조절합니다.")]
assert legacy.design_causality_assessment(function_script, function_only)["pass"]
unsupported_intent = [scene("압력을 조절하기 위해 이 구멍이 설계됐습니다.")]
d = legacy.design_causality_assessment(unsupported_intent, function_only)
assert not d["pass"] and "unsupported design intent" in d["reason"]

# CASE E: non-design topic keeps the existing narrative path.
general_context = {
    "topic": "번개가 칠 때 하늘에서 일어나는 현상",
    "angle": "자연 현상",
    "core_question": "번개는 어떻게 보이는가",
}
e = legacy.design_causality_assessment([scene("번개가 구름 사이를 가릅니다.")], general_context)
assert not e["applicable"] and e["pass"]

# CASE F: #20 contracts.
assert he._output_quality_is_declarative_hook("비행기 창문에는 작은 구멍이 있다.")
assert not he._output_quality_is_declarative_hook("비행기 창문 구멍은 뭘까요?")
assert hvd.HOOK_SUBJECT_VISIBILITY_MIN == 8.0
assert vd.current_narration_semantic_match(
    {"title": "airplane window layers", "tags": "airplane window pane layers"}, "airplane window layers"
) > vd.current_narration_semantic_match(
    {"title": "airplane cockpit", "tags": "airplane cockpit pilot"}, "airplane window layers"
)

# CASE G: #21 retention contracts.
locked = {"reveal": "작은 구멍은 판 사이 압력을 조절한다", "payoff": "압력 하중이 구조에 걸리도록 돕는다"}
progression = {
    "_candidate_retention": locked,
    "scenes": [
        scene("비행기 창문에는 작은 구멍이 있다."),
        scene("비행기 안팎에는 압력 차이가 생깁니다."),
        scene("창문은 한 장이 아니라 여러 겹입니다."),
        scene("작은 구멍은 판 사이 압력을 조절한다."),
        scene("압력 하중이 구조에 걸리도록 돕는다."),
    ],
}
ok, reason = legacy.validate_curiosity_retention(progression)
assert ok, reason
leak = dict(progression)
leak["scenes"] = [
    scene("비행기 창문에는 작은 구멍이 있다."),
    scene("작은 구멍은 판 사이 압력을 조절한다."),
    scene("창문은 여러 겹입니다."),
    scene("압력 하중이 구조에 걸리도록 돕는다."),
]
ok, reason = legacy.validate_curiosity_retention(leak)
assert not ok and "answer leakage" in reason

# CASE H: #22 visual specificity / anti-generic B-roll.
exact = {"id": 1, "provider": "pixabay", "source_id": 1, "title": "airplane window small hole close up", "tags": "aircraft window hole detail", "search_position": 2}
generic = {"id": 2, "provider": "pixabay", "source_id": 2, "title": "airplane flying", "tags": "airplane aircraft flight", "search_position": 1}
selected = vd.choose_best_candidate([generic, exact], subject_filter_query="airplane window small hole")
assert selected["source_id"] == 1
abstract = {"id": 3, "provider": "pixabay", "source_id": 3, "title": "abstract ink liquid", "tags": "abstract ink liquid particles", "search_position": 1}
assert vd.visual_specificity_decision(abstract, "aircraft pressure valve mechanism")["level"] == 5

print("PASS: design causality A-E, #20 F, #21 G, #22 H")
