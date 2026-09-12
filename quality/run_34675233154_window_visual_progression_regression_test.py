"""Regression for Run 34675233154 visual-progression failures.

Authority failures reproduced here:
1) Scene 2 used the exact Scene-1 verified rounded-window still even though the
   grounded question query was about rounded corners; the neutral shape
   comparison should be eligible before any causal claim is revealed.
2) Scene 5 was rejected as an information repeat of Scene 4 solely because
   both grounded AIRCRAFT_WINDOW_STRESS_V1 states annotated the same physical
   verified still. Distinct trusted claim/presentation states are information
   progression; exact duplicates must still fail closed.
"""

import ast
from pathlib import Path

from video.aircraft_window_stress_grounding import (
    SHAPE_CONTRAST_INTRO_CLAIM_ID,
    supports_aircraft_window_shape_contrast_intro_from_grounding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VISUAL_EXPLANATION = REPO_ROOT / "video" / "visual_explanation.py"
SUPPLY = {
    "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
    "grounding_source": "faa_comet_lessons_v1",
}


def _load_information_signature_helper():
    """Load only the pure helper, avoiding moviepy/Pillow CI dependencies."""
    source = VISUAL_EXPLANATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    matches = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_information_signature_for_plan"
    ]
    assert len(matches) == 1, "information-signature helper must exist exactly once"
    module = ast.Module(body=[matches[0]], type_ignores=[])
    namespace = {}
    exec(compile(module, str(VISUAL_EXPLANATION), "exec"), namespace)
    return namespace["_information_signature_for_plan"], source


def _question_scene(keyword, visual_goal="둥근 창문 모서리를 강조하며 질문을 제시합니다."):
    return {
        "role": "question",
        "keyword": keyword,
        "visual_goal": visual_goal,
        "_canonical_visual_supply": dict(SUPPLY),
    }


def _grounded_plan(claim, presentation, param_signature):
    return {
        "template": "AIRCRAFT_WINDOW_STRESS_V1",
        "evidence_source": "TRUSTED_GROUNDING",
        "owned_claim_id": claim,
        "presentation_variant": presentation,
        "param_signature": param_signature,
    }


def main():
    information_signature_for_plan, visual_source = _load_information_signature_helper()

    # Exact Run #524 Scene-2 shape: no explicit comparison word in visual_goal,
    # but the existing deterministic query lock carries rounded+corners under
    # trusted aircraft-window grounding. It must route to the neutral two-shape
    # intro rather than reuse Scene 1's single-state still.
    scene2 = _question_scene("aircraft window why rounded corners stage 2")
    eligibility = supports_aircraft_window_shape_contrast_intro_from_grounding(scene2)
    assert eligibility is not None
    assert eligibility["owned_claim_id"] == SHAPE_CONTRAST_INTRO_CLAIM_ID
    assert eligibility["evidence_source"] == "TRUSTED_GROUNDING"

    # The extension stays narrow: generic same-subject question footage without
    # explicit comparison or rounded-corner query terms remains ineligible.
    assert supports_aircraft_window_shape_contrast_intro_from_grounding(
        _question_scene("aircraft window closeup")
    ) is None

    # Claim ownership still wins: the comparison-intro path cannot steal a
    # causal scene even if its keyword contains rounded corners.
    claim_scene = _question_scene("aircraft window why rounded corners stage 2")
    claim_scene["owned_claim_id"] = "rounded_window_stress_distribution"
    assert supports_aircraft_window_shape_contrast_intro_from_grounding(claim_scene) is None

    # Exact #524 S4/S5 setup: same verified physical base, same deterministic
    # template, but distinct grounded claims and presentation variants.
    asset_id = "still-a5aed2169ab7be2b"
    scene4_plan = _grounded_plan(
        "rounded_window_stress_distribution",
        "RIGHT_FLOW_INSPECTION",
        "sig-flow",
    )
    scene5_plan = _grounded_plan(
        "squarish_window_fatigue_rupture",
        "LEFT_FATIGUE_PAYOFF",
        "sig-fatigue",
    )
    scene4_sig = information_signature_for_plan(asset_id, scene4_plan)
    scene5_sig = information_signature_for_plan(asset_id, scene5_plan)
    assert scene4_sig != scene5_sig

    # Exact repeat remains a repeat. We are refining information identity, not
    # disabling the duplicate guard.
    assert scene4_sig == information_signature_for_plan(asset_id, dict(scene4_plan))

    # Anything outside the closed trusted aircraft-window plan keeps the old
    # physical-asset + template identity semantics.
    untrusted_a = dict(scene4_plan, evidence_source="UNVERIFIED")
    untrusted_b = dict(scene5_plan, evidence_source="UNVERIFIED")
    assert information_signature_for_plan(asset_id, untrusted_a) == (
        asset_id,
        "AIRCRAFT_WINDOW_STRESS_V1",
    )
    assert information_signature_for_plan(asset_id, untrusted_a) == information_signature_for_plan(
        asset_id, untrusted_b
    )

    # No explanation budget increase accompanies this recovery. Check the
    # source declaration itself so the test remains dependency-free.
    assert 'os.environ.get("MAX_EXPLANATION_TRANSFORMS_PER_VIDEO", "3")' in visual_source
    assert "# RUN_34675233154_GROUNDED_INFORMATION_IDENTITY_V1" in visual_source

    print("Run 34675233154 window visual progression regression PASS")


if __name__ == "__main__":
    main()
