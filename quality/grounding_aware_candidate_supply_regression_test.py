#!/usr/bin/env python3
"""Regression for Run 33960845940 grounding-aware aviation supply."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_handoff import handoff_candidate_pool
from quality.grounding_aware_candidate_supply import (
    NO_GROUNDED_CANDIDATE_SUPPLY,
    all_trusted_candidate_records,
    grounding_candidate_capabilities,
    grounding_capability_context,
    no_grounded_candidate_supply_result,
)


ROOT = Path(__file__).resolve().parents[1]


def _window_candidate():
    return {
        "topic": "비행기 창문 가장자리의 둥근 모서리",
        "angle": "둥근 창문 모서리와 응력 집중",
        "core_question": "왜 비행기 창문은 모서리가 둥글까?",
        "micro_narrative": {
            "hook": "비행기 창문 모서리는 일부러 둥글다.",
            "core_question": "왜 모서리를 둥글게 만들었을까?",
            "reveal": "곡선 가장자리는 응력이 한 지점에 쌓이는 것을 줄인다.",
            "payoff": "작은 곡선이 동체의 반복 하중과 연결된다.",
        },
        "fact_check_focus": ["rounded aircraft windows and stress concentration"],
        "visual_proof": ["modern passenger aircraft window rounded corner"],
        "selection_reason": "trusted FAA-backed physical feature",
        "specific_observation": "비행기 창문 가장자리의 둥근 모서리",
        "constraint": "각진 창문 모서리의 높은 응력 집중",
        "counterintuitive_result": "작은 곡선이 응력 흐름을 바꾼다",
        "tradeoff": "",
        "concrete_condition": "가압 동체가 반복 하중을 받을 때",
        "subject_kind": "",
        "canonical_subject": "UNKNOWN",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }


def _unsupported_run_candidate():
    candidate = _window_candidate()
    candidate.update(
        topic="비행기 활주로의 흰색 선",
        angle="활주로 흰색 선의 의미",
        core_question="왜 활주로에는 흰색 선이 있을까?",
        specific_observation="비행기 활주로의 흰색 선",
        constraint="활주로 운항 표시",
        counterintuitive_result="표시 위치마다 의미가 다르다",
        concrete_condition="항공기가 활주로를 사용할 때",
    )
    candidate["micro_narrative"] = {
        "hook": "활주로에는 흰 선이 반복된다.",
        "core_question": "왜 이런 선이 있을까?",
        "reveal": "운항 표시를 구분한다.",
        "payoff": "조종사는 표시를 보고 위치를 구분한다.",
    }
    candidate["visual_proof"] = ["airport runway white markings"]
    return candidate


def _unresolved_candidate():
    candidate = _window_candidate()
    candidate.update(
        topic="비행 중 승객이 느끼는 기내 소음",
        angle="기내 소음의 변화",
        core_question="왜 비행 중 기내 소음은 달라질까?",
        specific_observation="비행 중 들리는 기내 소음",
        constraint="비행 단계에 따른 소음 변화",
        counterintuitive_result="소음의 원인이 하나가 아니다",
        concrete_condition="순항 중 객실에서 들을 때",
    )
    candidate["micro_narrative"] = {
        "hook": "기내 소음은 계속 같지 않다.",
        "core_question": "왜 소리가 달라질까?",
        "reveal": "여러 소음원이 함께 들린다.",
        "payoff": "비행 단계마다 들리는 소리가 바뀐다.",
    }
    candidate["visual_proof"] = ["passenger cabin during cruise"]
    return candidate


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
    return deepcopy(candidate)


def _hard_validate(candidate):
    if not candidate.get("specific_observation") or not candidate.get("visual_proof"):
        return False, "missing concrete specificity or visual proof"
    return True, "PASS"


def _handoff(candidate):
    return handoff_candidate_pool(
        {"status": "CANDIDATE_POOL", "candidates": [candidate]},
        scope="aviation",
        validate_candidate_fn=_validate,
        hard_validate_fn=_hard_validate,
        trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )


def main() -> int:
    records = all_trusted_candidate_records()
    capabilities = grounding_candidate_capabilities()
    assert records, "trusted registry unexpectedly empty"
    assert capabilities, "grounding capability unexpectedly empty"
    record_canonicals = {str(record.get("canonical_subject")) for record in records}
    capability_canonicals = {item["canonical_subject"] for item in capabilities}
    assert capability_canonicals == record_canonicals, (
        capability_canonicals,
        record_canonicals,
    )
    print(f"TEST A capability single source: PASS capabilities={len(capabilities)}")

    context = grounding_capability_context()
    assert "GROUNDING-AWARE CANDIDATE SUPPLY" in context
    assert "modern aircraft passenger window with rounded/oval corners" in context
    assert "jet engine nacelle/nozzle chevrons" in context
    assert "비행기 활주로의 흰색 선" not in context
    print("TEST A capability context constrains supply to trusted subject space: PASS")

    supported = _handoff(_window_candidate())
    assert supported["status"] == "SELECTED", supported
    assert (supported.get("_candidate_pool_handoff") or {}).get("survived") == 1
    print("TEST A supported aviation subject -> host survivor >= 1: PASS")

    unsupported = _handoff(_unsupported_run_candidate())
    assert unsupported["status"] == "REGENERATE", unsupported
    assert "ALL_CANDIDATES_HARD_FAILED" in unsupported.get("reason", "")
    diagnostics = (unsupported.get("_candidate_pool_handoff") or {}).get("diagnostics") or []
    assert diagnostics and "no trusted evidence" in diagnostics[0].get("reason", "")
    print("TEST B Run 33960845940 unsupported runway subject still rejected: PASS")

    unresolved = _handoff(_unresolved_candidate())
    assert unresolved["status"] == "REGENERATE", unresolved
    diagnostics = (unresolved.get("_candidate_pool_handoff") or {}).get("diagnostics") or []
    assert diagnostics and (
        "unresolved" in diagnostics[0].get("reason", "")
        or "no trusted evidence" in diagnostics[0].get("reason", "")
    )
    print("TEST C unresolved/untrusted subject still fail-closed: PASS")

    empty_caps = grounding_candidate_capabilities(production_records=(), pool_records=())
    assert empty_caps == ()
    empty_context = grounding_capability_context(production_records=(), pool_records=())
    assert NO_GROUNDED_CANDIDATE_SUPPLY in empty_context
    empty_result = no_grounded_candidate_supply_result(
        production_records=(), pool_records=()
    )
    assert empty_result and empty_result["status"] == "REGENERATE"
    assert NO_GROUNDED_CANDIDATE_SUPPLY in empty_result["reason"]
    print("TEST E empty capability -> deterministic fail-close without fallback: PASS")

    installer = (ROOT / "ci_grounding_aware_candidate_supply_hotfix.py").read_text(
        encoding="utf-8"
    )
    assert "GROUNDING_AWARE_CANDIDATE_SUPPLY_V1" in installer
    assert "_grounding_aware_previous_build_execution_context" in installer
    assert "no_grounded_candidate_supply_result" in installer
    assert "Candidate Gate" in installer
    forbidden_calls = (
        "authorize_call(",
        "openai.chat",
        "chat.completions",
        "responses.create",
        "images.generate",
        "vision_client",
    )
    surface = (
        (ROOT / "quality/grounding_aware_candidate_supply.py").read_text(encoding="utf-8")
        + installer
    ).lower()
    assert all(token not in surface for token in forbidden_calls)
    print("TEST D quality/fact authority unchanged; new external calls=0: PASS")

    projection = (ROOT / "ci_aviation_specificity_projection_hotfix.py").read_text(
        encoding="utf-8"
    )
    assert "import ci_candidate_pool_handoff_hotfix" in projection
    assert "import ci_grounding_aware_candidate_supply_hotfix" in projection
    recovery = (ROOT / "ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
    assert "CANDIDATE SUPPLY RECOVERY (1/1)" in recovery
    assert "_candidate_supply_recovery_used" in recovery
    print("TEST F production composition + existing 1/1 recovery contract preserved: PASS")

    main_workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    assert 'V3_MAX_API_CALLS: "60"' in main_workflow
    assert 'V3_MAX_COST_USD: "0.05"' in main_workflow
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "MAX_TOPIC_REGENERATIONS = 6" in main_source
    print("CAPS: PASS API=60 cost=$0.05 attempts=7")

    print("GROUNDING-AWARE CANDIDATE SUPPLY REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
