#!/usr/bin/env python3
"""Regression for Run 34704697595 Candidate rejection memory.

Production #536 proved the prior rewrite-exhaustion and 4+ pool normalization fixes
worked, then exposed two bounded-control losses:
1. a Candidate whose Hook merely restated Core Question could consume host supply
   even when the same model response already contained a safe declarative
   specificity beat; and
2. topics rejected by host Candidate Pool validation were not copied into the
   existing rejected_topics memory before the next automatic Explorer attempt.

This regression permits no new fact, call, retry, threshold, or grounding escape.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import quality.candidate_pool_handoff as handoff


ROOT = Path(__file__).resolve().parents[1]
REPEAT_ERROR = (
    "Candidate pool[1]: micro_narrative hook이 Core Question과 같은 내용을 반복합니다."
)


def _raw_candidate(*, observation: str = ""):
    candidate = {
        "topic": "비행기 플랩이 이착륙 때 움직이는 방식",
        "angle": "플랩의 이동 자체를 관찰하는 각도",
        "core_question": "왜 플랩은 이착륙 때 뒤로 이동할까?",
        "micro_narrative": {
            "hook": "왜 플랩은 이착륙 때 뒤로 이동할까?",
            "core_question": "왜 플랩은 이착륙 때 뒤로 이동할까?",
            "reveal": "플랩 이동은 날개 형상을 바꾸는 과정이다.",
            "payoff": "같은 날개가 저속 구간에서 다른 형상으로 작동한다.",
        },
        "fact_check_focus": [],
        "visual_proof": ["플랩이 뒤로 이동하는 실제 날개 장면"],
        "selection_reason": "움직임을 눈으로 확인할 수 있다.",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft flap",
        "subject_identity_confidence": 1.0,
        "grounding_evidence": [],
    }
    if observation:
        candidate["specific_observation"] = observation
    return candidate


def _with_stubbed_grounding(fn):
    original_supply = handoff.supply_trusted_subject_grounding
    original_evaluate = handoff.evaluate_candidate_subject_grounding
    handoff.supply_trusted_subject_grounding = (
        lambda validated, *, trusted_records: dict(
            validated,
            subject_kind="physical_entity",
            canonical_subject="aircraft flap",
            subject_identity_confidence=1.0,
            _trusted_grounding_evidence=[{"source": "fixture"}],
        )
    )
    handoff.evaluate_candidate_subject_grounding = (
        lambda candidate: {
            "status": "PASS",
            "subject_grounding": {
                "subject_kind": "physical_entity",
                "canonical_subject": "aircraft flap",
                "confidence": 1.0,
            },
        }
    )
    try:
        return fn()
    finally:
        handoff.supply_trusted_subject_grounding = original_supply
        handoff.evaluate_candidate_subject_grounding = original_evaluate


def _repeat_sensitive_validator(raw, *, prefix):
    hook = str((raw.get("micro_narrative") or {}).get("hook") or "").strip()
    question = str(raw.get("core_question") or "").strip()
    if hook == question:
        raise ValueError(REPEAT_ERROR)
    return deepcopy(raw)


def test_repeated_hook_repairs_from_existing_specific_observation():
    observation = "착륙 때 플랩이 뒤로 밀려나며 날개의 유효 면적이 커진다."
    raw = _raw_candidate(observation=observation)

    def run():
        return handoff.handoff_candidate_pool(
            {"status": "CANDIDATE_POOL", "candidates": [raw]},
            scope="aviation",
            validate_candidate_fn=_repeat_sensitive_validator,
            hard_validate_fn=lambda candidate: (True, "fixture pass"),
            trusted_records=(),
        )

    result = _with_stubbed_grounding(run)
    assert result["status"] == "SELECTED", result
    assert result["winner"]["micro_narrative"]["hook"] == observation, result
    diag = result["_candidate_pool_handoff"]["diagnostics"][0]
    assert diag["status"] == "SURVIVE", diag
    assert diag["normalization"] == {
        "status": "REPAIRED_REPEATED_HOOK_FROM_SUPPLIED_EVIDENCE",
        "source_field": "specific_observation",
    }, diag
    print("CASE A repeated Hook repaired only from supplied observation: PASS")


def test_repeated_hook_without_safe_supplied_beat_stays_rejected():
    raw = _raw_candidate(observation="왜 플랩은 이착륙 때 뒤로 이동할까?")

    result = handoff.handoff_candidate_pool(
        {"status": "CANDIDATE_POOL", "candidates": [raw]},
        scope="aviation",
        validate_candidate_fn=_repeat_sensitive_validator,
        hard_validate_fn=lambda candidate: (True, "must not be reached"),
        trusted_records=(),
    )
    assert result["status"] == "REGENERATE", result
    diag = result["_candidate_pool_handoff"]["diagnostics"][0]
    assert diag["status"] == "REJECT", diag
    assert "micro_narrative hook" in diag["reason"], diag
    assert "normalization" not in diag, diag
    print("CASE B unsafe/missing Hook repair remains fail-closed: PASS")


def test_unrelated_schema_error_never_uses_hook_repair():
    raw = _raw_candidate(
        observation="착륙 때 플랩이 뒤로 밀려나며 날개의 유효 면적이 커진다."
    )

    def unrelated_validator(candidate, *, prefix):
        raise ValueError(f"{prefix}.angle이 비어 있습니다.")

    result = handoff.handoff_candidate_pool(
        {"status": "CANDIDATE_POOL", "candidates": [raw]},
        scope="aviation",
        validate_candidate_fn=unrelated_validator,
        hard_validate_fn=lambda candidate: (True, "must not be reached"),
        trusted_records=(),
    )
    assert result["status"] == "REGENERATE", result
    diag = result["_candidate_pool_handoff"]["diagnostics"][0]
    assert diag["status"] == "REJECT", diag
    assert "angle이 비어 있습니다" in diag["reason"], diag
    assert "normalization" not in diag, diag
    print("CASE C unrelated schema failure remains untouched: PASS")


def _string_assignment(source: str, variable_name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == variable_name:
            value = ast.literal_eval(node.value)
            assert isinstance(value, str)
            return value
    raise AssertionError(f"missing assignment: {variable_name}")


def test_rejected_topic_memory_contract_is_bounded_and_automatic_only():
    source = (ROOT / "ci_candidate_pool_handoff_hotfix.py").read_text(encoding="utf-8")
    replacement = _string_assignment(source, "REJECTION_MEMORY_REPLACEMENT")

    required = (
        "# RUN_34704697595_CANDIDATE_REJECT_MEMORY_V1",
        'os.environ.get(',
        '"SHORTS_TOPIC"',
        '== "ALL_CANDIDATES_HARD_FAILED"',
        '!= "REJECT"',
        "rejected_topics.append(",
        "CANDIDATE_REJECT_MEMORY",
    )
    for marker in required:
        assert marker in replacement, marker

    # Memory is disabled whenever a fixed SHORTS_TOPIC exists. The automatic-only
    # guard must wrap the all-hard-failed trace before any topic is appended.
    fixed_guard = 'not str(\n                        os.environ.get('
    assert fixed_guard in replacement, replacement
    assert replacement.index('"SHORTS_TOPIC"') < replacement.index(
        '== "ALL_CANDIDATES_HARD_FAILED"'
    )
    assert replacement.index('== "ALL_CANDIDATES_HARD_FAILED"') < replacement.index(
        "rejected_topics.append("
    )
    print("CASE D host rejected topics feed automatic rejected_topics only: PASS")


def test_installer_anchor_is_single_and_composable():
    source = (ROOT / "ci_candidate_pool_handoff_hotfix.py").read_text(encoding="utf-8")
    anchor = _string_assignment(source, "REJECTION_MEMORY_ANCHOR")
    replacement = _string_assignment(source, "REJECTION_MEMORY_REPLACEMENT")
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")

    assert main_source.count(anchor) == 1, main_source.count(anchor)
    composed = main_source.replace(anchor, replacement, 1)
    assert "# RUN_34704697595_CANDIDATE_REJECT_MEMORY_V1" in composed
    assert composed.count("# RUN_34704697595_CANDIDATE_REJECT_MEMORY_V1") == 1
    print("CASE E rejection-memory installer composes exactly once: PASS")


def test_safety_limits_and_no_new_calls_unchanged():
    assert handoff.CANDIDATE_POOL_MAX == 3
    workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    recovery = (ROOT / "ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
    assert 'V3_MAX_API_CALLS: "60"' in workflow
    assert 'V3_MAX_COST_USD: "0.05"' in workflow
    assert "CANDIDATE SUPPLY RECOVERY (1/1)" in recovery

    touched = "\n".join(
        (ROOT / path).read_text(encoding="utf-8").lower()
        for path in (
            "quality/candidate_pool_handoff.py",
            "ci_candidate_pool_handoff_hotfix.py",
        )
    )
    for forbidden in (
        "authorize_call(",
        "chat.completions",
        "responses.create",
        "images.generate",
        "max_topic_regenerations =",
        "max_rewrites =",
        "v3_max_cost_usd =",
        "v3_max_api_calls =",
    ):
        assert forbidden not in touched, forbidden
    print("CASE F API/cost/retry/quality/grounding authority unchanged: PASS")


def main():
    test_repeated_hook_repairs_from_existing_specific_observation()
    test_repeated_hook_without_safe_supplied_beat_stays_rejected()
    test_unrelated_schema_error_never_uses_hook_repair()
    test_rejected_topic_memory_contract_is_bounded_and_automatic_only()
    test_installer_anchor_is_single_and_composable()
    test_safety_limits_and_no_new_calls_unchanged()
    print("RUN 34704697595 REJECTED TOPIC MEMORY REGRESSION: PASS")


if __name__ == "__main__":
    main()
