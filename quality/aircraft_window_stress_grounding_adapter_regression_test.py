"""PHASE 2 regression: grounding eligibility adapter for
AIRCRAFT_WINDOW_STRESS_V1 (video/aircraft_window_stress_grounding.py).

No network/API call. Confirms the adapter reads only existing trusted
grounding/claim registry authority -- never Vision EvidenceState -- and stays
fail-closed (returns None) for every negative control required by this task.
"""
from __future__ import annotations

from video.aircraft_window_stress_grounding import (
    CANONICAL_SUBJECT,
    SUPPORTED_OWNED_CLAIM_IDS,
    canonical_subject_id,
    supports_aircraft_window_stress_from_grounding,
)

_FAA_SOURCE = "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"


def _window_supply(canonical=CANONICAL_SUBJECT, source=_FAA_SOURCE):
    return {"canonical_subject": canonical, "grounding_source": source}


def _result_scene(**overrides):
    scene = {
        "keyword": "modern aircraft window squarish fatigue rupture comet",
        "role": "payoff",
        "_canonical_visual_supply": _window_supply(),
    }
    scene.update(overrides)
    return scene


def test_positive_eligible_result_scene():
    params = supports_aircraft_window_stress_from_grounding(_result_scene())
    assert params is not None
    assert params["template_id"] == "AIRCRAFT_WINDOW_STRESS_V1"
    assert params["evidence_source"] == "TRUSTED_GROUNDING"
    assert params["owned_claim_id"] in SUPPORTED_OWNED_CLAIM_IDS
    assert params["canonical_subject_id"] == canonical_subject_id(CANONICAL_SUBJECT)


def test_positive_explicit_owned_claim_matches():
    for claim_id in SUPPORTED_OWNED_CLAIM_IDS:
        scene = _result_scene(owned_claim_id=claim_id)
        params = supports_aircraft_window_stress_from_grounding(scene)
        assert params is not None, claim_id
        assert params["owned_claim_id"] == claim_id


# ---- Required negative controls ----

def test_negative_building_window():
    scene = _result_scene(
        keyword="modern building window frame corner stress",
        _canonical_visual_supply=_window_supply(
            canonical="modern office building window with square corners",
        ),
    )
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_car_window():
    scene = _result_scene(
        keyword="car window rounded corner glass",
        _canonical_visual_supply=_window_supply(
            canonical="passenger car side window with rounded corners",
        ),
    )
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_generic_window():
    scene = _result_scene(
        keyword="generic window corner shape",
        _canonical_visual_supply=_window_supply(canonical="a window with corners"),
    )
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_cockpit_windshield():
    scene = _result_scene(
        keyword="aircraft cockpit windshield frame",
        _canonical_visual_supply=_window_supply(
            canonical="aircraft cockpit windshield with flat panels",
        ),
    )
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_aircraft_window_unrelated_claim():
    # Same subject, but the owned claim belongs to a different grounded
    # record entirely (the flap record) -- must stay fail-closed.
    scene = _result_scene(owned_claim_id="flap_low_landing_speed")
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_no_grounding():
    scene = _result_scene()
    del scene["_canonical_visual_supply"]
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_wrong_owned_claim():
    scene = _result_scene(owned_claim_id="landing_flap_low_speed_need")
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_contradicted_or_absent_grounding():
    # The trusted-grounding *input* layer has no negative/contradicted state
    # today (task section 3) -- only the separate Vision-driven
    # quality.visual_state_evidence.EvidenceState has CONTRADICTED, and that
    # is output-side (verifies an already-produced render), never consulted
    # here. An empty/absent supply is the only "not usable" input-layer state
    # this V1 models, and it is already covered by no-grounding above; this
    # case additionally proves a present-but-empty supply dict (as if a
    # negative result had been written into the same slot) is equally
    # fail-closed, not silently treated as valid.
    scene = _result_scene(_canonical_visual_supply={})
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_negative_vision_only_verified_cannot_raise_eligibility():
    # A Vision-side VERIFIED-shaped signal, with no trusted grounding
    # attached, must never raise eligibility -- Vision EvidenceState is
    # output authority (task section 1), never input authority here.
    scene = _result_scene()
    del scene["_canonical_visual_supply"]
    scene["_vision_evidence"] = {
        "pass": True,
        "visible_subject_groups": {"aircraft": True, "window": True},
        "state": "VERIFIED",
    }
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_adapter_never_imports_vision_evidence_state():
    # Structural proof the adapter cannot consult Vision EvidenceState even
    # by accident: the module never has an import statement naming
    # quality.visual_state_evidence or EvidenceState (prose explaining *why*
    # it doesn't, in the module's own docstring, is fine and expected).
    import ast
    import video.aircraft_window_stress_grounding as module

    tree = ast.parse(inspect_getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "quality.visual_state_evidence"
            assert not any(alias.name == "EvidenceState" for alias in node.names)
        elif isinstance(node, ast.Import):
            assert not any(alias.name == "quality.visual_state_evidence" for alias in node.names)


def inspect_getsource(module):
    import inspect

    return inspect.getsource(module)


def test_missing_anchor_words_rejected():
    scene = _result_scene(keyword="modern aircraft fuselage panel corner")
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def test_non_result_scene_rejected():
    scene = _result_scene(role="mechanism_1")
    assert supports_aircraft_window_stress_from_grounding(scene) is None


def main():
    test_positive_eligible_result_scene()
    test_positive_explicit_owned_claim_matches()
    test_negative_building_window()
    test_negative_car_window()
    test_negative_generic_window()
    test_negative_cockpit_windshield()
    test_negative_aircraft_window_unrelated_claim()
    test_negative_no_grounding()
    test_negative_wrong_owned_claim()
    test_negative_contradicted_or_absent_grounding()
    test_negative_vision_only_verified_cannot_raise_eligibility()
    test_adapter_never_imports_vision_evidence_state()
    test_missing_anchor_words_rejected()
    test_non_result_scene_rejected()
    print("AIRCRAFT WINDOW STRESS GROUNDING ADAPTER PHASE 2 REGRESSION: PASS")


if __name__ == "__main__":
    main()
