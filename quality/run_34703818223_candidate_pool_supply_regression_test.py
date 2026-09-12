#!/usr/bin/env python3
"""Regression for Run 34703818223 Candidate Pool supply failures.

Authority from production #535:
- the previous rewrite-exhaustion recovery worked and advanced to later attempts;
- one aviation Explorer response supplied 5 candidates although the host ceiling is 3;
- repeated Candidate pools used a micro_narrative hook that merely restated the
  Core Question and were correctly rejected by the existing schema/progression gate.

This regression strengthens supply shape without relaxing candidate-level gates.
"""

from __future__ import annotations

from pathlib import Path

import quality.candidate_pool_handoff as handoff


ROOT = Path(__file__).resolve().parents[1]


def _raw_candidate(index: int):
    return {
        "topic": f"candidate-{index}",
        "subject_kind": "UNKNOWN",
        "canonical_subject": "UNKNOWN",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }


def _with_stubbed_grounding(fn):
    original_supply = handoff.supply_trusted_subject_grounding
    original_evaluate = handoff.evaluate_candidate_subject_grounding
    handoff.supply_trusted_subject_grounding = (
        lambda validated, *, trusted_records: dict(
            validated,
            subject_kind="physical_entity",
            canonical_subject="fixture aircraft component",
            subject_identity_confidence=1.0,
            _trusted_grounding_evidence=[{"source": "fixture"}],
        )
    )
    handoff.evaluate_candidate_subject_grounding = (
        lambda candidate: {
            "status": "PASS",
            "subject_grounding": {
                "subject_kind": "physical_entity",
                "canonical_subject": "fixture aircraft component",
                "confidence": 1.0,
            },
        }
    )
    try:
        return fn()
    finally:
        handoff.supply_trusted_subject_grounding = original_supply
        handoff.evaluate_candidate_subject_grounding = original_evaluate


def test_oversize_pool_is_bounded_before_validation():
    seen = []

    def validate(raw, *, prefix):
        seen.append((raw["topic"], prefix))
        return dict(raw)

    def run():
        return handoff.handoff_candidate_pool(
            {
                "status": "CANDIDATE_POOL",
                "candidates": [_raw_candidate(i) for i in range(1, 6)],
            },
            scope="aviation",
            validate_candidate_fn=validate,
            hard_validate_fn=lambda candidate: (True, "fixture pass"),
            trusted_records=(),
        )

    result = _with_stubbed_grounding(run)
    assert result["status"] == "SELECTED", result
    trace = result["_candidate_pool_handoff"]
    assert trace["supplied"] == 5, trace
    assert trace["validated"] == 3, trace
    assert trace["survived"] == 3, trace
    assert trace["normalization"] == {
        "status": "TRUNCATED_TO_HOST_MAX",
        "supplied": 5,
        "validated": 3,
        "limit": 3,
    }, trace
    assert [topic for topic, _ in seen] == ["candidate-1", "candidate-2", "candidate-3"], seen
    assert all("candidate-4" != topic and "candidate-5" != topic for topic, _ in seen), seen
    print("CASE A oversize 5->3 bounded normalization: PASS")


def test_normalization_does_not_bypass_candidate_gates():
    seen = []

    def validate(raw, *, prefix):
        seen.append(raw["topic"])
        return dict(raw)

    result = handoff.handoff_candidate_pool(
        {
            "status": "CANDIDATE_POOL",
            "candidates": [_raw_candidate(i) for i in range(1, 6)],
        },
        scope="aviation",
        validate_candidate_fn=validate,
        hard_validate_fn=lambda candidate: (False, "fixture hard reject"),
        trusted_records=(),
    )
    assert result["status"] == "REGENERATE", result
    assert "ALL_CANDIDATES_HARD_FAILED" in result["reason"], result
    trace = result["_candidate_pool_handoff"]
    assert trace["supplied"] == 5, trace
    assert trace["validated"] == 3, trace
    assert len(trace["diagnostics"]) == 3, trace
    assert all(item["status"] == "REJECT" for item in trace["diagnostics"]), trace
    assert seen == ["candidate-1", "candidate-2", "candidate-3"], seen
    print("CASE B per-candidate hard gates remain fail-closed: PASS")


def test_empty_pool_still_fails_closed():
    result = handoff.handoff_candidate_pool(
        {"status": "CANDIDATE_POOL", "candidates": []},
        scope="aviation",
        validate_candidate_fn=lambda raw, *, prefix: dict(raw),
        hard_validate_fn=lambda candidate: (True, "unused"),
        trusted_records=(),
    )
    assert result["status"] == "REGENERATE", result
    assert "pool size must be 1..3; got 0" in result["reason"], result
    print("CASE C empty supply remains fail-closed: PASS")


def test_prompt_contract_matches_run_535_failure_modes():
    installer = (ROOT / "ci_candidate_pool_handoff_hotfix.py").read_text(encoding="utf-8")
    required = (
        "[POOL SIZE — HARD OUTPUT CONTRACT]",
        "MUST contain 1, 2, or 3 items",
        "NEVER return 4 or more Candidates",
        "[MICRO NARRATIVE PROGRESSION — HARD OUTPUT CONTRACT]",
        "MUST NOT be a question",
        "MUST NOT\nrepeat, paraphrase, or merely restate",
        "HOOK = concrete observation/result/constraint",
    )
    for marker in required:
        assert marker in installer, marker
    print("CASE D prompt prevents 4+ pools and Hook/Core-Question repetition: PASS")


def test_safety_limits_unchanged():
    assert handoff.CANDIDATE_POOL_MAX == 3
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    recovery = (ROOT / "ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
    assert "MAX_TOPIC_REGENERATIONS = 6" in main_source
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
    ):
        assert forbidden not in touched, forbidden
    print("CASE E API/cost/retry/quality authority unchanged: PASS")


def main():
    test_oversize_pool_is_bounded_before_validation()
    test_normalization_does_not_bypass_candidate_gates()
    test_empty_pool_still_fails_closed()
    test_prompt_contract_matches_run_535_failure_modes()
    test_safety_limits_unchanged()
    print("RUN 34703818223 CANDIDATE POOL SUPPLY REGRESSION: PASS")


if __name__ == "__main__":
    main()
