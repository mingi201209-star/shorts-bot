from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content.candidate_recovery import (
    make_recovery_record,
    recovery_eligibility,
    select_best_recovery,
)


def candidate(topic="날개 끝 윙렛의 실제 역할", reveal="날개 끝 와류를 줄여 유도항력을 낮춘다"):
    return {
        "topic": topic,
        "angle": "익숙한 구조의 구체적인 설계 이유",
        "core_question": "왜 날개 끝은 위로 꺾여 있을까?",
        "micro_narrative": {
            "hook": "날개 끝이 위로 꺾인 건 장식이 아닙니다.",
            "core_question": "왜 굳이 이렇게 만들었을까요?",
            "reveal": reveal,
            "payoff": "작은 끝단 구조가 비행 전체의 에너지 손실을 줄입니다.",
        },
        "fact_check_focus": ["winglets reduce induced drag under relevant conditions"],
        "visual_proof": ["visible upturned wingtip"],
        "selection_reason": "구조와 메커니즘을 직접 시각화할 수 있습니다.",
    }


def test_soft_editorial_reject_is_recoverable():
    gate = {
        "status": "REGENERATE",
        "reason": "두 번째 인과 단계가 약하고 payoff를 더 구체화해야 합니다.",
    }
    eligible, reason = recovery_eligibility(candidate(), gate)
    assert eligible is True
    assert reason == "soft_editorial_reject"


def test_predictable_candidate_is_never_recoverable():
    gate = {
        "status": "REGENERATE",
        "reason": "결론이 너무 예상 가능해서 시청자가 답을 이미 짐작할 수 있습니다.",
    }
    eligible, reason = recovery_eligibility(candidate(), gate)
    assert eligible is False
    assert reason == "hard_novelty_reject"
    assert make_recovery_record(candidate(), gate, attempt=7) is None


def test_low_novelty_candidate_cannot_revive_after_exhaustion():
    predictable_gate = {
        "status": "REGENERATE",
        "reason": "의외성이 부족하고 결론이 뻔합니다.",
    }
    records = []
    for attempt in range(1, 8):
        record = make_recovery_record(
            candidate(topic=f"예측 가능한 후보 {attempt}"),
            predictable_gate,
            attempt=attempt,
        )
        if record is not None:
            records.append(record)

    assert records == []
    assert select_best_recovery(records) is None


def test_hard_grounding_reject_is_never_recoverable():
    gate = {
        "status": "REGENERATE",
        "reason": "핵심 인과관계에 근거가 없어 검증 불가능합니다.",
    }
    eligible, reason = recovery_eligibility(candidate(), gate)
    assert eligible is False
    assert reason == "hard_grounding_reject"


def test_placeholder_is_never_recoverable():
    bad = candidate(topic="placeholder candidate")
    gate = {
        "status": "REGENERATE",
        "reason": "Payoff가 약합니다.",
    }
    record = make_recovery_record(bad, gate, attempt=1)
    assert record is None


def test_best_grounded_candidate_is_selected_deterministically():
    gate = {
        "status": "REGENERATE",
        "reason": "Payoff의 인과 연결을 한 단계 더 구체화해야 합니다.",
    }
    weaker = candidate(
        topic="약한 후보",
        reveal="구조가 공기 흐름에 영향을 줍니다.",
    )
    weaker["fact_check_focus"] = []
    weaker["visual_proof"] = []

    stronger = candidate(
        topic="강한 후보",
        reveal="압력 차로 생기는 끝단 와류를 줄여 유도항력 손실을 낮춥니다.",
    )

    records = [
        make_recovery_record(weaker, gate, attempt=1),
        make_recovery_record(stronger, gate, attempt=2),
    ]
    selected = select_best_recovery(records)
    assert selected is not None
    assert selected["candidate"]["topic"] == "강한 후보"


def test_no_recoverable_candidate_stays_terminal():
    assert select_best_recovery([]) is None
    assert select_best_recovery([None]) is None


def _load_supply_module():
    # This focused regression intentionally has no third-party install step.
    # The wrapper behavior below stubs all model calls, so a minimal import-only
    # openai module is enough to load candidate_explorer without network access.
    if "openai" not in sys.modules:
        fake_openai = types.ModuleType("openai")
        fake_openai.api_key = None
        sys.modules["openai"] = fake_openai

    import content.candidate_explorer as explorer

    assert hasattr(explorer, "_candidate_supply_reason_is_zero_usable"), (
        "candidate supply recovery hotfix was not applied before regression"
    )
    return explorer


def test_supply_recovery_does_not_run_for_normal_selected():
    explorer = _load_supply_module()
    explorer._reset_candidate_supply_recovery_for_tests()

    normal = {
        "status": "SELECTED",
        "winner": candidate(),
        "runner_up": None,
    }
    calls = {"recovery": 0}
    original = explorer._original_explore_candidates_before_supply_recovery
    recovery = explorer._run_candidate_supply_recovery

    try:
        explorer._original_explore_candidates_before_supply_recovery = (
            lambda *args, **kwargs: normal
        )

        def forbidden_recovery(*args, **kwargs):
            calls["recovery"] += 1
            raise AssertionError("normal SELECTED must not spend supply recovery")

        explorer._run_candidate_supply_recovery = forbidden_recovery
        result = explorer.explore_candidates({"category": "항공", "topic": "객실 구조"})
        assert result is normal
        assert calls["recovery"] == 0
    finally:
        explorer._original_explore_candidates_before_supply_recovery = original
        explorer._run_candidate_supply_recovery = recovery


def test_zero_supply_gets_exactly_one_recovery_and_stays_validated():
    explorer = _load_supply_module()
    explorer._reset_candidate_supply_recovery_for_tests()

    zero = {
        "status": "REGENERATE",
        "reason": "usable grounded Candidate가 0개",
    }
    recovered = explorer.validate_explorer_output({
        "status": "SELECTED",
        "winner": candidate(topic="비행기 창문 아래 작은 구멍의 역할"),
        "runner_up": None,
    })

    calls = {"recovery": 0}
    original = explorer._original_explore_candidates_before_supply_recovery
    recovery = explorer._run_candidate_supply_recovery

    try:
        explorer._original_explore_candidates_before_supply_recovery = (
            lambda *args, **kwargs: zero
        )

        def bounded_recovery(*args, **kwargs):
            calls["recovery"] += 1
            return recovered

        explorer._run_candidate_supply_recovery = bounded_recovery
        result = explorer.explore_candidates({"category": "항공", "topic": "객실 구조"})
        assert result["status"] == "SELECTED"
        assert result["winner"]["topic"] == "비행기 창문 아래 작은 구멍의 역할"
        assert calls["recovery"] == 1
    finally:
        explorer._original_explore_candidates_before_supply_recovery = original
        explorer._run_candidate_supply_recovery = recovery


def test_supply_recovery_is_one_per_generation_and_fails_closed_after_spend():
    explorer = _load_supply_module()
    explorer._reset_candidate_supply_recovery_for_tests()

    zero = {
        "status": "REGENERATE",
        "reason": "usable grounded Candidate가 0개",
    }
    calls = {"recovery": 0}
    original = explorer._original_explore_candidates_before_supply_recovery
    recovery = explorer._run_candidate_supply_recovery

    try:
        explorer._original_explore_candidates_before_supply_recovery = (
            lambda *args, **kwargs: zero
        )

        def still_empty(*args, **kwargs):
            calls["recovery"] += 1
            return zero

        explorer._run_candidate_supply_recovery = still_empty
        first = explorer.explore_candidates({"category": "항공", "topic": "공항 시스템"})
        second = explorer.explore_candidates({"category": "항공", "topic": "착륙장치"})

        assert first["status"] == "REGENERATE"
        assert second["status"] == "REGENERATE"
        assert calls["recovery"] == 1
    finally:
        explorer._original_explore_candidates_before_supply_recovery = original
        explorer._run_candidate_supply_recovery = recovery


def test_supply_recovery_only_triggers_on_zero_usable_reason():
    explorer = _load_supply_module()
    assert explorer._candidate_supply_reason_is_zero_usable({
        "status": "REGENERATE",
        "reason": "usable grounded Candidate가 0개",
    }) is True
    assert explorer._candidate_supply_reason_is_zero_usable({
        "status": "REGENERATE",
        "reason": "결론이 너무 예상 가능합니다.",
    }) is False


def main():
    test_soft_editorial_reject_is_recoverable()
    print("CASE A soft editorial recovery: PASS")
    test_predictable_candidate_is_never_recoverable()
    print("CASE B predictable candidate exclusion: PASS")
    test_low_novelty_candidate_cannot_revive_after_exhaustion()
    print("CASE C exhausted low-novelty recovery stays terminal: PASS")
    test_hard_grounding_reject_is_never_recoverable()
    print("CASE D hard grounding exclusion: PASS")
    test_placeholder_is_never_recoverable()
    print("CASE E placeholder exclusion: PASS")
    test_best_grounded_candidate_is_selected_deterministically()
    print("CASE F deterministic strongest selection: PASS")
    test_no_recoverable_candidate_stays_terminal()
    print("CASE G terminal without recoverable candidate: PASS")
    test_supply_recovery_does_not_run_for_normal_selected()
    print("CASE H normal SELECTED spends zero supply calls: PASS")
    test_zero_supply_gets_exactly_one_recovery_and_stays_validated()
    print("CASE I zero supply gets one validated recovery: PASS")
    test_supply_recovery_is_one_per_generation_and_fails_closed_after_spend()
    print("CASE J one-call bound and fail-close: PASS")
    test_supply_recovery_only_triggers_on_zero_usable_reason()
    print("CASE K trigger reason remains narrow: PASS")
    print("CANDIDATE GROUNDED RECOVERY REGRESSION: PASS")


if __name__ == "__main__":
    main()
