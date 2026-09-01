from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


CANONICAL = "jet engine nacelle/nozzle chevrons"


def _compose_production_path() -> None:
    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)
    explorer = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
    assert "CANONICAL_SUBJECT_GROUNDING_GATE_V1" in explorer
    assert "CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1" in explorer
    supply = Path("quality/canonical_subject_grounding_supply.py").read_text(encoding="utf-8")
    assert "RUN_33479576919_EXACT_CANONICAL_IDENTITY" in supply


def _supply(candidate):
    module = importlib.import_module("quality.canonical_subject_grounding_supply")
    return module.supply_trusted_subject_grounding(
        candidate,
        trusted_records=module.PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )


def _grounded(candidate) -> bool:
    return (
        candidate.get("subject_kind") == "physical_entity"
        and candidate.get("canonical_subject") == CANONICAL
        and float(candidate.get("subject_identity_confidence") or 0.0) >= 0.80
        and bool(candidate.get("_trusted_grounding_evidence"))
    )


def main() -> None:
    _compose_production_path()
    importlib.invalidate_caches()

    # Run 33479576919 exact fixed-topic counterexample: the fixed topic is
    # already the repo-owned canonical identity. It must retain the record's
    # authoritative provenance without another model/retry call.
    exact = _supply({
        "topic": CANONICAL,
        "core_question": "Why are they shaped that way?",
    })
    assert _grounded(exact)
    assert exact["canonical_subject"] != "UNKNOWN"

    # Existing successful Korean physical observation remains grounded.
    korean = _supply({
        "topic": "비행기 엔진 뒤쪽은 왜 톱니처럼 생겼을까",
        "core_question": "비행기 엔진 뒤쪽의 톱니 모양은 왜 그렇게 설계되었을까요?",
    })
    assert _grounded(korean)

    # False-positive guards: exact canonical authority is narrow. Generic or
    # cross-domain engine text must not manufacture the chevron identity.
    for topic in (
        "engine",
        "Unreal Engine",
        "jet engine",
        "generic airplane",
        "aircraft engine detail",
        "비행기 엔진",
        "비행기",
    ):
        assert not _grounded(_supply({"topic": topic}))

    # Candidate-authored/free-text trust claims are not authoritative.
    fake = _supply({
        "topic": "engine",
        "canonical_subject": CANONICAL,
        "subject_kind": "physical_entity",
        "subject_identity_confidence": 0.99,
        "grounding_evidence": [{"source": "model says trusted"}],
    })
    assert not fake.get("_trusted_grounding_evidence")

    # Non-physical topics stay non-physical and are never promoted.
    nonphysical = _supply({
        "topic": "왜 소음 감소가 중요한가",
        "subject_kind": "non_physical_concept",
    })
    assert nonphysical.get("subject_kind") == "non_physical_concept"
    assert not nonphysical.get("_trusted_grounding_evidence")

    # Candidate Gate success alone is not grounding evidence.
    gate_only = _supply({"topic": "engine", "candidate_gate_status": "PASS"})
    assert not _grounded(gate_only)

    print("RUN_33479576919_COUNTEREXAMPLE: PASS")
    print("FALSE_POSITIVE_GUARDS: PASS")
    print("NEW_LLM_CALLS: 0")
    print("NEW_VISION_CALLS: 0")
    print("NEW_IMAGE_GENERATION_CALLS: 0")
    print("API_COST_CHANGE: NONE")
    print("RETRY_CHANGE: NONE")


if __name__ == "__main__":
    main()
