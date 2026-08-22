from pathlib import Path
import hashlib
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
assert "AVIATION_SPECIFICITY_PROJECTION_V3" in source_text
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

# A: production counterexample shape. Existing structured detail is projected
# verbatim into Gate-visible reveal with zero projection API calls.
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

# V1 must not be called when a grounded specificity field already exists.
def v1_must_not_run(*args, **kwargs):
    raise AssertionError("V1 schema repair must not run for existing specificity")

repair_globals["_aviation_specificity_schema_repair_v1"] = v1_must_not_run
result = ce._repair_aviation_specificity_output_if_needed(base_payload, model="mock-model")
assert result["status"] == "SELECTED", result
assert result["winner"]["tradeoff"] == base["tradeoff"]
assert base["tradeoff"] in result["winner"]["micro_narrative"]["reveal"]
assert result["winner"]["topic"] == base["topic"]
assert result["winner"]["core_question"] == base["core_question"]
ok, reason = ce.aviation_candidate_quality_check(result["winner"])
assert ok, reason

# B: missing specificity delegates exactly once to V1, then V3 performs only a
# deterministic exact-copy projection. This is the production regression for the
# V2 'introduced ungrounded specificity' loop.
missing = winner(
    topic="비행기 착륙장치의 구조적 설계",
    question="왜 비행기 착륙장치는 특정한 형태로 설계될까?",
    reveal="여러 바퀴가 하중을 나누지만 장치 중량과 복잡성도 늘어난다.",
)
missing_payload = {"status": "SELECTED", "winner": missing, "runner_up": None}
v1_calls = []

def fake_v1(data, *, model):
    v1_calls.append(model)
    repaired = dict(data)
    repaired_winner = dict(data["winner"])
    repaired_winner["tradeoff"] = "여러 바퀴가 하중을 나누지만 장치 중량과 복잡성도 늘어난다"
    repaired["winner"] = repaired_winner
    return repaired

repair_globals["_aviation_specificity_schema_repair_v1"] = fake_v1
repaired = ce._repair_aviation_specificity_output_if_needed(missing_payload, model="mock-model")
assert v1_calls == ["mock-model"], v1_calls
assert repaired["status"] == "SELECTED", repaired
assert repaired["winner"]["tradeoff"] in repaired["winner"]["micro_narrative"]["reveal"]
ok, reason = ce.aviation_candidate_quality_check(repaired["winner"])
assert ok, reason

# C: if V1 cannot recover a grounded detail, propagate REGENERATE; V3 must never
# fabricate a specificity field itself.
def fake_v1_fail(data, *, model):
    return {
        "status": "REGENERATE",
        "reason": "aviation specificity repair could not recover a grounded concrete field",
    }

repair_globals["_aviation_specificity_schema_repair_v1"] = fake_v1_fail
failed = ce._repair_aviation_specificity_output_if_needed(missing_payload, model="mock-model")
assert failed["status"] == "REGENERATE"
assert "could not recover" in failed["reason"]

# D: already-good aviation Candidate is an identity no-op.
good = winner(
    topic="여러 바퀴로 하중을 나누는 비행기 착륙장치",
    question="왜 착륙장치는 여러 바퀴로 하중을 나눌까?",
    reveal="여러 바퀴로 하중을 나누는 대신 착륙장치 중량과 복잡성이 늘어나는 trade-off다.",
    tradeoff="여러 바퀴로 하중을 나누는 대신 착륙장치 중량과 복잡성이 늘어나는 trade-off",
)
good_payload = {"status": "SELECTED", "winner": good, "runner_up": None}
assert ce._repair_aviation_specificity_output_if_needed(good_payload, model="mock-model") is good_payload

# E: non-aviation execution is untouched.
os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
assert ce._repair_aviation_specificity_output_if_needed(base_payload, model="mock-model") is base_payload

# F: Candidate Gate and production policy remain unchanged.
assert gate_before == gate_after
workflow_text = (ROOT / ".github" / "workflows" / "main.yml").read_text(encoding="utf-8")
assert 'V3_MAX_API_CALLS: "60"' in workflow_text
assert 'V3_MAX_COST_USD: "0.05"' in workflow_text
assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in workflow_text

print("PASS: aviation specificity projection V3 A-F; deterministic projection, V1 preserved, Gate/budget/Sora unchanged")
