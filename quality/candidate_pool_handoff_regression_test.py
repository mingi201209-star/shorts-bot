#!/usr/bin/env python3
"""Authority regression for Candidate Pool Handoff.

RED authority:
- Runs 33887547463 and 33893139846 both measured model-side ZERO_SUPPLY=6/7,
  EXPLORER_SELECTED=1/7.
- Legacy output validation accepts only SELECTED/REGENERATE, so host cannot see
  a reviewable pool before the model self-withholds it.

GREEN authority:
- aviation Candidate Explorer may hand a bounded 1..3 pool to host;
- host validates candidates independently and grounds them deterministically;
- editorial weakness remains Candidate Gate authority;
- all-hard-invalid stays fail-closed;
- no new model/Vision/image-generation call is introduced.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _runtime_explorer_module():
    # content.candidate_explorer is a safe wrapper package that intentionally loads
    # content/candidate_explorer.py as _LEGACY. Production uses the same module.
    import content.candidate_explorer as explorer_package

    return explorer_package._LEGACY


def _window_candidate(*, editorially_weak: bool = False):
    reveal = (
        "안전을 위해 이런 모양입니다."
        if editorially_weak
        else "둥근 모서리는 각진 모서리보다 응력이 한 지점에 집중되는 것을 줄입니다."
    )
    return {
        "topic": "비행기 창문 가장자리의 둥근 모서리",
        "angle": "각진 창문 대신 둥근 모서리를 쓰는 구조적 이유",
        "core_question": "왜 비행기 창문은 모서리가 둥글게 디자인되어 있을까?",
        "micro_narrative": {
            "hook": "비행기 창문 모서리는 일부러 둥글게 만들었습니다.",
            "core_question": "왜 비행기 창문 모서리는 둥글까요?",
            "reveal": reveal,
            "payoff": "작은 곡선이 동체 하중을 받는 방식과 연결됩니다.",
        },
        "fact_check_focus": ["둥근/타원형 항공기 창문과 응력 집중의 관계"],
        "visual_proof": ["여객기 창문의 둥근 모서리를 가까이 보여주기"],
        "selection_reason": "승객이 직접 보는 작은 구조를 물리적 이유로 설명할 수 있습니다.",
        "specific_observation": "비행기 창문 가장자리의 둥근 모서리",
        "constraint": "가압된 동체에서 창문 개구부 주변으로 반복 하중이 전달됩니다.",
        "counterintuitive_result": "작은 모서리 형상이 응력 집중과 연결됩니다.",
        "tradeoff": "",
        "concrete_condition": "객실 가압으로 동체가 반복 하중을 받을 때",
        "subject_kind": "",
        "canonical_subject": "UNKNOWN",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }


def _offscope_candidate():
    candidate = _window_candidate()
    candidate.update(
        topic="자동차 타이어의 홈",
        angle="젖은 노면의 물을 빼는 홈",
        core_question="왜 자동차 타이어에는 깊은 홈이 있을까?",
        specific_observation="타이어 표면의 홈",
        constraint="젖은 노면의 물 배출",
        concrete_condition="젖은 도로에서 주행할 때",
    )
    candidate["micro_narrative"] = {
        "hook": "타이어 홈에는 물이 지나갑니다.",
        "core_question": "왜 홈이 있을까요?",
        "reveal": "젖은 노면에서 물을 배출하는 통로입니다.",
        "payoff": "노면 접촉을 유지하는 데 쓰입니다.",
    }
    candidate["visual_proof"] = ["젖은 도로 위 자동차 타이어 홈"]
    return candidate


def _malformed_candidate():
    candidate = _window_candidate()
    candidate.pop("angle")
    return candidate


def _pool(candidates):
    return {"status": "CANDIDATE_POOL", "candidates": candidates}


def legacy_red() -> int:
    validate_explorer_output = _runtime_explorer_module().validate_explorer_output
    try:
        validate_explorer_output(_pool([_window_candidate()]))
    except ValueError as exc:
        print(f"RED reproduced: legacy host rejects CANDIDATE_POOL before seeing candidates: {exc}")
        return 1
    print("RED NOT reproduced: legacy validator unexpectedly accepted CANDIDATE_POOL")
    return 0


def _assert_new_surface_has_zero_calls():
    text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "quality/candidate_pool_handoff.py",
            "quality/candidate_pool_grounding_records.py",
            "ci_candidate_pool_handoff_hotfix.py",
        )
    ).lower()
    forbidden = (
        "authorize_call(",
        "openai.chat",
        "chat.completions",
        "responses.create",
        "vision_client",
        "image.generate",
        "images.generate",
    )
    assert all(token not in text for token in forbidden), "new external/model call found"


def green() -> int:
    os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"

    validate_explorer_output = _runtime_explorer_module().validate_explorer_output
    from content.candidate_gate import evaluate_candidate as candidate_gate_evaluate
    from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding

    mixed = _pool([
        _malformed_candidate(),
        _window_candidate(editorially_weak=False),
        _window_candidate(editorially_weak=True),
    ])
    result = validate_explorer_output(mixed)
    assert result["status"] == "SELECTED", result
    trace = result.get("_candidate_pool_handoff") or {}
    diagnostics = trace.get("diagnostics") or []
    assert trace.get("supplied") == 3, trace
    assert trace.get("survived") == 2, trace
    assert diagnostics[0]["status"] == "REJECT", diagnostics
    assert diagnostics[1]["status"] == "SURVIVE", diagnostics
    assert diagnostics[2]["status"] == "SURVIVE", diagnostics
    assert result["winner"]["topic"] == "비행기 창문 가장자리의 둥근 모서리"
    print("TEST B mixed pool: PASS (hard invalid rejected; factual + editorially weak supply survived)")

    weak_gate = candidate_gate_evaluate(_window_candidate(editorially_weak=True))
    assert weak_gate.get("status") in {"PASS", "REGENERATE"}, weak_gate
    print(f"Candidate Gate remains independent: {weak_gate.get('status')}")

    all_bad = validate_explorer_output(_pool([_malformed_candidate(), _offscope_candidate()]))
    assert all_bad["status"] == "REGENERATE", all_bad
    assert "ALL_CANDIDATES_HARD_FAILED" in all_bad.get("reason", ""), all_bad
    print("TEST C all hard invalid: PASS (fail-close)")

    window_only = validate_explorer_output(_pool([_window_candidate()]))
    window = window_only["winner"]
    grounding = evaluate_candidate_subject_grounding(window)
    assert grounding["status"] == "PASS", grounding
    assert window["subject_kind"] == "physical_entity", window
    assert window["canonical_subject"] != "UNKNOWN", window
    evidence = window.get("_trusted_grounding_evidence") or []
    assert evidence and "faa.gov" in evidence[0].get("source", ""), evidence
    print("TEST D rounded-window trusted grounding: PASS")

    malformed = validate_explorer_output(_pool([_malformed_candidate()]))
    assert malformed["status"] == "REGENERATE", malformed
    print("TEST E malformed schema: PASS (fail-close)")

    os.environ["SHORTS_CANDIDATE_SCOPE"] = "urban"
    try:
        validate_explorer_output(_pool([_window_candidate()]))
    except ValueError:
        pass
    else:
        raise AssertionError("non-aviation scope unexpectedly activated Candidate Pool Handoff")
    print("TEST F non-aviation compatibility: PASS")
    os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"

    explorer_source = (ROOT / "content/candidate_explorer.py").read_text(encoding="utf-8")
    assert "AVIATION_SYSTEM_AUTHORITY_SUPPLY_V1" in explorer_source
    assert "AVIATION OBSERVABLE SEED SUPPLY CONTRACT" in explorer_source
    assert "CANDIDATE_POOL_HANDOFF_V1" in explorer_source
    print("#282/#283 preservation: PASS")

    recovery_source = (ROOT / "ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
    assert "CANDIDATE SUPPLY RECOVERY (1/1)" in recovery_source
    assert "_candidate_supply_recovery_used" in recovery_source
    print("TEST G recovery bound contract: PASS (1/1)")

    _assert_new_surface_has_zero_calls()
    main_workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    assert 'V3_MAX_API_CALLS: "60"' in main_workflow
    assert 'V3_MAX_COST_USD: "0.05"' in main_workflow
    assert "MAX_TOPIC_REGENERATIONS = 6" in (ROOT / "main.py").read_text(encoding="utf-8")
    print("TEST H API/cost/retry safety: PASS (new calls=0; caps unchanged)")

    print("CANDIDATE POOL HANDOFF AUTHORITY REGRESSION: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-red", action="store_true")
    args = parser.parse_args()
    return legacy_red() if args.legacy_red else green()


if __name__ == "__main__":
    raise SystemExit(main())
