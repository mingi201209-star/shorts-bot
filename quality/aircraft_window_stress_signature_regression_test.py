"""PHASE 4 regression: param_signature / attempt identity stability.

No network/API call.
"""
from __future__ import annotations

from video.aircraft_window_stress_grounding import (
    CANONICAL_SUBJECT,
    canonical_subject_id,
    supports_aircraft_window_stress_from_grounding,
)
from video.aircraft_window_stress_signature import (
    build_deterministic_explanation_params,
    build_grounding_fingerprint,
    build_param_signature,
)
from quality.grounded_deterministic_explanation import (
    validate_deterministic_explanation_params_shape,
)

_FAA_SOURCE = "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"


def _scene(*, run_id="RUNX", timestamp="T0", scene_index=5, keyword_suffix="", claim=None):
    scene = {
        "keyword": f"modern aircraft window squarish fatigue rupture comet{keyword_suffix}",
        "role": "payoff",
        "_canonical_visual_supply": {
            "canonical_subject": CANONICAL_SUBJECT,
            "grounding_source": _FAA_SOURCE,
        },
        # Deliberately included to prove these do NOT affect the signature.
        "_run_id": run_id,
        "_timestamp": timestamp,
        "_scene_index": scene_index,
        "_output_path": f"/tmp/run-{run_id}/scene-{scene_index}.mp4",
        "_uuid": "11111111-2222-3333-4444-555555555555",
    }
    if claim:
        scene["owned_claim_id"] = claim
    return scene


def _full_params(scene, segment_id="seg-1"):
    eligibility = supports_aircraft_window_stress_from_grounding(scene)
    assert eligibility is not None
    return build_deterministic_explanation_params(eligibility, comparison_segment_id=segment_id)


def test_full_params_pass_shape_validator():
    params = _full_params(_scene())
    result = validate_deterministic_explanation_params_shape(params)
    assert result.ok, result.errors


def test_same_evidence_same_signature():
    a = _full_params(_scene(run_id="A", timestamp="t1", scene_index=5))
    b = _full_params(_scene(run_id="A", timestamp="t1", scene_index=5))
    assert a["param_signature"] == b["param_signature"]


def test_run_id_change_same_signature():
    a = _full_params(_scene(run_id="RUN_ONE"))
    b = _full_params(_scene(run_id="RUN_TWO"))
    assert a["param_signature"] == b["param_signature"]


def test_timestamp_change_same_signature():
    a = _full_params(_scene(timestamp="2026-01-01T00:00:00Z"))
    b = _full_params(_scene(timestamp="2099-12-31T23:59:59Z"))
    assert a["param_signature"] == b["param_signature"]


def test_scene_index_alone_same_signature():
    a = _full_params(_scene(scene_index=5))
    b = _full_params(_scene(scene_index=7))
    assert a["param_signature"] == b["param_signature"]


def test_different_provenance_different_signature():
    fp_a = build_grounding_fingerprint(
        canonical_subject_id=canonical_subject_id(CANONICAL_SUBJECT),
        grounding_provenance_ref=_FAA_SOURCE,
    )
    fp_b = build_grounding_fingerprint(
        canonical_subject_id=canonical_subject_id(CANONICAL_SUBJECT),
        grounding_provenance_ref="https://example.org/different-source",
    )
    assert fp_a != fp_b

    sig_a = build_param_signature(
        template_id="AIRCRAFT_WINDOW_STRESS_V1",
        canonical_subject_id=canonical_subject_id(CANONICAL_SUBJECT),
        owned_claim_id="squarish_window_fatigue_rupture",
        presentation="CONTRAST",
        grounding_fingerprint=fp_a,
    )
    sig_b = build_param_signature(
        template_id="AIRCRAFT_WINDOW_STRESS_V1",
        canonical_subject_id=canonical_subject_id(CANONICAL_SUBJECT),
        owned_claim_id="squarish_window_fatigue_rupture",
        presentation="CONTRAST",
        grounding_fingerprint=fp_b,
    )
    assert sig_a != sig_b


def test_different_claim_identity_different_signature():
    a = _full_params(_scene(claim="squarish_window_fatigue_rupture"))
    b = _full_params(_scene(claim="rounded_window_stress_distribution"))
    assert a["param_signature"] != b["param_signature"]


def test_narration_keyword_variation_does_not_change_signature():
    a = _full_params(_scene(keyword_suffix=""))
    b = _full_params(_scene(keyword_suffix=" extra narration words here"))
    assert a["param_signature"] == b["param_signature"]


def test_signature_contains_no_forbidden_raw_fields():
    params = _full_params(_scene(run_id="SECRET_RUN_ID_42"))
    sig = params["param_signature"]
    assert "SECRET_RUN_ID_42" not in sig
    assert "11111111-2222-3333-4444-555555555555" not in sig
    assert "/tmp/run-" not in sig


def test_signature_is_none_without_comparison_segment_id():
    scene = _scene()
    eligibility = supports_aircraft_window_stress_from_grounding(scene)
    assert build_deterministic_explanation_params(eligibility, comparison_segment_id="") is None


def main():
    test_full_params_pass_shape_validator()
    test_same_evidence_same_signature()
    test_run_id_change_same_signature()
    test_timestamp_change_same_signature()
    test_scene_index_alone_same_signature()
    test_different_provenance_different_signature()
    test_different_claim_identity_different_signature()
    test_narration_keyword_variation_does_not_change_signature()
    test_signature_contains_no_forbidden_raw_fields()
    test_signature_is_none_without_comparison_segment_id()
    print("AIRCRAFT WINDOW STRESS PARAM SIGNATURE PHASE 4 REGRESSION: PASS")


if __name__ == "__main__":
    main()
