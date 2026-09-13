#!/usr/bin/env python3
"""Exact regression for production Run 34784063294 (#552).

Authority:
- Candidate grounding already passed on #552.
- repeated Hook/Core Question repair fell through to a generic Candidate-owned
  counterintuitive_result and still scored below the unchanged fixed-topic floor;
- a non-FACT Rewrite also produced terminal ``하는데요`` and was discarded.

This regression permits neither a threshold relaxation nor a new model call.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_handoff import _validate_with_bounded_hook_repair
from quality.consensus import GOOD_ENOUGH_FLOORS


ROOT = Path(__file__).resolve().parents[1]
SPOILER_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"


def _spoiler_record():
    matches = [
        record
        for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
        if (record.get("seed_candidate") or {}).get("topic") == SPOILER_TOPIC
    ]
    assert len(matches) == 1, matches
    return matches[0]


def _repeated_hook_candidate():
    record = _spoiler_record()
    raw = deepcopy(record["seed_candidate"])
    micro = deepcopy(raw["micro_narrative"])
    micro["hook"] = micro["core_question"]
    raw["micro_narrative"] = micro

    # Reproduce the #552 ordering problem: the LLM Candidate itself does not
    # provide a usable observation, so the legacy fallback would eventually
    # select a generic explanatory field. The repo-owned seed still has its
    # trusted observable first beat.
    raw["specific_observation"] = ""
    raw["counterintuitive_result"] = "스포일러는 착륙 뒤 양력을 줄입니다."
    return raw


def _validator(candidate, *, prefix):
    del prefix
    hook = str((candidate.get("micro_narrative") or {}).get("hook") or "").strip()
    core = str((candidate.get("micro_narrative") or {}).get("core_question") or "").strip()
    if hook == core:
        raise ValueError("micro_narrative hook repeats Core Question")
    return deepcopy(candidate)


def test_exact_fixed_topic_uses_repo_owned_observation_first():
    record = _spoiler_record()
    raw = _repeated_hook_candidate()
    validated, source = _validate_with_bounded_hook_repair(
        raw,
        prefix="Run34784063294",
        validate_candidate_fn=_validator,
        fixed_topic=SPOILER_TOPIC,
        trusted_records=CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )
    expected = str(record["seed_candidate"]["specific_observation"]).strip()
    actual = str(validated["micro_narrative"]["hook"]).strip()
    assert source == "exact_fixed_topic_seed.specific_observation", source
    assert actual == expected, (actual, expected)
    assert actual == "착륙 직후 날개 윗면의 판 모양 스포일러가 위로 솟습니다.", actual
    print("TEST A exact fixed-topic trusted observation first: PASS")


def test_modified_topic_cannot_borrow_exact_seed_authority():
    raw = _repeated_hook_candidate()
    raw["topic"] = SPOILER_TOPIC + "?"
    validated, source = _validate_with_bounded_hook_repair(
        raw,
        prefix="Run34784063294-modified",
        validate_candidate_fn=_validator,
        fixed_topic=SPOILER_TOPIC,
        trusted_records=CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )
    assert source == "counterintuitive_result", source
    assert source != "exact_fixed_topic_seed.specific_observation", source
    assert validated["micro_narrative"]["hook"] == raw["counterintuitive_result"]
    print("TEST B modified topic cannot borrow exact seed: PASS")


def test_terminal_hada_rewrite_is_repaired_without_new_call():
    # ci_speech_style_hotfix.py must have been applied before this regression,
    # exactly as production composition does.
    import quality.rewrite_engine as rewrite_engine

    assert hasattr(rewrite_engine, "_repair_rewrite_speech_style"), (
        "speech-style production hotfix was not applied before regression"
    )
    script = {
        "title": "Run 34784063294",
        "scenes": [
            {
                "text": "스포일러가 고압 공기를 분산시켜 하강 속도를 조절하는데요.",
                "visual_goal": "착륙 직후 날개 윗면의 스포일러",
                "keyword": "aircraft wing spoiler landing",
            }
        ],
    }
    repaired = rewrite_engine._repair_rewrite_speech_style(script)
    assert repaired is not None, repaired
    assert repaired["scenes"][0]["text"] == (
        "스포일러가 고압 공기를 분산시켜 하강 속도를 조절합니다."
    ), repaired

    # Scope guard: only terminal ~하는데요 is normalized by this new rule.
    nonterminal = deepcopy(script)
    nonterminal["scenes"][0]["text"] = (
        "스포일러가 작동하는데요, 다음 장면에서 원리를 설명합니다."
    )
    assert rewrite_engine._repair_rewrite_speech_style(nonterminal) is None
    print("TEST C terminal 하는데요 deterministic formal repair: PASS")


def test_safety_budgets_and_floor_unchanged():
    workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    assert 'V3_MAX_API_CALLS: "60"' in workflow
    assert 'V3_MAX_COST_USD: "0.05"' in workflow

    # #552 was rejected at Hook 6.0 because the production Good Enough Hook
    # floor is 7.0. Read that real runtime authority instead of inventing a
    # fixed-topic-only constant in the feedback installer.
    assert GOOD_ENOUGH_FLOORS["hook"] == 7.0, GOOD_ENOUGH_FLOORS
    print("TEST D API/cost/Hook floor unchanged: PASS")


def main() -> int:
    test_exact_fixed_topic_uses_repo_owned_observation_first()
    test_modified_topic_cannot_borrow_exact_seed_authority()
    test_terminal_hada_rewrite_is_repaired_without_new_call()
    test_safety_budgets_and_floor_unchanged()
    print("RUN 34784063294 HOOK RECOVERY REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
