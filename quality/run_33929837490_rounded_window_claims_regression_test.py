"""Deterministic regression for Run 33929837490 rounded-window claim coverage.

No model/network call is made. The repo-owned FAA record must provide at least
three genuinely distinct, provenance-bearing factual propositions before Writer
planning can proceed. Quota padding, missing provenance, and cross-topic facts
remain fail-closed.
"""
from __future__ import annotations

from copy import deepcopy
import importlib
import re
import runpy

from content.grounded_claim_plan import extract_grounded_claims
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    FAA_COMET_LESSONS_SOURCE,
)
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding


# Reproduce the Writer plan layer that owns the minimum-3 assertion.
runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")

import content.script_engine_v2 as engine

engine = importlib.reload(engine)


def _rounded_record():
    matches = [
        item for item in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
        if item.get("canonical_subject")
        == "modern aircraft passenger window with rounded/oval corners"
    ]
    assert len(matches) == 1, matches
    return deepcopy(matches[0])


def _authority_candidate():
    return {
        "topic": "비행기 창문 모서리의 둥근 형태",
        "angle": "비행기 창문 모서리가 둥근 구조적 이유",
        "core_question": "왜 비행기 창문은 모서리가 둥글게 되어 있을까?",
        "specific_observation": "비행기 창문 가장자리의 둥근 모서리",
        "fact_check_focus": [
            "비행기 창문 모서리의 둥근 형태",
            # Hostile cross-topic material must never become trusted claim supply.
            "윙렛이 유도항력을 줄여 연료 효율을 높입니다.",
        ],
        "visual_proof": ["현대 여객기 동체의 승객용 창문"],
        "micro_narrative": {
            "hook": "비행기 창문 모서리는 둥글게 생겼습니다.",
            "core_question": "왜 비행기 창문은 모서리가 둥글게 되어 있을까?",
            "reveal": "윙렛은 항력을 줄입니다.",
            "payoff": "연료 효율이 좋아집니다.",
        },
    }


def _signature(claim):
    """Exact proposition guard for repo-owned evidence, not fuzzy semantic merging."""
    summary = str(claim.get("evidence_summary") or "").lower()
    return " ".join(re.findall(r"[0-9a-z가-힣]+", summary))


def _assert_distinct_repo_propositions(claims):
    signatures = [_signature(item) for item in claims]
    assert all(signatures), signatures
    assert len(signatures) == len(set(signatures)), (
        "same factual proposition cannot satisfy the minimum by changing claim_id"
    )


def _expect_minimum_three_failure(candidate):
    try:
        engine.build_narrative_plan(candidate)
    except ValueError as exc:
        assert "at least 3 distinct supported factual claims" in str(exc), exc
        return
    raise AssertionError("minimum-3 claim plan unexpectedly passed")


def assert_authority_run_now_passes():
    record = _rounded_record()
    claims = record.get("supported_claims") or []
    assert len(claims) == 3, claims
    assert [item["claim_id"] for item in claims] == [
        "squarish_window_stress_concentration",
        "rounded_window_stress_distribution",
        "squarish_window_fatigue_rupture",
    ]
    _assert_distinct_repo_propositions(claims)

    for claim in claims:
        assert claim.get("source") == FAA_COMET_LESSONS_SOURCE, claim
        assert str(claim.get("detail") or "").strip(), claim
        assert str(claim.get("evidence_summary") or "").strip(), claim
        assert any(str(item or "").strip() for item in claim.get("allowed_paraphrase_scope") or []), claim

    grounded = supply_trusted_subject_grounding(
        _authority_candidate(), trusted_records=(record,)
    )
    assert grounded["canonical_subject"] == "modern aircraft passenger window with rounded/oval corners"
    trusted = grounded.get("_trusted_grounded_claims") or []
    assert len(trusted) == 3, trusted
    assert len({item["claim_id"] for item in trusted}) == 3
    assert all(item.get("source") == FAA_COMET_LESSONS_SOURCE for item in trusted)
    serialized = str(trusted)
    for forbidden in ("윙렛", "유도항력", "연료 효율"):
        assert forbidden not in serialized, serialized

    extracted = extract_grounded_claims(grounded)
    assert len(extracted) == 3, extracted
    assert all(item.get("provenance_present") is True for item in extracted)

    plan = engine.build_narrative_plan(grounded)
    claim_plan = plan.get("grounded_claim_plan") or []
    assert len(claim_plan) == 3, plan
    assert len({item["claim_id"] for item in claim_plan}) == 3
    assert len({item["owner_scene"] for item in claim_plan}) == 3
    assert plan["target_scene_count"] == 5, plan


def assert_duplicate_claim_id_fails_closed():
    grounded = supply_trusted_subject_grounding(
        _authority_candidate(), trusted_records=(_rounded_record(),)
    )
    claims = deepcopy(grounded["_trusted_grounded_claims"])
    claims[1]["claim_id"] = claims[0]["claim_id"]
    grounded["_trusted_grounded_claims"] = claims
    assert len(extract_grounded_claims(grounded)) == 2
    _expect_minimum_three_failure(grounded)


def assert_same_proposition_renamed_fails_record_guard():
    claims = deepcopy(_rounded_record()["supported_claims"])
    duplicate = deepcopy(claims[0])
    duplicate["claim_id"] = "renamed_same_fact_1"
    triplicate = deepcopy(claims[0])
    triplicate["claim_id"] = "renamed_same_fact_2"
    fake_quota = [claims[0], duplicate, triplicate]
    try:
        _assert_distinct_repo_propositions(fake_quota)
    except AssertionError:
        return
    raise AssertionError("renamed duplicate propositions satisfied quota guard")


def assert_missing_provenance_fails_closed():
    grounded = supply_trusted_subject_grounding(
        _authority_candidate(), trusted_records=(_rounded_record(),)
    )
    claims = deepcopy(grounded["_trusted_grounded_claims"])
    claims[2]["source"] = ""
    claims[2]["detail"] = ""
    grounded["_trusted_grounded_claims"] = claims
    assert len(extract_grounded_claims(grounded)) == 2
    _expect_minimum_three_failure(grounded)


def assert_existing_paths_unchanged():
    import quality.script_engine_v2_grounded_claim_plan_regression_test as existing

    existing.assert_run_332398_plan_and_rejection()  # chevron stays 4-claim grounded path
    existing.assert_cross_topic_generalization()     # winglet/flap stay >=3-claim paths


def main():
    assert_authority_run_now_passes()
    assert_duplicate_claim_id_fails_closed()
    assert_same_proposition_renamed_fails_record_guard()
    assert_missing_provenance_fails_closed()
    assert_existing_paths_unchanged()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("RUN 33929837490 ROUNDED WINDOW GROUNDED CLAIM REGRESSION: PASS")


if __name__ == "__main__":
    main()
