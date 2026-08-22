from pathlib import Path
import hashlib
import json
import os
import runpy
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# Candidate Gate must remain byte-for-byte unchanged by this hotfix.
gate_path = ROOT / "content" / "candidate_gate.py"
gate_before = hashlib.sha256(gate_path.read_bytes()).hexdigest()

subprocess.run([sys.executable, "ci_aviation_candidate_context_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_aviation_candidate_specificity_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_aviation_specificity_output_repair_hotfix.py"], check=True)

gate_after = hashlib.sha256(gate_path.read_bytes()).hexdigest()
assert gate_before == gate_after, "Candidate Gate implementation changed"

# Execute the exact runtime-patched production source, bypassing package/pyc cache.
patched_source = ROOT / "content" / "candidate_explorer.py"
source_text = patched_source.read_text(encoding="utf-8")
assert "AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V1" in source_text
assert "AVIATION_SPECIFICITY_OUTPUT_REPAIR_V1" in source_text
namespace = runpy.run_path(str(patched_source), run_name="candidate_explorer_regression_runtime")
ce = types.SimpleNamespace(**namespace)
assert hasattr(ce, "aviation_candidate_quality_check")
assert hasattr(ce, "_repair_aviation_specificity_output_if_needed")


def candidate(
    *,
    topic,
    question,
    reveal,
    angle="구체적인 항공 설계 제약",
    specific_observation=None,
    constraint=None,
    counterintuitive_result=None,
    tradeoff=None,
    concrete_condition=None,
):
    value = {
        "topic": topic,
        "angle": angle,
        "core_question": question,
        "micro_narrative": {
            "hook": topic,
            "core_question": question,
            "reveal": reveal,
            "payoff": reveal,
        },
        "fact_check_focus": [],
        "visual_proof": ["aircraft physical detail"],
        "selection_reason": "구체적 조건과 인과관계를 한 줄기로 설명할 수 있다.",
    }
    optional = {
        "specific_observation": specific_observation,
        "constraint": constraint,
        "counterintuitive_result": counterintuitive_result,
        "tradeoff": tradeoff,
        "concrete_condition": concrete_condition,
    }
    value.update({k: v for k, v in optional.items() if v})
    return value


# A: broad generic why-design topic is rejected by Explorer quality check.
broad = candidate(
    topic="비행기 객실 창문 위치",
    question="비행기 창문이 왜 특정 위치일까?",
    reveal="객실 설계에 맞는 위치이기 때문이다.",
)
ok, reason = ce.aviation_candidate_quality_check(broad)
assert not ok and "concrete" in reason.lower(), (ok, reason)

# B: a generic safety-only reveal is rejected even if a superficial detail field exists.
generic_safety = candidate(
    topic="비행기 객실 조명 색상",
    question="비행기 객실 조명이 비상 상황에서 왜 특정 색으로 바뀔까?",
    reveal="승객의 안전을 높이기 위해서다.",
    specific_observation="비상 상황에서 바뀌는 객실 조명 색상",
)
ok, reason = ce.aviation_candidate_quality_check(generic_safety)
assert not ok and "generic benefit reveal" in reason, (ok, reason)

# C: concrete structure + condition + counterintuitive result passes.
specific = candidate(
    topic="강한 측풍 착륙에서 비행기 착륙장치 연결부의 움직임",
    question="강한 측풍 착륙에서 착륙장치 연결부가 왜 완전히 고정되지 않을까?",
    reveal="강한 측풍 착륙 조건에서는 연결부의 제한된 움직임이 특정 방향 하중이 한 지점에 집중되는 것을 피하는 구조적 역할을 한다.",
    specific_observation="착륙장치 연결부의 제한된 움직임",
    concrete_condition="강한 측풍 착륙 조건",
    counterintuitive_result="완전 고정보다 제한된 움직임이 특정 방향 하중 집중을 피한다",
)
ok, reason = ce.aviation_candidate_quality_check(specific)
assert ok, reason

# D: a concrete trade-off candidate passes.
tradeoff = candidate(
    topic="비행기 날개 끝 장치가 구조 중량 증가를 감수하는 trade-off",
    question="비행기 날개 끝 장치는 왜 구조 중량 증가를 감수하면서도 추가될까?",
    reveal="날개 끝 장치는 구조 중량 증가라는 손해를 감수하는 대신 비행 중 날개 끝 흐름에서 얻는 이점을 택하는 trade-off다.",
    tradeoff="구조 중량 증가를 감수하는 대신 날개 끝 흐름에서 이점을 얻는 trade-off",
    specific_observation="날개 끝에 추가된 별도 구조물",
)
ok, reason = ce.aviation_candidate_quality_check(tradeoff)
assert ok, reason

# E: downstream-rejected topics feed the next attempt with semantic diversity guidance.
os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
context = ce.build_execution_context(
    {"category": "항공", "topic": "엔진과 흡기 주변의 설계"},
    rejected_topics=["비행기 엔진의 흡기 시스템 설계"],
)
assert "비행기 엔진의 흡기 시스템 설계" in context
assert "같은 semantic pattern" in context
assert "왜 [부품]이 특정 모양/배치/위치인가?" in context
assert "retry 횟수나 API budget을 늘리지 말고" in context

# F: aviation scope stays inside aviation.
outside = candidate(
    topic="도시 다리의 진동 구조",
    question="강풍 조건에서 다리 구조가 왜 움직일까?",
    reveal="강풍 조건에서 구조가 제한적으로 움직이며 하중을 분산한다.",
    angle="도시 교량의 구조 제약",
    constraint="강풍 조건",
)
ok, _ = ce.aviation_candidate_quality_check(outside)
assert not ok
assert ce.aviation_scope_compatible(specific)

# G: default/non-aviation Explorer keeps the pre-existing output behavior.
os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
default_payload = {
    "status": "SELECTED",
    "winner": broad,
    "runner_up": None,
}
validated = ce.validate_explorer_output(default_payload)
assert validated["status"] == "SELECTED"
assert validated["winner"]["topic"] == broad["topic"]

# Aviation mode applies the extra contract before Candidate Gate.
os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
rejected = ce.validate_explorer_output(default_payload)
assert rejected["status"] == "REGENERATE"

# H: Candidate Gate source and policy are unchanged; retry/API limits are untouched.
assert gate_before == gate_after
main_text = (ROOT / "main.py").read_text(encoding="utf-8")
assert "MAX_TOPIC_REGENERATIONS = 1" in main_text
assert "evaluate_candidate(" in main_text

# I: aviation SELECTED output contract now requires >=1 grounded specificity field.
assert "winner에는 아래 5개 중" in source_text
assert "최소 1개 반드시 포함" in source_text
assert "근거 없는 값을 만들어 필드 수를 채우는 것은 금지" in source_text

# J: a field-missing but already-concrete winner gets exactly one bounded schema repair.
repair_base = candidate(
    topic="강한 측풍 착륙에서 비행기 착륙장치 연결부의 움직임",
    question="강한 측풍 착륙에서 착륙장치 연결부가 왜 완전히 고정되지 않을까?",
    reveal="강한 측풍 착륙 조건에서는 연결부의 제한된 움직임이 하중 집중을 피한다.",
)
repair_payload = {"status": "SELECTED", "winner": repair_base, "runner_up": None}
repaired_winner = dict(repair_base)
repaired_winner["concrete_condition"] = "강한 측풍 착륙 조건"
repair_response_payload = {
    "status": "SELECTED",
    "winner": repaired_winner,
    "runner_up": None,
}

calls = []


def fake_create(**kwargs):
    calls.append(kwargs)
    return types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(
                message=types.SimpleNamespace(
                    content=json.dumps(repair_response_payload, ensure_ascii=False)
                )
            )
        ]
    )


namespace["authorize_call"] = lambda model: 17
namespace["record_usage"] = lambda model, response: {"cost_usd": 0.0, "over_budget": False}
namespace["print_budget_status"] = lambda: None
namespace["openai"] = types.SimpleNamespace(
    chat=types.SimpleNamespace(
        completions=types.SimpleNamespace(create=fake_create)
    )
)
repaired = ce._repair_aviation_specificity_output_if_needed(repair_payload, model="mock-model")
assert len(calls) == 1, f"expected exactly one bounded repair call, got {len(calls)}"
assert repaired["winner"]["concrete_condition"] == "강한 측풍 착륙 조건"
for protected in (
    "topic", "angle", "core_question", "micro_narrative",
    "fact_check_focus", "visual_proof", "selection_reason",
):
    assert repaired["winner"][protected] == repair_base[protected]
validated_repair = ce.validate_explorer_output(repaired)
assert validated_repair["status"] == "SELECTED"

# K: no safe concrete detail => repair is allowed to return REGENERATE, never invent.
def fake_regenerate(**kwargs):
    calls.append(kwargs)
    payload = {
        "status": "REGENERATE",
        "reason": "aviation specificity repair could not recover a grounded concrete field",
    }
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps(payload)))]
    )

namespace["openai"] = types.SimpleNamespace(
    chat=types.SimpleNamespace(
        completions=types.SimpleNamespace(create=fake_regenerate)
    )
)
before_calls = len(calls)
failed_repair = ce._repair_aviation_specificity_output_if_needed(default_payload, model="mock-model")
assert len(calls) == before_calls + 1
assert failed_repair["status"] == "REGENERATE"

# L: non-aviation output never spends a repair call.
os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
before_calls = len(calls)
unchanged = ce._repair_aviation_specificity_output_if_needed(default_payload, model="mock-model")
assert unchanged is default_payload
assert len(calls) == before_calls

# M: repair prompt explicitly forbids fabrication and only copies existing JSON facts.
os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
namespace["openai"] = types.SimpleNamespace(
    chat=types.SimpleNamespace(
        completions=types.SimpleNamespace(create=fake_create)
    )
)
calls.clear()
ce._repair_aviation_specificity_output_if_needed(repair_payload, model="mock-model")
repair_prompt = calls[0]["messages"][1]["content"]
assert "새 사실" in repair_prompt and "추가하지 마라" in repair_prompt
assert "기존 JSON에 이미 명시적으로 표현된 구체 요소만" in repair_prompt
assert calls[0]["temperature"] == 0.0

print("PASS: aviation candidate specificity A-M; bounded repair=1; Candidate Gate unchanged; no paid/Sora calls")
