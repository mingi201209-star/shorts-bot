"""PHASE 6 regression: comparison_segment emission via the existing V2.1
visual_explanation_contract_v2 authority (no new comparison schema).
"""
from __future__ import annotations

from quality.visual_explanation_contract_v2 import semantic_validate
from quality.visual_state_registry import SubjectStateRegistry
from video.aircraft_window_stress_comparison import (
    LEFT_CLAIM_ID,
    RIGHT_CLAIM_ID,
    build_window_corner_comparison_segment,
    stable_comparison_segment_id,
)
from video.aircraft_window_stress_signature import RELATION_ID


def _build(**overrides):
    kwargs = dict(scene_id=5, comparison_segment_id="seg-1", start_sec=0.0, end_sec=6.0)
    kwargs.update(overrides)
    return build_window_corner_comparison_segment(**kwargs)


def test_left_right_pass():
    contract = _build()
    assert contract is not None
    result = semantic_validate(contract, SubjectStateRegistry())
    assert result.ok, result.errors
    segment = contract["comparison_segments"][0]
    assert segment["presentation"] == "SPLIT_SCREEN"
    slots = {b["slot"]: b["claim_id"] for b in segment["bindings"]}
    assert slots == {"LEFT": LEFT_CLAIM_ID, "RIGHT": RIGHT_CLAIM_ID}
    relation = contract["relations"][0]
    assert relation["type"] == "CONTRAST"
    assert set(relation["members"]) == {LEFT_CLAIM_ID, RIGHT_CLAIM_ID}
    assert relation["id"] == RELATION_ID


def test_bindings_exactly_two_unique():
    contract = _build()
    bindings = contract["comparison_segments"][0]["bindings"]
    assert len(bindings) == 2
    assert len({b["claim_id"] for b in bindings}) == 2


def test_relation_members_match_segment_bindings():
    contract = _build()
    relation = contract["relations"][0]
    segment = contract["comparison_segments"][0]
    binding_ids = {b["claim_id"] for b in segment["bindings"]}
    assert set(relation["members"]) == binding_ids


def test_left_left_rejected():
    contract = _build()
    contract["comparison_segments"][0]["bindings"][1]["slot"] = "LEFT"
    result = semantic_validate(contract, SubjectStateRegistry())
    assert not result.ok
    assert any("LEFT and RIGHT" in e for e in result.errors)


def test_right_missing_rejected():
    contract = _build()
    contract["comparison_segments"][0]["bindings"] = [
        {"claim_id": LEFT_CLAIM_ID, "slot": "LEFT"},
    ]
    contract["relations"][0]["members"] = [LEFT_CLAIM_ID]
    result = semantic_validate(contract, SubjectStateRegistry())
    assert not result.ok


def test_duplicate_claim_rejected():
    contract = _build()
    contract["comparison_segments"][0]["bindings"][1]["claim_id"] = LEFT_CLAIM_ID
    result = semantic_validate(contract, SubjectStateRegistry())
    assert not result.ok
    assert any("duplicate claim bindings" in e for e in result.errors)


def test_unknown_claim_rejected():
    contract = _build()
    contract["comparison_segments"][0]["bindings"][1]["claim_id"] = "unknown_claim_id"
    contract["relations"][0]["members"] = [LEFT_CLAIM_ID, "unknown_claim_id"]
    result = semantic_validate(contract, SubjectStateRegistry())
    assert not result.ok


def test_relation_mismatch_rejected():
    contract = _build()
    contract["relations"][0]["members"] = [LEFT_CLAIM_ID, LEFT_CLAIM_ID]
    result = semantic_validate(contract, SubjectStateRegistry())
    assert not result.ok


def test_malformed_time_range_rejected_by_builder():
    # end_sec <= start_sec: builder must return None (shape-invalid,
    # non-selection), never raise.
    assert _build(start_sec=5.0, end_sec=2.0) is None


def test_stable_comparison_segment_id_deterministic():
    a = stable_comparison_segment_id("modern_aircraft_passenger_window", "squarish_window_fatigue_rupture")
    b = stable_comparison_segment_id("modern_aircraft_passenger_window", "squarish_window_fatigue_rupture")
    c = stable_comparison_segment_id("modern_aircraft_passenger_window", "rounded_window_stress_distribution")
    assert a == b
    assert a != c


def main():
    test_left_right_pass()
    test_bindings_exactly_two_unique()
    test_relation_members_match_segment_bindings()
    test_left_left_rejected()
    test_right_missing_rejected()
    test_duplicate_claim_rejected()
    test_unknown_claim_rejected()
    test_relation_mismatch_rejected()
    test_malformed_time_range_rejected_by_builder()
    test_stable_comparison_segment_id_deterministic()
    print("AIRCRAFT WINDOW STRESS COMPARISON SEGMENT PHASE 6 REGRESSION: PASS")


if __name__ == "__main__":
    main()
