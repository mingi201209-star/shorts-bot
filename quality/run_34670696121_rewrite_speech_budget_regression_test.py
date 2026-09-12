import copy

from quality import rewrite_engine
from quality.korean_speech_style import validate_script_speech_style


AUTHORITY_CASUAL_TEXT = "현대 항공기의 창문은 둥근 형태로 되어 있는데요."
AUTHORITY_REPAIRED_TEXT = "현대 항공기의 창문은 둥근 형태로 되어 있습니다."


def _script(text):
    return {
        "topic": "비행기 창문 모서리는 왜 둥글까",
        "category": "aviation",
        "angle": "shape and stress",
        "core_question": "비행기 창문 모서리는 왜 둥글까",
        "micro_narrative": {"hook": "창문 모서리에는 이유가 있습니다."},
        "fact_check_focus": ["window shape"],
        "visual_proof": ["rounded vs angular"],
        "candidate_selection_reason": "fixed topic",
        "scenes": [
            {
                "scene_id": 1,
                "text": text,
                "keyword": "aircraft rounded window",
                "visual_goal": "둥근 창문을 보여줍니다.",
                "visual_type": "still",
                "owned_claim_id": "rounded_window_stress_distribution",
            }
        ],
    }


def _consensus(domain):
    return {
        "domain_summaries": {
            domain: {
                "score": 6.0,
                "confidence": 1.0,
                "critical_risk": domain == "fact",
                "disagreement": 0.0,
                "issues": ["근거 표현을 완화해야 합니다"] if domain == "fact" else ["첫 장면이 단순 설명으로 시작합니다"],
            }
        }
    }


def _assert_scene_contract_unchanged(before, after):
    for field in ("keyword", "visual_goal", "visual_type", "owned_claim_id"):
        assert after["scenes"][0][field] == before["scenes"][0][field], field
    for field in rewrite_engine.IMMUTABLE_CANDIDATE_FIELDS:
        assert after.get(field) == before.get(field), field


def case_a_exact_run_519_counterexample_repairs_without_second_llm_call():
    original = _script("비행기 창문 모서리는 둥글게 설계되어 있습니다.")
    rewritten = _script(AUTHORITY_CASUAL_TEXT)
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return copy.deepcopy(rewritten)

    old_call = rewrite_engine._run_rewrite_call
    try:
        rewrite_engine._run_rewrite_call = fake_call
        result = rewrite_engine.rewrite_script(original, _consensus("hook"), model="gpt-4o-mini")
    finally:
        rewrite_engine._run_rewrite_call = old_call

    assert len(calls) == 1, f"speech-only recovery spent {len(calls)} LLM calls"
    actual = result["script_data"]
    assert actual["scenes"][0]["text"] == AUTHORITY_REPAIRED_TEXT
    valid, reason = validate_script_speech_style(actual)
    assert valid, reason
    _assert_scene_contract_unchanged(rewritten, actual)


def case_b_unrepairable_nonfact_casual_rewrite_fails_closed_without_second_call():
    original = _script("비행기 창문 모서리는 둥글게 설계되어 있습니다.")
    rewritten = _script("이 차이가 정말 중요하네요.")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return copy.deepcopy(rewritten)

    old_call = rewrite_engine._run_rewrite_call
    try:
        rewrite_engine._run_rewrite_call = fake_call
        result = rewrite_engine.rewrite_script(original, _consensus("hook"), model="gpt-4o-mini")
    finally:
        rewrite_engine._run_rewrite_call = old_call

    assert len(calls) == 1, f"unrepairable non-FACT speech spent {len(calls)} calls"
    assert result["script_data"] == original


def case_c_fact_owned_bounded_second_attempt_is_preserved():
    original = _script("근거 범위 안에서 설명합니다.")
    first = _script("이 설명은 조금 과장되어 있네요.")
    second = _script("근거 범위 안에서 표현을 완화했습니다.")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return copy.deepcopy(first if len(calls) == 1 else second)

    old_call = rewrite_engine._run_rewrite_call
    old_persistent = rewrite_engine.find_persistent_fact_issues
    try:
        rewrite_engine._run_rewrite_call = fake_call
        rewrite_engine.find_persistent_fact_issues = lambda *args, **kwargs: []
        result = rewrite_engine.rewrite_script(original, _consensus("fact"), model="gpt-4o-mini")
    finally:
        rewrite_engine._run_rewrite_call = old_call
        rewrite_engine.find_persistent_fact_issues = old_persistent

    assert rewrite_engine.FACT_REWRITE_MAX_ATTEMPTS == 2
    assert len(calls) == 2, f"FACT bounded retry changed: {len(calls)} calls"
    assert result["script_data"]["scenes"][0]["text"] == second["scenes"][0]["text"]


def case_d_already_formal_rewrite_stays_one_call():
    original = _script("원래 문장입니다.")
    rewritten = _script("각진 모서리에는 응력이 집중될 수 있습니다.")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return copy.deepcopy(rewritten)

    old_call = rewrite_engine._run_rewrite_call
    try:
        rewrite_engine._run_rewrite_call = fake_call
        result = rewrite_engine.rewrite_script(original, _consensus("hook"), model="gpt-4o-mini")
    finally:
        rewrite_engine._run_rewrite_call = old_call

    assert len(calls) == 1
    assert result["script_data"] == rewritten


def case_e_formal_question_exception_remains_valid():
    original = _script("원래 문장입니다.")
    rewritten = _script("그 차이는 어디서 생길까요?")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return copy.deepcopy(rewritten)

    old_call = rewrite_engine._run_rewrite_call
    try:
        rewrite_engine._run_rewrite_call = fake_call
        result = rewrite_engine.rewrite_script(original, _consensus("hook"), model="gpt-4o-mini")
    finally:
        rewrite_engine._run_rewrite_call = old_call

    assert len(calls) == 1
    assert result["script_data"] == rewritten


def case_f_repair_is_narrow_and_does_not_guess_ambiguous_casual_endings():
    for casual in ("중요하네요.", "그렇죠.", "왜 그런가요?"):
        candidate = _script(casual)
        repaired = rewrite_engine._repair_rewrite_speech_style(candidate)
        assert repaired is None, f"ambiguous ending was rewritten: {casual}"


def case_g_budget_and_retry_contracts_are_not_relaxed():
    source = open("ci_speech_style_hotfix.py", encoding="utf-8").read()
    assert "FACT_REWRITE_MAX_ATTEMPTS if fact_guard_enabled else 1" in source
    assert "FACT_REWRITE_MAX_ATTEMPTS if fact_guard_enabled else 2" not in source
    assert "V3_MAX_COST_USD" not in source
    assert "V3_MAX_API_CALLS" not in source
    assert "MAX_REWRITES" not in source
    assert "MAX_TOPIC_REGENERATIONS" not in source


def main():
    case_a_exact_run_519_counterexample_repairs_without_second_llm_call()
    case_b_unrepairable_nonfact_casual_rewrite_fails_closed_without_second_call()
    case_c_fact_owned_bounded_second_attempt_is_preserved()
    case_d_already_formal_rewrite_stays_one_call()
    case_e_formal_question_exception_remains_valid()
    case_f_repair_is_narrow_and_does_not_guess_ambiguous_casual_endings()
    case_g_budget_and_retry_contracts_are_not_relaxed()
    print("PASS: Run 34670696121 rewrite speech budget regression")


if __name__ == "__main__":
    main()
