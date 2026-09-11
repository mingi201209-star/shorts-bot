"""PHASE 1 regression: shape schema + parser baseline for
PRODUCE/DETERMINISTIC_EXPLANATION params, template AIRCRAFT_WINDOW_STRESS_V1.

No network/API call. No production behavior change -- this only exercises
the new quality/grounded_deterministic_explanation.py module and confirms it
is not yet wired into any runtime call path.
"""
from __future__ import annotations

from pathlib import Path

from quality.grounded_deterministic_explanation import (
    SUPPORTED_TEMPLATE_IDS,
    validate_deterministic_explanation_params_shape,
)
from quality.visual_escalation_router import (
    EscalationMethod,
    RoutingAction,
    semantic_validate_routing_decision,
)

ROOT = Path(__file__).resolve().parents[1]


def _positive_params():
    return {
        "template_id": "AIRCRAFT_WINDOW_STRESS_V1",
        "presentation": "CONTRAST",
        "canonical_subject_id": "modern_aircraft_passenger_window_rounded_oval_corners",
        "owned_claim_id": "squarish_window_fatigue_rupture",
        "evidence_source": "TRUSTED_GROUNDING",
        "grounding_provenance_ref": "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV",
        "grounding_fingerprint": "faa-comet-window-corners-v1",
        "comparison_segment_id": "seg-window-corner-contrast-1",
        "param_signature": (
            "AIRCRAFT_WINDOW_STRESS_V1|"
            "modern_aircraft_passenger_window_rounded_oval_corners|"
            "squarish_window_fatigue_rupture|"
            "window_corner_contrast|CONTRAST|faa-comet-window-corners-v1"
        ),
    }


def test_positive_fixture_passes():
    params = _positive_params()
    result = validate_deterministic_explanation_params_shape(params)
    assert result.ok, result.errors
    assert params["template_id"] in SUPPORTED_TEMPLATE_IDS

    decision = {
        "action": RoutingAction.PRODUCE,
        "method": EscalationMethod.DETERMINISTIC_EXPLANATION,
        "param_signature": params["param_signature"],
        "reason": "grounded window-corner comparison eligible",
    }
    outer = semantic_validate_routing_decision(decision)
    assert outer.ok, outer.errors


def test_malformed_shape_rejected_missing_field():
    params = _positive_params()
    del params["grounding_fingerprint"]
    result = validate_deterministic_explanation_params_shape(params)
    assert not result.ok
    assert any("grounding_fingerprint" in e for e in result.errors)


def test_malformed_shape_rejected_wrong_type():
    params = _positive_params()
    params["owned_claim_id"] = 12345  # not a string
    result = validate_deterministic_explanation_params_shape(params)
    assert not result.ok
    assert any("owned_claim_id" in e for e in result.errors)


def test_malformed_shape_rejected_field_leakage():
    params = _positive_params()
    params["action"] = "PRODUCE"  # RoutingDecision-level field, not a params field
    result = validate_deterministic_explanation_params_shape(params)
    assert not result.ok
    assert any("unsupported fields" in e for e in result.errors)


def test_semantic_invalid_rejected_unsupported_template():
    params = _positive_params()
    params["template_id"] = "AIRCRAFT_WINDOW_STRESS_V2"  # does not exist in V1
    result = validate_deterministic_explanation_params_shape(params)
    assert not result.ok
    assert any("template_id" in e for e in result.errors)


def test_semantic_invalid_rejected_unsupported_evidence_source():
    for bad_source in ("VISION", "SCRIPT_ONLY", "INFERRED", "UNKNOWN", "LLM"):
        params = _positive_params()
        params["evidence_source"] = bad_source
        result = validate_deterministic_explanation_params_shape(params)
        assert not result.ok, f"{bad_source} must be rejected"
        assert any("evidence_source" in e for e in result.errors)


def test_semantic_invalid_rejected_unsupported_presentation():
    params = _positive_params()
    params["presentation"] = "SPLIT_SCREEN"  # that is the segment-level field, not this one
    result = validate_deterministic_explanation_params_shape(params)
    assert not result.ok
    assert any("presentation" in e for e in result.errors)


def test_no_stub_or_todo_templates_registered():
    # V1 registers exactly AIRCRAFT_WINDOW_STRESS_V1, nothing else.
    assert SUPPORTED_TEMPLATE_IDS == frozenset({"AIRCRAFT_WINDOW_STRESS_V1"})


def test_production_behavior_unchanged_not_wired_yet():
    # PHASE 1 must not touch any runtime call path. video/visual_explanation.py
    # is the live production consumer of deterministic explanation templates
    # (WINGLET_VORTEX, CHEVRON_FLOW_MIXING, FLOW_INTERFACE); it must not import
    # this new module yet.
    text = (ROOT / "video" / "visual_explanation.py").read_text(encoding="utf-8")
    assert "grounded_deterministic_explanation" not in text
    assert "AIRCRAFT_WINDOW_STRESS_V1" not in text


def main():
    test_positive_fixture_passes()
    test_malformed_shape_rejected_missing_field()
    test_malformed_shape_rejected_wrong_type()
    test_malformed_shape_rejected_field_leakage()
    test_semantic_invalid_rejected_unsupported_template()
    test_semantic_invalid_rejected_unsupported_evidence_source()
    test_semantic_invalid_rejected_unsupported_presentation()
    test_no_stub_or_todo_templates_registered()
    test_production_behavior_unchanged_not_wired_yet()
    print("GROUNDED DETERMINISTIC EXPLANATION PHASE 1 (schema/parser) REGRESSION: PASS")


if __name__ == "__main__":
    main()
