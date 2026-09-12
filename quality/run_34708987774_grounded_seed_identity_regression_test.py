#!/usr/bin/env python3
"""Regression for Run 34708987774 deterministic grounded-seed identity scoping."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_handoff import handoff_candidate_pool
from quality.grounding_aware_candidate_supply import (
    REPO_OWNED_SEED_RECORD_REF_FIELD,
    all_trusted_candidate_records,
    grounded_seed_candidate_pool,
)


ROOT = Path(__file__).resolve().parents[1]


def _validate(candidate, *, prefix="Candidate"):
    required = (
        "topic",
        "angle",
        "core_question",
        "micro_narrative",
        "fact_check_focus",
        "visual_proof",
        "selection_reason",
    )
    missing = [key for key in required if key not in candidate]
    if missing:
        raise ValueError(f"{prefix} missing: {missing}")
    validated = deepcopy(candidate)
    # Production validate_candidate does not grant trust from private helper data.
    # Keep that trust decision solely in handoff's raw in-memory object boundary.
    validated.pop(REPO_OWNED_SEED_RECORD_REF_FIELD, None)
    return validated


def _hard_validate(candidate):
    if not candidate.get("specific_observation"):
        return False, "missing concrete specificity"
    if not candidate.get("visual_proof"):
        return False, "visual_proof missing"
    return True, "PASS"


def _handoff(candidate):
    return handoff_candidate_pool(
        {"status": "CANDIDATE_POOL", "candidates": [candidate]},
        scope="aviation",
        validate_candidate_fn=_validate,
        hard_validate_fn=_hard_validate,
        trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )


def _unsupported_candidate():
    return {
        "topic": "비행기 활주로의 흰색 선",
        "angle": "활주로 흰색 선의 의미",
        "core_question": "왜 활주로에는 흰색 선이 있을까?",
        "micro_narrative": {
            "hook": "활주로에는 흰색 선이 반복됩니다.",
            "core_question": "왜 이런 선이 있을까요?",
            "reveal": "운항 표시를 구분합니다.",
            "payoff": "조종사는 표시를 보고 위치를 구분합니다.",
        },
        "fact_check_focus": ["airport runway white markings"],
        "visual_proof": ["airport runway white markings"],
        "selection_reason": "unsupported control candidate",
        "specific_observation": "비행기 활주로의 흰색 선",
        "constraint": "활주로 운항 표시",
        "counterintuitive_result": "표시 위치마다 의미가 다릅니다.",
        "tradeoff": "",
        "concrete_condition": "항공기가 활주로를 사용할 때",
        "subject_kind": "physical_entity",
        "canonical_subject": "airport runway white markings",
        "subject_identity_confidence": 0.99,
        "grounding_evidence": [],
    }


def main() -> int:
    records = all_trusted_candidate_records()
    seed_records = [
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("seed_candidate"), dict)
        and str(record.get("seed_candidate", {}).get("topic") or "").strip()
    ]
    assert seed_records, "trusted deterministic seed registry unexpectedly empty"

    expected_topics = {
        str(record["seed_candidate"]["topic"]).strip() for record in seed_records
    }
    observed_topics = []
    observed_canonicals = []

    # Walk the seed registry one at a time so every repo-owned deterministic seed
    # must survive the unchanged canonical gate, not merely one candidate in a pool.
    for _ in range(len(expected_topics)):
        pool = grounded_seed_candidate_pool(
            recent_topics=observed_topics,
            rejected_topics=[],
            max_candidates=1,
        )
        assert pool["status"] == "CANDIDATE_POOL", pool
        candidate = pool["candidates"][0]
        topic = str(candidate.get("topic") or "").strip()
        record_ref = candidate.get(REPO_OWNED_SEED_RECORD_REF_FIELD)
        assert any(record_ref is record for record in records), (
            "seed lost host-owned record identity",
            topic,
        )
        expected_canonical = str(record_ref.get("canonical_subject") or "").strip()

        result = _handoff(candidate)
        assert result["status"] == "SELECTED", (topic, result)
        trace = result.get("_candidate_pool_handoff") or {}
        assert trace.get("survived") == 1, (topic, trace)
        diagnostics = trace.get("diagnostics") or []
        assert diagnostics and diagnostics[0].get("status") == "SURVIVE", diagnostics
        assert diagnostics[0].get("trusted_seed_scope") == expected_canonical, diagnostics
        winner = result.get("winner") or {}
        assert winner.get("canonical_subject") == expected_canonical, (
            topic,
            winner.get("canonical_subject"),
            expected_canonical,
        )
        assert winner.get("_trusted_grounding_evidence"), (topic, winner)

        observed_topics.append(topic)
        observed_canonicals.append(expected_canonical)

    assert set(observed_topics) == expected_topics, (observed_topics, expected_topics)
    print(
        "CASE A every repo-owned deterministic seed resolves to its originating "
        f"trusted identity: PASS seeds={len(observed_topics)}"
    )

    # A JSON/model candidate can imitate the private field name and even copy a
    # record's contents, but it cannot reproduce the exact in-memory record object.
    # Therefore it must fall back to the unchanged generic resolver and fail closed
    # when its own subject is unsupported.
    spoof = _unsupported_candidate()
    spoof[REPO_OWNED_SEED_RECORD_REF_FIELD] = deepcopy(records[0])
    spoof_result = _handoff(spoof)
    assert spoof_result["status"] == "REGENERATE", spoof_result
    spoof_trace = spoof_result.get("_candidate_pool_handoff") or {}
    spoof_diag = (spoof_trace.get("diagnostics") or [{}])[0]
    assert spoof_diag.get("status") == "REJECT", spoof_diag
    assert not spoof_diag.get("trusted_seed_scope"), spoof_diag
    print("CASE B copied/model-authored private seed metadata cannot gain trust: PASS")

    # Run 34710062143 exposed an integration-only failure: production imports the
    # installer rather than executing it as a script. Lock that composition path so
    # a __main__-only guard can never silently disable this patch again.
    chain_source = (ROOT / "ci_grounding_aware_candidate_supply_hotfix.py").read_text(
        encoding="utf-8"
    )
    installer_source = (
        ROOT / "ci_run_34708987774_grounded_seed_identity_hotfix.py"
    ).read_text(encoding="utf-8")
    assert "import ci_run_34708987774_grounded_seed_identity_hotfix" in chain_source
    assert installer_source.rstrip().endswith("main()"), (
        "production-imported seed identity installer must execute main() on import"
    )
    assert 'if __name__ == "__main__":\n    main()' not in installer_source
    print("CASE C production import actually executes seed identity installer: PASS")

    # The patch is a narrowing operation only; it does not change retry, API,
    # cost, Candidate Gate, FACT, or quality thresholds.
    assert len(observed_canonicals) == len(observed_topics)
    print("CASE D seed provenance narrows canonical matching without gate relaxation: PASS")
    print("RUN 34708987774 GROUNDED SEED IDENTITY REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
