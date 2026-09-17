#!/usr/bin/env python3
"""Regression for publish-stable Run 35196073609 seed identity drift."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import runpy
import subprocess
import sys


SPOILER_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"
WRONG_FLAP_CANONICAL = "aircraft trailing-edge flap"


def _apply_candidate_composition() -> None:
    scripts = (
        "ci_topic_input_hotfix.py",
        "ci_aviation_candidate_context_hotfix.py",
        "ci_aviation_candidate_specificity_hotfix.py",
        "ci_aviation_context_signature_compat_hotfix.py",
        "ci_aviation_specificity_output_repair_hotfix.py",
        "ci_aviation_specificity_projection_hotfix.py",
        "ci_candidate_grounded_recovery_hotfix.py",
    )
    for script in scripts:
        subprocess.run([sys.executable, script], check=True)

    explorer_source = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
    required = (
        "# CANDIDATE_POOL_HANDOFF_V1",
        "# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1",
        "# RUN_35196073609_SEED_LINEAGE_PRESERVATION_V1",
    )
    for marker in required:
        assert marker in explorer_source, marker


def main() -> int:
    os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
    os.environ.pop("SHORTS_TOPIC", None)
    _apply_candidate_composition()

    from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding
    from quality.grounding_aware_candidate_supply import (
        REPO_OWNED_SEED_RECORD_REF_FIELD,
        all_trusted_candidate_records,
        grounded_seed_candidate_pool,
    )

    records = all_trusted_candidate_records()
    spoiler_record = next(
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("seed_candidate"), dict)
        and str(record["seed_candidate"].get("topic") or "").strip() == SPOILER_TOPIC
    )
    expected_canonical = str(spoiler_record.get("canonical_subject") or "").strip()
    assert expected_canonical and expected_canonical != WRONG_FLAP_CANONICAL

    # Exclude every other deterministic seed so the exact Run 35196073609
    # spoiler seed is the only bounded host-created fallback Candidate.
    other_topics = [
        str(record.get("seed_candidate", {}).get("topic") or "").strip()
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("seed_candidate"), dict)
        and str(record.get("seed_candidate", {}).get("topic") or "").strip()
        and str(record.get("seed_candidate", {}).get("topic") or "").strip()
        != SPOILER_TOPIC
    ]
    pool = grounded_seed_candidate_pool(
        recent_topics=other_topics,
        rejected_topics=[],
        max_candidates=1,
    )
    assert pool.get("status") == "CANDIDATE_POOL", pool
    candidate = pool["candidates"][0]
    assert candidate.get("topic") == SPOILER_TOPIC, candidate
    original_ref = candidate.get(REPO_OWNED_SEED_RECORD_REF_FIELD)
    assert original_ref is spoiler_record, "deterministic spoiler seed lost host record identity"

    candidate_explorer = runpy.run_path(
        "content/candidate_explorer.py",
        run_name="run_35196073609_candidate_explorer",
    )
    result = candidate_explorer["validate_explorer_output"](
        {"status": "CANDIDATE_POOL", "candidates": [candidate]}
    )
    assert result.get("status") == "SELECTED", result
    winner = result.get("winner") or {}

    # Exact production counterexample: before this fix the outer canonical
    # supplier changed this spoiler winner to aircraft trailing-edge flap.
    assert winner.get("topic") == SPOILER_TOPIC, winner
    assert winner.get("canonical_subject") == expected_canonical, winner
    assert winner.get("canonical_subject") != WRONG_FLAP_CANONICAL, winner
    assert winner.get(REPO_OWNED_SEED_RECORD_REF_FIELD) is spoiler_record, winner
    assert winner.get("_trusted_grounding_evidence"), winner
    assert evaluate_candidate_subject_grounding(winner)["status"] == "PASS", winner
    print(
        "CASE A Run 35196073609 spoiler seed stays on its exact canonical family "
        "through outer supply: PASS"
    )

    # A copied/model-authored value can copy the private field name and record
    # contents but cannot reproduce the active registry object's identity.
    spoof = deepcopy(candidate)
    assert spoof.get(REPO_OWNED_SEED_RECORD_REF_FIELD) is not spoiler_record
    spoof["canonical_subject"] = "UNTRUSTED_SENTINEL"
    restore = candidate_explorer["_run_35196073609_restore_seed_identity"]
    spoof_after = restore(spoof)
    assert spoof_after is spoof
    assert spoof_after.get("canonical_subject") == "UNTRUSTED_SENTINEL"
    print("CASE B copied private seed metadata gains no authority: PASS")

    ordinary = {"topic": "ordinary model candidate"}
    assert restore(ordinary) is ordinary
    print("CASE C ordinary/model Candidate path remains unchanged: PASS")

    hotfix_source = Path("ci_run_35196073609_seed_lineage_hotfix.py").read_text(
        encoding="utf-8"
    )
    for protected_constant in (
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
        "MAX_TOPIC_REGENERATIONS",
        "NOVELTY_HARD_REGENERATE_SCORE",
    ):
        assert protected_constant not in hotfix_source, protected_constant
    print("CASE D quality/retry/API/cost authorities untouched: PASS")
    print("RUN 35196073609 SEED LINEAGE REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
