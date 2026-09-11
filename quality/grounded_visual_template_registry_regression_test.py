"""PHASE 3 regression: video/grounded_visual_template_registry.py.

No network/API call. Confirms the registry is a pure lookup (does not decide
eligibility itself) and registers exactly one template.
"""
from __future__ import annotations

from video.aircraft_window_stress_grounding import (
    supports_aircraft_window_stress_from_grounding,
)
from video.grounded_visual_template_registry import (
    find_grounded_visual_template,
    known_template_ids,
)


def test_known_templates_is_exactly_one():
    assert known_template_ids() == frozenset({"AIRCRAFT_WINDOW_STRESS_V1"})


def test_lookup_none_for_ineligible_scene():
    assert find_grounded_visual_template(None) is None
    assert find_grounded_visual_template({}) is None


def test_lookup_matches_eligible_scene():
    scene = {
        "keyword": "modern aircraft window squarish fatigue rupture comet",
        "role": "payoff",
        "_canonical_visual_supply": {
            "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
            "grounding_source": "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV",
        },
    }
    params = supports_aircraft_window_stress_from_grounding(scene)
    assert params is not None
    capability = find_grounded_visual_template(params)
    assert capability is not None
    assert capability.template_id == "AIRCRAFT_WINDOW_STRESS_V1"
    assert capability.presentation == "CONTRAST"
    assert capability.comparison_presentation == "SPLIT_SCREEN"
    assert capability.required_claim_count == 2


def test_lookup_none_for_unknown_template_id():
    assert find_grounded_visual_template({"template_id": "SOME_OTHER_TEMPLATE"}) is None


def test_registry_lookup_does_not_replace_eligibility():
    # A hand-built params dict claiming the right template_id but with no
    # real grounding behind it still resolves capability -- the registry
    # trusts its input's template_id field and does not re-derive
    # eligibility. That is by design: eligibility is the adapter's job, not
    # the registry's. This test documents the boundary rather than treating
    # it as a bug.
    fabricated = {"template_id": "AIRCRAFT_WINDOW_STRESS_V1"}
    assert find_grounded_visual_template(fabricated) is not None


def main():
    test_known_templates_is_exactly_one()
    test_lookup_none_for_ineligible_scene()
    test_lookup_matches_eligible_scene()
    test_lookup_none_for_unknown_template_id()
    test_registry_lookup_does_not_replace_eligibility()
    print("GROUNDED VISUAL TEMPLATE REGISTRY PHASE 3 REGRESSION: PASS")


if __name__ == "__main__":
    main()
