from pathlib import Path
import os
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_explorer():
    if "openai" not in sys.modules:
        fake_openai = types.ModuleType("openai")
        fake_openai.api_key = None
        sys.modules["openai"] = fake_openai

    import content.candidate_explorer as explorer_package
    explorer = explorer_package._LEGACY
    assert hasattr(explorer, "_run_35065228877_previous_zero_supply_reason")
    assert hasattr(explorer, "_run_35065228877_previous_recovery_context")
    return explorer


def _build_context_with_stubbed_previous(
    explorer,
    *,
    scope,
    fixed_topic,
    topic_info,
    original_reason,
):
    """Exercise only the new wrapper; production composition is tested separately."""
    previous_scope = os.environ.get("SHORTS_CANDIDATE_SCOPE")
    previous_topic = os.environ.get("SHORTS_TOPIC")
    previous_builder = explorer._run_35065228877_previous_recovery_context

    def previous_context_stub(*args, **kwargs):
        base = "BASE RECOVERY CONTEXT"
        if scope == "aviation":
            base += "\nAVIATION SUPPLY RECOVERY PRECEDENCE"
        return base

    try:
        os.environ["SHORTS_CANDIDATE_SCOPE"] = scope
        os.environ["SHORTS_TOPIC"] = fixed_topic
        explorer._run_35065228877_previous_recovery_context = previous_context_stub
        return explorer._build_candidate_supply_recovery_context(
            topic_info,
            original_reason=original_reason,
        )
    finally:
        explorer._run_35065228877_previous_recovery_context = previous_builder
        if previous_scope is None:
            os.environ.pop("SHORTS_CANDIDATE_SCOPE", None)
        else:
            os.environ["SHORTS_CANDIDATE_SCOPE"] = previous_scope
        if previous_topic is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = previous_topic


def test_exact_run_reason_triggers_existing_single_recovery():
    explorer = _load_explorer()
    result = {
        "status": "REGENERATE",
        "reason": (
            "모든 후보가 실패했습니다. 사라진 생활 기술에 대한 구체적인 질문이나 "
            "메커니즘을 찾지 못했습니다. 또한 역사적 기술의 구체적인 사례와 그 기술이 "
            "사라진 이유를 연결하는 데 필요한 충분한 정보가 부족했습니다."
        ),
    }
    previous = os.environ.get("SHORTS_CANDIDATE_FINAL_ATTEMPT")
    try:
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is True
    finally:
        if previous is None:
            os.environ.pop("SHORTS_CANDIDATE_FINAL_ATTEMPT", None)
        else:
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = previous


def test_editorial_weakness_alone_does_not_spend_recovery():
    explorer = _load_explorer()
    result = {
        "status": "REGENERATE",
        "reason": (
            "질문이 지나치게 넓고 일반적이며 Reveal이 예상 가능한 결론이라 "
            "흥미를 끌기 어렵습니다."
        ),
    }
    assert explorer._candidate_supply_reason_is_zero_usable(result) is False


def test_partial_candidate_failure_is_not_whole_pool_exhaustion():
    explorer = _load_explorer()
    result = {
        "status": "REGENERATE",
        "reason": "한 후보의 구체적인 메커니즘이 부족합니다.",
    }
    assert explorer._candidate_supply_reason_is_zero_usable(result) is False


def test_default_intermediate_shortage_does_not_spend_recovery():
    explorer = _load_explorer()
    previous_scope = os.environ.get("SHORTS_CANDIDATE_SCOPE")
    previous_topic = os.environ.get("SHORTS_TOPIC")
    previous_final = os.environ.get("SHORTS_CANDIDATE_FINAL_ATTEMPT")
    try:
        os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
        os.environ["SHORTS_TOPIC"] = ""
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "0"
        result = {
            "status": "REGENERATE",
            "reason": (
                "모든 후보가 실패했습니다. 탐색 방향에 맞는 구체적인 후보가 없어 "
                "구체적인 질문이나 메커니즘을 명확히 제시할 수 없었습니다."
            ),
        }
        assert explorer._candidate_supply_reason_is_zero_usable(result) is False
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is True
    finally:
        if previous_scope is None:
            os.environ.pop("SHORTS_CANDIDATE_SCOPE", None)
        else:
            os.environ["SHORTS_CANDIDATE_SCOPE"] = previous_scope
        if previous_topic is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = previous_topic
        if previous_final is None:
            os.environ.pop("SHORTS_CANDIDATE_FINAL_ATTEMPT", None)
        else:
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = previous_final


def test_run_35186253060_compact_shortage_is_final_only():
    explorer = _load_explorer()
    previous_final = os.environ.get("SHORTS_CANDIDATE_FINAL_ATTEMPT")
    result = {
        "status": "REGENERATE",
        "reason": "구체적인 대상이나 연결이 부족하여 탐색이 필요함.",
    }
    try:
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "0"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is False
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is True
    finally:
        if previous_final is None:
            os.environ.pop("SHORTS_CANDIDATE_FINAL_ATTEMPT", None)
        else:
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = previous_final


def test_run_35187008225_direction_shortage_is_final_only():
    explorer = _load_explorer()
    previous_final = os.environ.get("SHORTS_CANDIDATE_FINAL_ATTEMPT")
    result = {
        "status": "REGENERATE",
        "reason": "탐색 방향에 맞는 구체적인 후보가 부족합니다.",
    }
    try:
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "0"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is False
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is True
    finally:
        if previous_final is None:
            os.environ.pop("SHORTS_CANDIDATE_FINAL_ATTEMPT", None)
        else:
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = previous_final


def test_run_35188477320_direction_topic_shortage_is_final_only():
    explorer = _load_explorer()
    previous_final = os.environ.get("SHORTS_CANDIDATE_FINAL_ATTEMPT")
    exact_result = {
        "status": "REGENERATE",
        "reason": (
            "모든 후보가 실패했습니다. 탐색 방향에 맞는 구체적인 동물 능력에 대한 "
            "주제를 찾지 못했습니다. 동물의 능력에 대한 질문이 지나치게 넓거나 "
            "일반적이었고, 예상 밖의 메커니즘이나 연결이 부족했습니다."
        ),
    }
    editorial_only = {
        "status": "REGENERATE",
        "reason": (
            "모든 후보가 실패했습니다. 탐색 방향에 맞는 구체적인 설명이 부족했고 "
            "질문이 지나치게 넓고 일반적이었습니다."
        ),
    }
    try:
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "0"
        assert explorer._candidate_supply_reason_is_zero_usable(exact_result) is False
        os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
        assert explorer._candidate_supply_reason_is_zero_usable(exact_result) is True
        assert explorer._candidate_supply_reason_is_zero_usable(editorial_only) is False
    finally:
        if previous_final is None:
            os.environ.pop("SHORTS_CANDIDATE_FINAL_ATTEMPT", None)
        else:
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = previous_final


def test_aviation_and_fixed_topic_keep_legacy_shortage_trigger():
    explorer = _load_explorer()
    result = {
        "status": "REGENERATE",
        "reason": "탐색 방향에 맞는 구체적인 후보가 부족합니다.",
    }
    previous_scope = os.environ.get("SHORTS_CANDIDATE_SCOPE")
    previous_topic = os.environ.get("SHORTS_TOPIC")
    try:
        os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
        os.environ["SHORTS_TOPIC"] = ""
        assert explorer._candidate_supply_reason_is_zero_usable(result) is True

        os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
        os.environ["SHORTS_TOPIC"] = "비행기 창문은 왜 둥글까"
        assert explorer._candidate_supply_reason_is_zero_usable(result) is True
    finally:
        if previous_scope is None:
            os.environ.pop("SHORTS_CANDIDATE_SCOPE", None)
        else:
            os.environ["SHORTS_CANDIDATE_SCOPE"] = previous_scope
        if previous_topic is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = previous_topic


def test_default_automatic_recovery_delegates_editorial_quality_to_gate():
    explorer = _load_explorer()
    context = _build_context_with_stubbed_previous(
        explorer,
        scope="",
        fixed_topic="",
        topic_info={"category": "역사", "topic": "역사 속 사라진 생활 기술"},
        original_reason="모든 후보가 실패했습니다. 구체적인 사례를 찾지 못했습니다.",
    )
    assert "BASE RECOVERY CONTEXT" in context
    assert "DEFAULT AUTOMATIC SUPPLY RECOVERY AUTHORITY — RUN 35065228877" in context
    assert "Candidate Gate = independent EDITORIAL authority" in context
    assert "Do not return REGENERATE solely because" in context
    assert "status=SELECTED" in context
    assert "NOT CANDIDATE_POOL" in context
    assert "no retry/API/cost ceiling changes" in context


def test_aviation_keeps_existing_scoped_recovery_contract():
    explorer = _load_explorer()
    context = _build_context_with_stubbed_previous(
        explorer,
        scope="aviation",
        fixed_topic="",
        topic_info={"category": "항공", "topic": "날개 구조"},
        original_reason="구체적인 후보가 부족합니다.",
    )
    assert "DEFAULT AUTOMATIC SUPPLY RECOVERY AUTHORITY — RUN 35065228877" not in context
    assert "AVIATION SUPPLY RECOVERY PRECEDENCE" in context


def test_fixed_topic_does_not_receive_default_automatic_override():
    explorer = _load_explorer()
    context = _build_context_with_stubbed_previous(
        explorer,
        scope="",
        fixed_topic="비행기 창문은 왜 둥글까",
        topic_info={"category": "항공", "topic": "비행기 창문은 왜 둥글까"},
        original_reason="구체적인 후보가 부족합니다.",
    )
    assert "BASE RECOVERY CONTEXT" in context
    assert "DEFAULT AUTOMATIC SUPPLY RECOVERY AUTHORITY — RUN 35065228877" not in context


def test_existing_one_call_guard_remains_single():
    source = (ROOT / "ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
    assert source.count("_candidate_supply_recovery_used = True") == 1
    new_hotfix = (
        ROOT / "ci_run_35065228877_bounded_supply_authority_hotfix.py"
    ).read_text(encoding="utf-8")
    assert "authorize_call(" not in new_hotfix
    assert "MAX_TOPIC_REGENERATIONS" not in new_hotfix
    assert "V3_MAX_COST_USD" not in new_hotfix
    assert "RUN_35180822768_FINAL_ATTEMPT_RECOVERY_V1" in new_hotfix
    assert 'topic_attempt == total_topic_attempts' in new_hotfix
    assert 'SHORTS_CANDIDATE_FINAL_ATTEMPT' in new_hotfix


def main():
    test_exact_run_reason_triggers_existing_single_recovery()
    print("CASE A exact Run 35065228877 zero-supply reason: PASS")
    test_editorial_weakness_alone_does_not_spend_recovery()
    print("CASE B editorial weakness alone does not trigger recovery: PASS")
    test_partial_candidate_failure_is_not_whole_pool_exhaustion()
    print("CASE C partial failure does not trigger recovery: PASS")
    test_default_intermediate_shortage_does_not_spend_recovery()
    print("CASE C2 default intermediate shortage preserves recovery: PASS")
    test_run_35186253060_compact_shortage_is_final_only()
    print("CASE C2b compact terminal shortage is final-only: PASS")
    test_run_35187008225_direction_shortage_is_final_only()
    print("CASE C2c direction shortage is final-only: PASS")
    test_run_35188477320_direction_topic_shortage_is_final_only()
    print("CASE C2d Run 35188477320 direction-topic shortage is final-only: PASS")
    test_aviation_and_fixed_topic_keep_legacy_shortage_trigger()
    print("CASE C3 aviation/fixed-topic legacy trigger unchanged: PASS")
    test_default_automatic_recovery_delegates_editorial_quality_to_gate()
    print("CASE D default bounded supplier/Gate authority separation: PASS")
    test_aviation_keeps_existing_scoped_recovery_contract()
    print("CASE E aviation recovery contract unchanged: PASS")
    test_fixed_topic_does_not_receive_default_automatic_override()
    print("CASE F fixed-topic recovery contract unchanged: PASS")
    test_existing_one_call_guard_remains_single()
    print("CASE G retry/API/cost ceilings unchanged: PASS")
    print("RUN 35065228877 BOUNDED SUPPLY AUTHORITY REGRESSION: PASS")


if __name__ == "__main__":
    main()
