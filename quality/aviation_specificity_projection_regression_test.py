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

gate_path = ROOT / "content" / "candidate_gate.py"
gate_before = hashlib.sha256(gate_path.read_bytes()).hexdigest()

for script in (
    "ci_aviation_candidate_context_hotfix.py",
    "ci_aviation_candidate_specificity_hotfix.py",
    "ci_aviation_specificity_output_repair_hotfix.py",
    "ci_aviation_specificity_projection_hotfix.py",
):
    subprocess.run([sys.executable, script], check=True)

gate_after = hashlib.sha256(gate_path.read_bytes()).hexdigest()
assert gate_before == gate_after, "Candidate Gate implementation changed"

source = ROOT / "content" / "candidate_explorer.py"
source_text = source.read_text(encoding="utf-8")
assert "AVIATION_SPECIFICITY_PROJECTION_V2" in source_text
ns = runpy.run_path(str(source), run_name="aviation_specificity_projection_runtime")
ce = types.SimpleNamespace(**ns)
repair_globals = ce._repair_aviation_specificity_output_if_needed.__globals__


def winner(*, topic, question, reveal, tradeoff=None, constraint=None):
    value = {
        "topic": topic,
        "angle": "항공기의 구체 설계 trade-off",
        "core_question": question,
        "micro_narrative": {
            "hook": topic,
            "core_question": question,
            "reveal": reveal,
            "payoff": reveal,
        },
        "fact_check_focus": [],
        "visual_proof": ["aircraft physical detail"],
        "selection_reason": "구체 제약과 결과를 짧게 설명할 수 있다.",
    }
    if tradeoff:
        value["tradeoff"] = tradeoff
    if constraint:
        value["constraint"] = constraint
    return value


os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"

# A: production counterexample shape: structured detail exists but Gate-visible text is generic.
base = winner(
    topic="비행기 착륙장치의 구조적 설계",
    question="왜 비행기 착륙장치는 특정한 형태로 설계될까?",
    reveal="착륙 때 안전성을 높이기 위해서다.",
    tradeoff="여러 바퀴로 하중을 나누는 대신 착륙장치 중량과 복잡성이 늘어나는 trade-off",
)
base_payload = {"status": "SELECTED", "winner": base, "runner_up": None}
assert ce._aviation_specificity_repair_needed(base_payload) is True
ok, reason = ce.aviation_candidate_quality_check(base)
assert not ok, reason

projected = dict(base)
projected["topic"] = "여러 바퀴로 하중을 나누지만 중량과 복잡성이 늘어나는 비행기 착륙장치"
projected["core_question"] = "왜 착륙장치는 여러 바퀴로 하중을 나누면서 중량과 복잡성 증가를 감수할까?"
projected["micro_narrative"] = dict(base["micro_narrative"])
projected["micro_narrative"].update(
    {
        "hook": projected["topic"],
        "core_question": projected["core_question"],
        "reveal": "여러 바퀴로 하중을 나누는 대신 착륙장치 중량과 복잡성이 늘어나는 trade-off다.",
        "payoff": "여러 바퀴로 하중을 나누는 대신 착륙장치 중량과 복잡성이 늘어나는 trade-off다.",
    }
)
projected_payload = {"status": "SELECTED", "winner": projected, "runner_up": None}

calls = []


def fake_create(**kwargs):
    calls.append(kwargs)
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(
            content=json.dumps(projected_payload, ensure_ascii=False)
        ))]
    )

repair_globals["authorize_call"] = lambda model: 21
repair_globals["record_usage"] = lambda model, response: {"cost_usd": 0.0, "over_budget": False}
repair_globals["print_budget_status"] = lambda: None
repair_globals["openai"] = types.SimpleNamespace(
    chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
)
result = ce._repair_aviation_specificity_output_if_needed(base_payload, model="mock-model")
assert len(calls) == 1, f"expected one bounded projection call, got {len(calls)}"
assert result["status"] == "SELECTED", result
ok, reason = ce.aviation_candidate_quality_check(result["winner"])
assert ok, reason
assert result["winner"]["tradeoff"] == base["tradeoff"]
for protected in ("angle", "fact_check_focus", "visual_proof", "selection_reason"):
    assert result["winner"][protected] == base[protected]

# B: prompt explicitly forbids invention and demands Gate-visible projection.
prompt = calls[0]["messages"][1]["content"]
assert "새 사실" in prompt and "추가하지 마라" in prompt
assert "topic/core_question/micro_narrative.reveal" in prompt
assert calls[0]["temperature"] == 0.0

# C: newly invented specificity that does not occur in the original JSON is blocked.
invented = dict(projected)
invented.pop("tradeoff", None)
invented["concrete_condition"] = "시속 300km 착륙 조건"
invented_payload = {"status": "SELECTED", "winner": invented, "runner_up": None}


def fake_invent(**kwargs):
    calls.append(kwargs)
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(
            content=json.dumps(invented_payload, ensure_ascii=False)
        ))]
    )

repair_globals["openai"] = types.SimpleNamespace(
    chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_invent))
)
failed = ce._repair_aviation_specificity_output_if_needed(base_payload, model="mock-model")
assert failed["status"] == "REGENERATE"
assert "ungrounded specificity" in failed["reason"]

# D: already-good aviation Candidate spends no repair call.
good_payload = projected_payload
before = len(calls)
unchanged = ce._repair_aviation_specificity_output_if_needed(good_payload, model="mock-model")
assert unchanged is good_payload
assert len(calls) == before

# E: non-aviation execution never spends this repair slot.
os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
before = len(calls)
unchanged = ce._repair_aviation_specificity_output_if_needed(base_payload, model="mock-model")
assert unchanged is base_payload
assert len(calls) == before

# F: policy limits and Candidate Gate remain unchanged.
assert gate_before == gate_after
main_text = (ROOT / "main.py").read_text(encoding="utf-8")
assert "MAX_TOPIC_REGENERATIONS = 1" in main_text
workflow_text = (ROOT / ".github" / "workflows" / "main.yml").read_text(encoding="utf-8")
assert 'V3_MAX_API_CALLS: "60"' in workflow_text
assert 'V3_MAX_COST_USD: "0.05"' in workflow_text
assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in workflow_text

print("PASS: aviation specificity projection A-F; one bounded repair; Gate/budget/Sora policy unchanged")
