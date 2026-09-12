#!/usr/bin/env python3
"""Regression for Run 34705737709 pre-Writer novelty budget control.

Production #537 spent a GPT-5.6 Sol Writer on an automatic aviation Candidate
whose downstream Novelty Judge scored 4/10, then received the same trusted
physical subject under a renamed topic and spent a second Sol Writer. The second
Writer pushed cost to $0.055195 against the unchanged $0.05 ceiling.

This regression proves the fix moves the existing Novelty >=5 requirement before
Writer, remembers only independently trusted canonical physical identity within
one automatic aviation run, and leaves fixed topics / unrelated candidates alone.
"""

from __future__ import annotations

import ast
import os
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "ci_novelty_budget_hotfix.py"


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


def _trusted_candidate(topic: str, canonical: str) -> dict:
    return {
        "topic": topic,
        "angle": "구체적인 설계 제약",
        "core_question": "왜 이런 설계가 필요할까?",
        "micro_narrative": {
            "hook": "눈에 보이는 구조가 예상과 다르게 작동한다.",
            "core_question": "왜 이런 설계가 필요할까?",
            "reveal": "하나의 구체적인 설계 제약이 작동한다.",
            "payoff": "겉모양이 아니라 제약 때문에 생긴 구조다.",
        },
        "subject_kind": "physical_entity",
        "canonical_subject": canonical,
        "_trusted_grounding_evidence": [
            {
                "supports_subject": canonical,
                "source": "https://example.invalid/fixture",
                "detail": "repo-owned fixture identity evidence",
            }
        ],
    }


def _load_patch_namespace():
    source = INSTALLER.read_text(encoding="utf-8")
    patch = _string_assignment(source, "PREWRITE_PATCH")
    calls = {"gate": 0, "novelty": 0}
    gate_result = {"status": "PASS", "reason": "fixture pass"}
    novelty_score = {"value": 6.0}

    def base_gate(candidate, *, model="fixture", role="Winner"):
        calls["gate"] += 1
        return deepcopy(gate_result)

    namespace = {
        "os": os,
        "MODEL": "fixture",
        "evaluate_candidate": base_gate,
    }
    exec(compile(patch, "<prewriter-patch>", "exec"), namespace)

    def novelty_stub(candidate):
        calls["novelty"] += 1
        return {
            "judge_type": "novelty",
            "score": novelty_score["value"],
            "confidence": 1.0,
            "reason": "fixture",
            "issues": [],
            "critical_risk": False,
        }

    namespace["_run_prewriter_novelty"] = novelty_stub
    return namespace, calls, gate_result, novelty_score, patch


def _set_env(*, topic: str = "", scope: str = "aviation"):
    old = {
        "SHORTS_TOPIC": os.environ.get("SHORTS_TOPIC"),
        "SHORTS_CANDIDATE_SCOPE": os.environ.get("SHORTS_CANDIDATE_SCOPE"),
    }
    os.environ["SHORTS_TOPIC"] = topic
    os.environ["SHORTS_CANDIDATE_SCOPE"] = scope
    return old


def _restore_env(old):
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_low_novelty_blocks_before_writer_and_remembers_trusted_family():
    ns, calls, _, novelty, _ = _load_patch_namespace()
    old = _set_env()
    try:
        novelty["value"] = 4.0
        first = _trusted_candidate(
            "비행기 창문 모서리의 둥근 디자인",
            "modern aircraft passenger window with rounded/oval corners",
        )
        result = ns["evaluate_candidate"](first, role="Winner")
        assert result["status"] == "REGENERATE", result
        assert result["failure_type"] == "PREWRITER_NOVELTY_LOW", result
        assert calls == {"gate": 1, "novelty": 1}, calls

        renamed = _trusted_candidate(
            "비행기 창문 주변의 디자인",
            "modern aircraft passenger window with rounded/oval corners",
        )
        repeated = ns["evaluate_candidate"](renamed, role="Winner")
        assert repeated["status"] == "REGENERATE", repeated
        assert repeated["failure_type"] == "PREWRITER_NOVELTY_FAMILY_REPEAT", repeated
        # Deterministic family memory fires before another Gate/Judge/Writer path.
        assert calls == {"gate": 1, "novelty": 1}, calls
    finally:
        _restore_env(old)
    print("CASE A low novelty blocks pre-Writer and renamed trusted family is remembered: PASS")


def test_different_trusted_family_can_pass():
    ns, calls, _, novelty, _ = _load_patch_namespace()
    old = _set_env()
    try:
        novelty["value"] = 6.0
        candidate = _trusted_candidate(
            "비행기 엔진 나셀의 톱니 모양 가장자리",
            "jet engine nacelle/nozzle chevrons",
        )
        result = ns["evaluate_candidate"](candidate, role="Winner")
        assert result["status"] == "PASS", result
        assert calls == {"gate": 1, "novelty": 1}, calls
    finally:
        _restore_env(old)
    print("CASE B different trusted family with Novelty >=5 remains eligible: PASS")


def test_untrusted_model_canonical_never_becomes_family_memory():
    ns, calls, _, novelty, _ = _load_patch_namespace()
    old = _set_env()
    try:
        novelty["value"] = 4.0
        candidate = _trusted_candidate("모델 표기 A", "model-authored identity")
        candidate["_trusted_grounding_evidence"] = []
        first = ns["evaluate_candidate"](candidate, role="Winner")
        assert first["failure_type"] == "PREWRITER_NOVELTY_LOW", first

        renamed = deepcopy(candidate)
        renamed["topic"] = "모델 표기 B"
        second = ns["evaluate_candidate"](renamed, role="Winner")
        assert second["failure_type"] == "PREWRITER_NOVELTY_LOW", second
        # No trusted evidence => no deterministic identity-family shortcut.
        assert calls == {"gate": 2, "novelty": 2}, calls
    finally:
        _restore_env(old)
    print("CASE C untrusted canonical text cannot create family memory: PASS")


def test_fixed_topic_and_non_aviation_are_unchanged():
    ns, calls, _, novelty, _ = _load_patch_namespace()
    candidate = _trusted_candidate("고정 소재", "trusted fixed subject")
    novelty["value"] = 0.0

    old = _set_env(topic="비행기 고정 소재", scope="aviation")
    try:
        result = ns["evaluate_candidate"](candidate, role="Winner")
        assert result["status"] == "PASS", result
        assert calls == {"gate": 1, "novelty": 0}, calls
    finally:
        _restore_env(old)

    old = _set_env(topic="", scope="")
    try:
        result = ns["evaluate_candidate"](candidate, role="Winner")
        assert result["status"] == "PASS", result
        assert calls == {"gate": 2, "novelty": 0}, calls
    finally:
        _restore_env(old)
    print("CASE D fixed-topic and non-aviation paths remain unchanged: PASS")


def test_candidate_gate_reject_does_not_spend_novelty_call():
    ns, calls, gate_result, novelty, _ = _load_patch_namespace()
    old = _set_env()
    try:
        gate_result.clear()
        gate_result.update({"status": "REGENERATE", "reason": "fixture reject"})
        novelty["value"] = 10.0
        result = ns["evaluate_candidate"](
            _trusted_candidate("약한 소재", "trusted subject"),
            role="Winner",
        )
        assert result["status"] == "REGENERATE", result
        assert calls == {"gate": 1, "novelty": 0}, calls
    finally:
        _restore_env(old)
    print("CASE E Candidate Gate reject never spends pre-Writer Novelty call: PASS")


def test_safety_and_budget_contracts_unchanged():
    ns, _, _, _, patch = _load_patch_namespace()
    workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")

    assert ns["_PREWRITER_NOVELTY_MIN_SCORE"] == 5.0
    assert 'V3_MAX_API_CALLS: "60"' in workflow
    assert 'V3_MAX_COST_USD: "0.05"' in workflow
    assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in workflow
    assert "MAX_TOPIC_REGENERATIONS =" not in patch
    assert "MAX_REWRITES =" not in patch
    assert "V3_MAX_COST_USD =" not in installer
    assert "gpt-5.6-sol" not in patch.lower()
    assert patch.count('run_judge(\n        "novelty"') == 1
    assert "SHORTS_TOPIC" in patch and "SHORTS_CANDIDATE_SCOPE" in patch
    print("CASE F novelty floor, API/cost/retry/Writer/publish contracts unchanged: PASS")


def main():
    test_low_novelty_blocks_before_writer_and_remembers_trusted_family()
    test_different_trusted_family_can_pass()
    test_untrusted_model_canonical_never_becomes_family_memory()
    test_fixed_topic_and_non_aviation_are_unchanged()
    test_candidate_gate_reject_does_not_spend_novelty_call()
    test_safety_and_budget_contracts_unchanged()
    print("RUN 34705737709 PRE-WRITER NOVELTY REGRESSION: PASS")


if __name__ == "__main__":
    main()
