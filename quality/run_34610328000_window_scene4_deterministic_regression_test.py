from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video.aircraft_window_stress_grounding import (
    supports_aircraft_window_stress_from_grounding,
)

FAA_SOURCE = "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"
CANONICAL = "modern aircraft passenger window with rounded/oval corners"


def scene(*, role: str, keyword: str, causal_role: str = "", owned_claim_id: str = ""):
    value = {
        "scene_id": 4,
        "role": role,
        "text": "grounded fixture",
        "visual_goal": "grounded fixture",
        "keyword": keyword,
        "_canonical_visual_supply": {
            "canonical_subject": CANONICAL,
            "identity_confidence": 0.97,
            "grounding_source": FAA_SOURCE,
        },
    }
    if causal_role:
        value["causal_role"] = causal_role
    if owned_claim_id:
        value["owned_claim_id"] = owned_claim_id
    return value


def main():
    # Authority counterexample: Run 34610328000 stopped at Scene 4 after stock
    # and still supply failed. The final runtime Scene role is the existing
    # reveal/mechanism-change role and its Grounded Keyword Contract output is
    # exact below. Before the fix, the result-only eligibility restriction
    # returned None even though this claim is in the template's closed trusted
    # three-claim set.
    scene4 = scene(
        role="reveal",
        keyword="modern aircraft window rounded stress distribution",
    )
    result4 = supports_aircraft_window_stress_from_grounding(scene4)
    assert result4 is not None
    assert result4["template_id"] == "AIRCRAFT_WINDOW_STRESS_V1"
    assert result4["evidence_source"] == "TRUSTED_GROUNDING"
    assert result4["owned_claim_id"] == "rounded_window_stress_distribution"

    # The authoritative causal role, when carried, resolves to the same claim.
    scene4_causal = scene(
        role="reveal",
        causal_role="mechanism_change",
        keyword="modern aircraft window rounded stress distribution",
    )
    assert (
        supports_aircraft_window_stress_from_grounding(scene4_causal)["owned_claim_id"]
        == "rounded_window_stress_distribution"
    )

    # Same one-template capability may safely rescue either adjacent grounded
    # beat if visual supply exhausts there. These are not new claim families.
    scene3 = scene(
        role="causal_clue",
        keyword="modern aircraft window squarish stress concentration comet",
    )
    assert (
        supports_aircraft_window_stress_from_grounding(scene3)["owned_claim_id"]
        == "squarish_window_stress_concentration"
    )

    scene5 = scene(
        role="payoff",
        keyword="modern aircraft window squarish fatigue rupture comet",
    )
    assert (
        supports_aircraft_window_stress_from_grounding(scene5)["owned_claim_id"]
        == "squarish_window_fatigue_rupture"
    )

    # Fail closed on an unrelated/unknown structural role even if generic
    # subject anchors and a stress word are present.
    unknown_role = scene(
        role="phenomenon",
        keyword="modern aircraft window rounded stress distribution",
    )
    assert supports_aircraft_window_stress_from_grounding(unknown_role) is None

    # Explicit claim ownership may never disagree with the authoritative role.
    mismatch = scene(
        role="reveal",
        keyword="modern aircraft window rounded stress distribution",
        owned_claim_id="squarish_window_fatigue_rupture",
    )
    assert supports_aircraft_window_stress_from_grounding(mismatch) is None

    # Foreign explicit claim remains blocked.
    foreign = scene(
        role="reveal",
        keyword="modern aircraft window rounded stress distribution",
        owned_claim_id="flap_low_landing_speed",
    )
    assert supports_aircraft_window_stress_from_grounding(foreign) is None

    # Vision-only evidence still cannot grant INPUT eligibility.
    no_grounding = scene(
        role="reveal",
        keyword="modern aircraft window rounded stress distribution",
    )
    no_grounding.pop("_canonical_visual_supply")
    no_grounding["_vision_evidence"] = {"state": "VERIFIED", "pass": True}
    assert supports_aircraft_window_stress_from_grounding(no_grounding) is None

    print("RUN 34610328000 WINDOW SCENE4 DETERMINISTIC REGRESSION: PASS")


if __name__ == "__main__":
    main()
