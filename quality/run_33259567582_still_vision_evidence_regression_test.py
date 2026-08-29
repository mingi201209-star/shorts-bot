"""Run 33259567582 Scene 2 structured Vision evidence regression.

No network/model call is performed. The fixture reproduces the exact state
boundary that failed in production and preserves the strict #256 parent-domain
contract without trusting free-text reason content.
"""
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_still_image_verifier_contract_hotfix as verifier_hotfix
import ci_still_vision_evidence_groups_hotfix as evidence_hotfix

verifier_hotfix.main()
evidence_hotfix.main()

from video import hook_visual_dominance as dominance  # noqa: E402
from video import still_image_fallback as still  # noqa: E402


SCENE = {
    "scene_id": 2,
    "role": "question",
    "text": "그런데 왜 비행기 엔진 뒤는 톱니 모양으로 설계되었을까요?",
    "visual_goal": "톱니 모양의 엔진 뒷면",
    "keyword": "aircraft engine chevron wing mechanism stage 2",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
        "grounding_source": "trusted-fixture",
    },
}

REQUIRED = ["aircraft", "engine", "chevron"]


def payload(*, passed=True, components=None, groups=None, reason=""):
    return {
        "target_subject": "jet engine rear chevron",
        "subject_dominance": 9.0,
        "subject_visibility": 9.0,
        "action_match": 10.0,
        "competing_subject_risk": 1.0,
        "vertical_crop_subject_visible": True,
        "visible_components": list(components or []),
        "visible_subject_groups": dict(groups or {}),
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "reason": reason,
        "_fixture_pass": bool(passed),
    }


def structured_result(raw):
    result = dominance.normalize_dominance_result(raw, action_required=False)
    result = dominance._still_vision_apply_structured_evidence(result, raw, REQUIRED)
    result["pass"] = bool(raw.get("_fixture_pass"))
    return result


fake_downloader = types.ModuleType("video.video_downloader")


def extract_query_anchors(query):
    words = set(str(query or "").lower().replace("/", " ").split())
    return [anchor for anchor in ("aircraft", "engine", "chevron") if anchor in words]


def _anchor_aliases(anchor):
    aliases = {
        "aircraft": {"aircraft", "airplane", "plane", "jet"},
        "engine": {"engine", "nacelle"},
        "chevron": {"chevron", "chevrons", "serrated", "sawtooth"},
    }
    return aliases.get(anchor, {anchor})


fake_downloader.extract_query_anchors = extract_query_anchors
fake_downloader._anchor_aliases = _anchor_aliases
original_downloader_module = sys.modules.get("video.video_downloader")
sys.modules["video.video_downloader"] = fake_downloader
original_eval = dominance.evaluate_hook_subject_dominance


def verify(raw, scene=SCENE):
    evidence = structured_result(raw)
    dominance.evaluate_hook_subject_dominance = lambda candidate, current_scene: dict(evidence)
    return still._verify_motion_clip(
        scene,
        ROOT / "not-read-because-vision-is-mocked.mp4",
    )


try:
    # A. Positive #256 branch: structured engine+chevron evidence plus trusted
    # canonical parent-domain identity may satisfy aircraft without weakening 3/3.
    ok, evidence = verify(payload(
        components=["engine", "chevron"],
        groups={"aircraft": False, "engine": True, "chevron": True},
        reason="Engine and chevron are clearly visible.",
    ))
    assert ok is True, evidence
    assert evidence.get("parent_domain_satisfied") == ["aircraft"], evidence
    assert evidence.get("visible_subject_groups", {}).get("chevron") is True

    # B. Exact Run 33259567582 contradiction. Reason may say chevron, but
    # structured engine+wing with chevron=false must remain fail-closed.
    ok, evidence = verify(payload(
        components=["engine", "wing"],
        groups={"aircraft": False, "engine": True, "chevron": False},
        reason="The engine chevron design is clearly visible and dominant in the frames.",
    ))
    assert ok is False, evidence
    assert evidence.get("visible_subject_groups", {}).get("chevron") is False
    assert evidence.get("schema_parser_consistency") is False, evidence
    assert any(
        item == "reason_claims_missing_structured_group:chevron"
        for item in evidence.get("evidence_inconsistencies", [])
    ), evidence

    # C. Vision pass=False remains terminal even with complete subassembly proof.
    ok, evidence = verify(payload(
        passed=False,
        components=["engine", "chevron"],
        groups={"aircraft": False, "engine": True, "chevron": True},
        reason="Engine and chevron are visible.",
    ))
    assert ok is False, evidence

    # D. Engine-only cannot satisfy chevron.
    ok, evidence = verify(payload(
        components=["engine"],
        groups={"aircraft": False, "engine": True, "chevron": False},
        reason="Engine is visible.",
    ))
    assert ok is False, evidence

    # E. engine+wing remains 2/3 and cannot become chevron through aliasing.
    ok, evidence = verify(payload(
        components=["engine", "wing"],
        groups={"aircraft": False, "engine": True, "chevron": False},
        reason="Engine and wing are visible.",
    ))
    assert ok is False, evidence
    assert "chevron" not in evidence.get("visible_components", []), evidence

    # F. Approved STRUCTURED aliases normalize to the chevron group. Neither
    # reason text nor generic parts are involved.
    for alias in ("serrated nozzle", "sawtooth trailing edge"):
        ok, evidence = verify(payload(
            components=["engine", alias],
            groups={"aircraft": False, "engine": True, "chevron": True},
            reason=f"Engine and {alias} are visible.",
        ))
        assert ok is True, (alias, evidence)
        assert "chevron" in evidence.get("visible_components", []), evidence

    # G. Reason-only chevron evidence is never promoted into structured proof.
    ok, evidence = verify(payload(
        components=["engine"],
        groups={},
        reason="A chevron is clearly visible.",
    ))
    assert ok is False, evidence
    assert evidence.get("visible_subject_groups", {}).get("chevron") is False

    # H. #256 parent-domain satisfaction requires trusted canonical identity.
    untrusted = dict(SCENE)
    untrusted.pop("_canonical_visual_supply", None)
    ok, evidence = verify(payload(
        components=["engine", "chevron"],
        groups={"aircraft": False, "engine": True, "chevron": True},
        reason="Engine and chevron are visible.",
    ), scene=untrusted)
    assert ok is False, evidence

    # Structured contradiction between the boolean map and component list is
    # also fail-closed. This protects the new schema itself.
    ok, evidence = verify(payload(
        components=["engine", "wing"],
        groups={"aircraft": False, "engine": True, "chevron": True},
        reason="Chevron is visible.",
    ))
    assert ok is False, evidence
    assert evidence.get("schema_parser_consistency") is False
finally:
    dominance.evaluate_hook_subject_dominance = original_eval
    if original_downloader_module is None:
        sys.modules.pop("video.video_downloader", None)
    else:
        sys.modules["video.video_downloader"] = original_downloader_module

print("RUN 33259567582 STILL VISION STRUCTURED EVIDENCE REGRESSION: PASS")
