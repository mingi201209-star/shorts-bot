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
    "ci_concrete_visual_evidence_hotfix.py", "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py", "ci_hook_fallback_quality_floor_hotfix.py",
    "ci_ai_visual_fallback_hotfix.py", "ci_ai_visual_mechanism_fallback_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import hook_experiment as he
from content import script_generator as sg
from video import hook_visual as hv
from video import video_downloader as vd

legacy = sg._LEGACY


def scene(text, visual_goal, keyword="aircraft window detail"):
    return {"text": text, "visual_goal": visual_goal, "keyword": keyword}


design_context = {
    "topic": "왜 비행기 창문 모서리는 둥근 구조인가",
    "angle": "압력과 모서리 응력의 관계",
    "core_question": "왜 창문을 네모난 모서리로 두지 않는가",
    "fact_check_focus": [
        "높은 고도에서는 객실과 외부 사이에 압력 차이가 생긴다",
        "각진 모서리에는 응력이 집중되기 쉽다",
        "둥근 모서리는 응력 집중을 줄이는 데 유리하다",
    ],
    "micro_narrative": {
        "hook": "비행기 창문에서 네모난 모서리가 사라진 데는 이유가 있다.",
        "core_question": "모서리를 왜 둥글게 만드는가",
        "reveal": "각진 모서리에는 응력이 집중되기 쉽다",
        "payoff": "둥근 형상은 모서리 응력 집중을 줄인다",
    },
}

repeated_result = [
    scene("둥근 구조는 안전성을 높입니다.", "rounded aircraft window"),
    scene("그래서 파손 위험을 줄입니다.", "aircraft window safety"),
    scene("결과적으로 더 안전한 비행이 가능합니다.", "aircraft window in flight"),
]
a = legacy.causal_information_progression_assessment(repeated_result, design_context)
assert not a["pass"] and (
    "result repetition" in a["reason"] or "result enumeration" in a["reason"]
), a

causal_chain = [
    scene("높은 고도에서는 객실과 외부 사이 압력 차이가 커집니다.", "aircraft cabin pressure difference"),
    scene("창문은 그 압력 하중을 반복해서 견뎌야 합니다.", "aircraft window under pressure load"),
    scene("각진 모서리에는 응력이 집중되기 쉽습니다.", "square window corner stress concentration"),
    scene("그래서 창문 모서리를 둥글게 만듭니다.", "rounded aircraft window geometry"),
    scene("곡선은 힘이 한 모서리에 몰리는 정도를 줄입니다.", "stress distributed around curved window corner"),
    scene("그 결과 모서리의 응력 집중이 줄어듭니다.", "finished rounded aircraft window"),
]
b = legacy.causal_information_progression_assessment(causal_chain, design_context)
assert b["pass"], b
assert b["causal_depth"] >= 4, b
assert "weak_alternative" in b["stages"], b
visual = legacy.causal_visual_progression_assessment(causal_chain)
assert visual["distinct_visual_units"] >= 4, visual

unsupported_context = dict(design_context)
unsupported_context["fact_check_focus"] = ["둥근 모서리는 응력 집중을 줄이는 데 유리하다"]
unsupported_context["micro_narrative"] = {
    "hook": "비행기 창문 모서리는 둥글다.",
    "core_question": "둥근 형상은 어떤 역할을 하는가",
    "reveal": "둥근 형상은 응력 집중을 줄인다",
    "payoff": "모서리 응력 집중이 줄어든다",
}
unsupported = [
    scene("기존 방식은 비용 문제 때문에 사용할 수 없었습니다.", "generic manufacturing cost"),
    scene("그래서 둥근 모서리를 사용합니다.", "rounded aircraft window"),
    scene("곡선은 응력 집중을 줄입니다.", "curved window stress"),
]
d = legacy.causal_information_progression_assessment(unsupported, unsupported_context)
assert not d["pass"] and "unsupported weak/failed alternative" in d["reason"], d

outro = causal_chain + [scene("이처럼 작은 설계에서 안전은 시작됩니다.", "generic airplane beauty shot")]
e = legacy.causal_information_progression_assessment(outro, design_context)
assert not e["pass"] and "generic outro" in e["reason"], e

compact = [
    scene("압력 차이가 창문에 하중을 만듭니다.", "aircraft pressure difference"),
    scene("각진 모서리에는 응력이 집중되기 쉽습니다.", "square corner stress"),
    scene("그래서 모서리를 둥글게 만듭니다.", "rounded aircraft window"),
    scene("곡선은 모서리 응력 집중을 줄입니다.", "curved stress distribution"),
]
for item in compact:
    item["estimated_seconds"] = 6
f = legacy.causal_information_progression_assessment(compact, design_context)
assert f["pass"], f

general_context = {
    "topic": "어제 도심에서 관측된 무지개 이야기",
    "angle": "자연 현상 소개",
    "core_question": "무지개가 어떻게 보였는가",
}
g = legacy.causal_information_progression_assessment(
    [scene("비가 그친 뒤 무지개가 나타났습니다.", "rainbow over city")],
    general_context,
)
assert not g["applicable"] and g["pass"], g

assert he._output_quality_is_declarative_hook("비행기 창문 모서리는 둥글다.")
assert not he._output_quality_is_declarative_hook("비행기 창문은 왜 둥글까요?")

retention = {
    "_candidate_retention": {
        "reveal": "각진 모서리에는 응력이 집중되기 쉽다",
        "payoff": "둥근 형상은 모서리 응력 집중을 줄인다",
    },
    "scenes": [
        scene("비행기 창문에서 네모난 모서리가 사라진 데는 이유가 있다.", "aircraft window shape"),
        scene("높은 고도에서는 창문에 압력 하중이 생깁니다.", "aircraft pressure difference"),
        scene("각진 모서리에는 힘이 몰리기 쉽습니다.", "square corner stress"),
        scene("각진 모서리에는 응력이 집중되기 쉽다", "stress concentration detail"),
        scene("둥근 형상은 모서리 응력 집중을 줄인다", "rounded window stress distribution"),
    ],
}
ok, reason = legacy.validate_curiosity_retention(retention)
assert ok, reason
leak = dict(retention)
leak["scenes"] = [
    retention["scenes"][0],
    scene("각진 모서리에는 응력이 집중되기 쉽다", "stress concentration detail"),
    retention["scenes"][2],
    retention["scenes"][-1],
]
ok, reason = legacy.validate_curiosity_retention(leak)
assert not ok and "answer leakage" in reason, reason

base = legacy.design_causality_assessment(causal_chain, design_context)
assert base["pass"] and base["causal_stage_count"] >= 4, base
intent_only = [scene("안전을 위해 이 창문이 처음 설계됐습니다.", "aircraft window")]
intent_check = legacy.design_causality_assessment(intent_only, unsupported_context)
assert not intent_check["pass"] and "unsupported design intent" in intent_check["reason"], intent_check

exact = {
    "id": 1, "provider": "pixabay", "source_id": 1,
    "title": "aircraft window rounded detail", "tags": "airplane passenger window rounded corner",
    "search_position": 2,
}
generic = {
    "id": 2, "provider": "pixabay", "source_id": 2,
    "title": "airplane wing clouds", "tags": "aircraft flight sky",
    "search_position": 1,
}
selected = vd.choose_best_candidate([generic, exact], subject_filter_query="aircraft window rounded corner")
assert selected["source_id"] == 1
vd.register_visual_evidence(generic, visible_components=["aircraft"], source="vision", definitive=True)
assert hv._hook_fallback_quality(generic, "aircraft window rounded corner")["label"] in {
    "SAME_DOMAIN_CONTEXTUAL", "LAST_RESORT"
}

print("PASS: causal narrative A-G, #20 H, #21 I, #23 J-K, #24-#29 compatibility; no Sora/API calls")