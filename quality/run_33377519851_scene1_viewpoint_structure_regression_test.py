"""Run 33377519851 Scene-1 HUMAN-QA viewpoint/structure regression.

This test uses deterministic structured Vision payload fixtures only. It makes no
image, Vision, LLM, network, or production call.
"""
from pathlib import Path
import tempfile

from video import hook_visual_dominance as dominance
from video import still_image_fallback as still


SCENE = {
    "scene_id": 1,
    "role": "phenomenon",
    "text": "비행기 엔진 뒤쪽은 톱니처럼 생겼습니다.",
    "keyword": "aircraft jet engine nacelle nozzle chevron serrated",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron"],
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
        "grounding_source": "run-33377519851-fixture",
    },
}

GENERIC = {
    "scene_id": 9,
    "role": "phenomenon",
    "text": "비행기 창문은 둥근 모서리입니다.",
    "keyword": "aircraft window rounded corner",
    "_canonical_visual_supply": {
        "canonical_subject": "aircraft passenger window",
        "identity_confidence": 0.98,
        "canonical_terms": ["aircraft", "passenger", "window"],
        "visual_discriminators": ["window", "rounded"],
        "grounding_source": "generic-fixture",
    },
}


def subject_result():
    return {
        "pass": True,
        "schema_parser_consistency": True,
        "required_subject_groups": ["aircraft", "engine", "chevron"],
        "raw_visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "effective_subject_groups": {"aircraft": True, "engine": True, "chevron": True},
        "visible_components": ["jet engine", "chevron", "engine"],
        "parent_domain_satisfied": ["aircraft"],
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "reason": "rear nozzle",  # diagnostics only; never authoritative
    }


def payload(*, rear=False, owned=False, front=False, mobile=False, reason=""):
    return {
        "visible_components": ["jet engine", "chevron", "engine"],
        "visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "viewpoint_structure_evidence": {
            "rear_nozzle_or_trailing_edge_identifiable": rear,
            "chevron_attached_to_rear_nozzle_or_trailing_edge": owned,
            "front_intake_or_fan_side_dominant": front,
            "mobile_structure_identifiable": mobile,
        },
        "reason": reason,
    }


def classify(scene, structured_payload):
    return dominance._still_viewpoint_structure_apply(
        subject_result(), structured_payload, scene
    )


# Trusted canonical authority is deterministic and exactly preserves #261's
# generation contract rather than inventing a topic-specific rule.
requirement = dominance._still_viewpoint_structure_requirement(SCENE)
assert requirement["required"] is True
assert requirement["required_viewpoint"] == "rear or rear-quarter close-up of the trailing edge"
assert still._canonical_still_contract(SCENE)["required_viewpoint"] == requirement["required_viewpoint"]
assert "required viewpoint from trusted physical evidence: rear or rear-quarter close-up" in still._prompt(SCENE).lower()

# 1. Run 33377519851 class: front-intake/fan-side dominant + chevron-like rim.
front = classify(SCENE, payload(rear=False, owned=False, front=True, mobile=True))
assert front["viewpoint_structure_pass"] is False

# 2. Generic turbine/fan close-up cannot prove the required rear structure.
turbine = classify(SCENE, payload(rear=False, owned=False, front=True, mobile=True))
assert turbine["viewpoint_structure_pass"] is False

# 3. Positive fixture: rear nozzle + large clearly-owned trailing-edge chevrons.
good = classify(SCENE, payload(rear=True, owned=True, front=False, mobile=True))
assert good["viewpoint_structure_pass"] is True

# 4. Rear nozzle with no chevron ownership is insufficient.
rear_no_chevron = classify(SCENE, payload(rear=True, owned=False, front=False, mobile=True))
assert rear_no_chevron["viewpoint_structure_pass"] is False

# 5. Chevron visible but relation to rear/nozzle trailing edge unclear is insufficient.
unclear_relation = classify(SCENE, payload(rear=True, owned=False, front=False, mobile=True))
assert unclear_relation["viewpoint_structure_pass"] is False

# 6. Free-text reason can never substitute for structured viewpoint evidence.
reason_only = classify(
    SCENE,
    payload(rear=False, owned=False, front=False, mobile=False, reason="clear rear nozzle chevrons"),
)
assert reason_only["viewpoint_structure_pass"] is False

# 7. Explicit structured rear/nozzle false stays fail-closed even if reason claims rear.
structured_false = classify(
    SCENE,
    payload(rear=False, owned=True, front=False, mobile=True, reason="rear nozzle"),
)
assert structured_false["viewpoint_structure_pass"] is False

# Wide/tiny subject is also fail-closed through mobile_structure_identifiable.
wide_tiny = classify(SCENE, payload(rear=True, owned=True, front=False, mobile=False))
assert wide_tiny["viewpoint_structure_pass"] is False

# 8. No trusted rear/nozzle+edge basis => preserve established general verifier behavior.
assert dominance._still_viewpoint_structure_requirement(GENERIC) == {}
generic_result = dominance._still_viewpoint_structure_apply(subject_result(), {}, GENERIC)
assert generic_result["viewpoint_structure_required"] is False
assert generic_result["viewpoint_structure_pass"] is True
assert still._canonical_still_contract(GENERIC)["required_viewpoint"] == ""

# Scene 3 explanatory roles do not activate this Scene-1 physical viewpoint gate.
scene3 = dict(SCENE, scene_id=3, role="mechanism_input", causal_role="mechanism_input")
assert dominance._still_viewpoint_structure_requirement(scene3) == {}

# 9. Exact production subject proof (engine=true + chevron=true + inferred aircraft=true)
# does NOT replace rear/nozzle proof at the final still-verifier boundary.
previous = still._run33377519851_previous_verify_motion_clip
try:
    still._run33377519851_previous_verify_motion_clip = lambda scene, output: (
        True,
        classify(scene, payload(rear=False, owned=False, front=True, mobile=True)),
    )
    verified, bad_evidence = still._verify_motion_clip(SCENE, Path("unused.mp4"))
    assert verified is False
    assert bad_evidence["effective_subject_groups"] == {
        "aircraft": True, "engine": True, "chevron": True
    }
finally:
    still._run33377519851_previous_verify_motion_clip = previous

# Positive structured proof is accepted by the same boundary.
try:
    still._run33377519851_previous_verify_motion_clip = lambda scene, output: (
        True,
        classify(scene, payload(rear=True, owned=True, front=False, mobile=True)),
    )
    verified, good_evidence = still._verify_motion_clip(SCENE, Path("unused.mp4"))
    assert verified is True
finally:
    still._run33377519851_previous_verify_motion_clip = previous

# 10. #261 prompt composition and still budget remain unchanged.
assert still.STILL_IMAGE_MAX_PER_VIDEO == 2
source = (Path(__file__).resolve().parents[1] / "video/still_image_fallback.py").read_text(encoding="utf-8")
assert '"n": 1' in source

# 11/12. A BAD Scene-1 proof cannot enter #268's verified subject cache; a GOOD
# proof can. Parent-domain raw/effective separation remains intact.
still.reset_still_image_budget()
with tempfile.TemporaryDirectory() as tmp:
    image = Path(tmp) / "subject.png"
    image.write_bytes(b"fixture")
    bad_cached = still._cache_verified_subject_proof(
        SCENE,
        image_path=image,
        source_id="bad-viewpoint",
        evidence=bad_evidence,
        verified=False,
    )
    assert bad_cached is False
    assert not still._VERIFIED_SUBJECT_PROOF_CACHE

    good_evidence["raw_visible_subject_groups"] = {
        "aircraft": False, "engine": True, "chevron": True
    }
    good_evidence["effective_subject_groups"] = {
        "aircraft": True, "engine": True, "chevron": True
    }
    good_evidence["required_subject_groups"] = ["aircraft", "engine", "chevron"]
    good_evidence["schema_parser_consistency"] = True
    good_evidence["pass"] = True
    good_evidence["obvious_generation_artifact"] = False
    good_evidence["factual_visual_contradiction"] = False
    good_cached = still._cache_verified_subject_proof(
        SCENE,
        image_path=image,
        source_id="good-viewpoint",
        evidence=good_evidence,
        verified=True,
    )
    assert good_cached is True
    assert still._VERIFIED_SUBJECT_PROOF_CACHE

print("RUN 33377519851 SCENE 1 VIEWPOINT/STRUCTURE REGRESSION: PASS")
