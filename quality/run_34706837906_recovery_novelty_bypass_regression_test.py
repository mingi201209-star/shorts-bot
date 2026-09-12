#!/usr/bin/env python3
"""Regression for Production Run 34706837906.

The pre-Writer novelty fix correctly rejected a trusted aviation Candidate at
4/10 before GPT-5.6 Sol, but bounded grounded recovery later revived that exact
PREWRITER_NOVELTY_LOW result as a generic soft-editorial Candidate and sent it
to Script Generator. This regression proves structured pre-Writer novelty
rejections can never enter the recovery pool while ordinary grounded soft
editorial recovery remains intact.
"""

from __future__ import annotations

from pathlib import Path

from content.candidate_recovery import (
    make_recovery_record,
    recovery_eligibility,
    select_best_recovery,
)


ROOT = Path(__file__).resolve().parents[1]


def _trusted_candidate(topic: str = "비행기 엔진의 나셀 끝에 톱니 모양 가장자리"):
    canonical = "jet engine nacelle/nozzle chevrons"
    return {
        "topic": topic,
        "angle": "엔진 배기와 외부 흐름 경계에서 생기는 소음 제약",
        "core_question": "왜 비행기 엔진 나셀 끝이 톱니 모양으로 디자인되었을까?",
        "micro_narrative": {
            "hook": "엔진 뒤 톱니는 장식이 아니라 흐름을 나눕니다.",
            "core_question": "왜 가장자리를 매끈하게 두지 않았을까요?",
            "reveal": "톱니 가장자리가 서로 다른 흐름이 섞이는 방식을 바꿉니다.",
            "payoff": "그 변화가 특정 제트 소음을 줄이는 데 도움을 줍니다.",
        },
        "fact_check_focus": ["chevron flow mixing and jet-noise relation"],
        "visual_proof": ["visible nacelle/nozzle chevron edge"],
        "selection_reason": "구조를 실제 화면에서 확인할 수 있습니다.",
        "subject_kind": "physical_entity",
        "canonical_subject": canonical,
        "subject_identity_confidence": 0.98,
        "grounding_evidence": [],
        "_trusted_grounding_evidence": [
            {
                "evidence_type": "source_backed_identity",
                "supports_subject": canonical,
                "source": "trusted fixture source",
                "detail": "fixture establishes physical chevron identity",
            }
        ],
    }


def _run_34706837906_gate_result(failure_type="PREWRITER_NOVELTY_LOW"):
    return {
        "status": "REGENERATE",
        "failure_type": failure_type,
        "reason": (
            "Writer 실행 전 Novelty Judge가 기존 최소 기준 미달을 확인했습니다: "
            "4.00 < 5.00. 비싼 Writer를 사용하지 않고 새 Candidate를 탐색합니다."
        ),
    }


def test_exact_low_novelty_result_never_enters_recovery_pool():
    candidate = _trusted_candidate()
    gate = _run_34706837906_gate_result()
    eligible, reason = recovery_eligibility(candidate, gate)
    assert eligible is False
    assert reason == "prewriter_novelty_reject"
    assert make_recovery_record(candidate, gate, attempt=1) is None
    print("CASE A exact PREWRITER_NOVELTY_LOW is terminal for recovery: PASS")


def test_same_family_repeat_is_also_terminal_for_recovery():
    candidate = _trusted_candidate(topic="비행기 엔진 뒤쪽 톱니 디자인")
    gate = _run_34706837906_gate_result("PREWRITER_NOVELTY_FAMILY_REPEAT")
    eligible, reason = recovery_eligibility(candidate, gate)
    assert eligible is False
    assert reason == "prewriter_novelty_reject"
    assert make_recovery_record(candidate, gate, attempt=7) is None
    print("CASE B PREWRITER_NOVELTY_FAMILY_REPEAT cannot revive: PASS")


def test_future_structured_prewriter_novelty_failures_fail_closed():
    candidate = _trusted_candidate()
    gate = _run_34706837906_gate_result("PREWRITER_NOVELTY_FUTURE_REASON")
    eligible, reason = recovery_eligibility(candidate, gate)
    assert eligible is False
    assert reason == "prewriter_novelty_reject"
    print("CASE C PREWRITER_NOVELTY_* authority is preserved: PASS")


def test_normal_grounded_soft_editorial_recovery_is_unchanged():
    candidate = _trusted_candidate(topic="별도 grounded 후보")
    gate = {
        "status": "REGENERATE",
        "reason": "Payoff의 인과 연결을 한 단계 더 구체화해야 합니다.",
    }
    eligible, reason = recovery_eligibility(candidate, gate)
    assert eligible is True
    assert reason == "soft_editorial_reject"
    record = make_recovery_record(candidate, gate, attempt=2)
    assert record is not None
    assert select_best_recovery([record]) is record
    print("CASE D ordinary grounded soft-editorial recovery remains available: PASS")


def test_mixed_pool_cannot_select_run_34706837906_candidate():
    blocked = make_recovery_record(
        _trusted_candidate(),
        _run_34706837906_gate_result(),
        attempt=1,
    )
    safe_candidate = _trusted_candidate(topic="별도 복구 가능 후보")
    safe_gate = {
        "status": "REGENERATE",
        "reason": "설명의 깊이를 조금 더 보강해야 합니다.",
    }
    safe = make_recovery_record(safe_candidate, safe_gate, attempt=2)
    records = [record for record in (blocked, safe) if record is not None]
    selected = select_best_recovery(records)
    assert blocked is None
    assert selected is not None
    assert selected["candidate"]["topic"] == "별도 복구 가능 후보"
    print("CASE E blocked novelty Candidate cannot win mixed recovery pool: PASS")


def test_both_main_recovery_sites_use_make_recovery_record_authority():
    installer = (ROOT / "ci_candidate_grounded_recovery_hotfix.py").read_text(
        encoding="utf-8"
    )
    # There are two production composition variants (legacy and fixed-topic
    # aware). Both must create pool entries through make_recovery_record rather
    # than appending raw rejected Winners.
    assert installer.count("recovery_record = make_recovery_record(") >= 2
    assert "recovery_candidates.append(recovery_record)" in installer
    assert 'recovered = select_best_recovery(recovery_candidates)' in installer
    print("CASE F production recovery sites preserve helper authority: PASS")


def test_limits_and_writer_routing_are_unchanged():
    workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    router = (ROOT / "content/script_engine_v2_runner.py").read_text(encoding="utf-8")
    recovery = (ROOT / "content/candidate_recovery.py").read_text(encoding="utf-8")

    assert 'V3_MAX_API_CALLS: "60"' in workflow
    assert 'V3_MAX_COST_USD: "0.05"' in workflow
    assert "gpt-5.6-sol" in router.lower() or "gpt-5.6-sol" in (
        ROOT / "config.py"
    ).read_text(encoding="utf-8").lower()

    for forbidden in (
        "authorize_call(",
        "chat.completions",
        "responses.create",
        "max_topic_regenerations =",
        "max_script_attempts =",
        "v3_max_cost_usd =",
        "v3_max_api_calls =",
    ):
        assert forbidden not in recovery.lower(), forbidden

    print("CASE G API/cost/retry/Writer contracts remain unchanged: PASS")


def main():
    test_exact_low_novelty_result_never_enters_recovery_pool()
    test_same_family_repeat_is_also_terminal_for_recovery()
    test_future_structured_prewriter_novelty_failures_fail_closed()
    test_normal_grounded_soft_editorial_recovery_is_unchanged()
    test_mixed_pool_cannot_select_run_34706837906_candidate()
    test_both_main_recovery_sites_use_make_recovery_record_authority()
    test_limits_and_writer_routing_are_unchanged()
    print("RUN 34706837906 RECOVERY NOVELTY BYPASS REGRESSION: PASS")


if __name__ == "__main__":
    main()
