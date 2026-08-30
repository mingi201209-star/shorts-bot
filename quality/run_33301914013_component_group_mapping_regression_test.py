"""Run 33301914013 structured component -> canonical subject-group regression.

No image generation, Vision, network, or production call is made. The fixture
starts from the exact structured Vision payload observed in Run 33301914013 and
verifies the #259 mapper before the unchanged #262 parent-domain policy.
"""
from copy import deepcopy
from importlib import reload
from pathlib import Path
from types import ModuleType
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_still_image_verifier_contract_hotfix import main as install_verifier  # noqa: E402
from ci_still_vision_evidence_groups_hotfix import main as install_groups  # noqa: E402
from ci_still_vision_evidence_trace_hotfix import main as install_trace  # noqa: E402

install_verifier()
install_groups()
install_trace()

from video import hook_visual_dominance as dominance  # noqa: E402
from video import still_image_fallback as still  # noqa: E402
reload(dominance)
reload(still)

SCENE = {
    "scene_id": 1,
    "role": "phenomenon",
    "text": "비행기 엔진 뒤쪽은 톱니처럼 생겨있습니다.",
    "visual_goal": "톱니 모양의 엔진 뒤",
    "keyword": "aircraft jet engine nacelle nozzle chevron serrated",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron"],
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
        "grounding_source": "trusted-live-fixture",
    },
}


def _fixture_downloader_module():
    module = ModuleType("video.video_downloader")
    aliases = {
        "aircraft": {"aircraft", "airplane", "plane", "aviation", "jet"},
        "engine": {"engine", "turbofan", "nacelle", "nozzle"},
        "chevron": {"chevron", "chevrons", "serrated"},
    }
    module._anchor_aliases = lambda anchor: aliases.get(anchor, {anchor})
    module.extract_query_anchors = lambda query: ["aircraft", "engine", "chevron"]
    return module


def normalize(payload):
    return dominance._still_vision_apply_structured_evidence(
        {"pass": bool(payload.get("pass", True))},
        deepcopy(payload),
        ["aircraft", "engine", "chevron"],
    )


def verify_normalized(result, scene=None):
    scene = deepcopy(scene or SCENE)
    original_eval = dominance.evaluate_hook_subject_dominance
    original_module = sys.modules.get("video.video_downloader")
    dominance.evaluate_hook_subject_dominance = lambda candidate, supplied_scene: deepcopy(result)
    sys.modules["video.video_downloader"] = _fixture_downloader_module()
    try:
        return still._verify_motion_clip(scene, "fixture.mp4")
    finally:
        dominance.evaluate_hook_subject_dominance = original_eval
        if original_module is None:
            sys.modules.pop("video.video_downloader", None)
        else:
            sys.modules["video.video_downloader"] = original_module


# A. Exact Run 33301914013 structured payload.
payload = {
    "pass": True,
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["jet engine", "nacelle", "chevron"],
    "reason": "The chevron-shaped edge of the jet engine nozzle is clearly visible and dominant in the frames.",
}
result = normalize(payload)
assert result["model_visible_subject_groups"] == {
    "aircraft": False, "engine": False, "chevron": True
}
assert result["component_derived_subject_groups"] == {
    "aircraft": False, "engine": True, "chevron": True
}
assert result["effective_raw_subject_groups"] == {
    "aircraft": False, "engine": True, "chevron": True
}
assert result["visible_subject_groups"] == result["effective_raw_subject_groups"]
assert result["schema_parser_consistency"] is True
assert result["evidence_inconsistencies"] == []
assert result["resolved_evidence_inconsistencies"] == [
    "structured_group_component_disagree:engine:group=false:component=true"
]
ok, final = verify_normalized(result)
assert ok is True
assert final["parent_domain_satisfied"] == ["aircraft"]
assert final["effective_subject_groups"] == {
    "aircraft": True, "engine": True, "chevron": True
}
assert final["missing_subject_groups"] == []

# B. Canonical component label engine is sufficient structured engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["engine", "chevron"],
    "reason": "",
})
assert case["component_derived_subject_groups"]["engine"] is True
assert case["effective_raw_subject_groups"]["engine"] is True

# C. Multi-token approved alias jet engine is sufficient structured engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["jet engine", "chevron"],
    "reason": "",
})
assert case["component_derived_subject_groups"]["engine"] is True

# D. Nacelle + fan blades + chevron does not synthesize engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["fan blades", "nacelle", "chevron"],
    "reason": "",
})
assert case["component_derived_subject_groups"]["engine"] is False
assert case["effective_raw_subject_groups"]["engine"] is False
assert verify_normalized(case)[0] is False

# E. Wing + chevron cannot substitute for engine.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["wing", "chevron"],
    "reason": "",
})
assert case["effective_raw_subject_groups"]["engine"] is False
assert verify_normalized(case)[0] is False

# F. Free-text reason is not authority.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["chevron"],
    "reason": "A jet engine is clearly visible.",
})
assert case["effective_raw_subject_groups"]["engine"] is False
assert verify_normalized(case)[0] is False

# G. pass=False stays fail-closed even with approved engine + chevron evidence.
case = normalize({
    "pass": False,
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["jet engine", "chevron"],
    "reason": "",
})
case["pass"] = False
assert verify_normalized(case)[0] is False

# H. Trusted canonical profile is still required for aircraft parent inference.
scene = deepcopy(SCENE)
scene.pop("_canonical_visual_supply")
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["jet engine", "chevron"],
    "reason": "",
})
assert verify_normalized(case, scene)[0] is False

# I. Structured chevron=False + jet engine only remains rejected. Engine mapping
# must never manufacture chevron evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": False},
    "visible_components": ["jet engine"],
    "reason": "The chevron is visible.",
})
assert case["effective_raw_subject_groups"]["engine"] is True
assert case["effective_raw_subject_groups"]["chevron"] is False
assert verify_normalized(case)[0] is False

# J. #261 prompt contract remains outside this mapper patch.
source = (ROOT / "ci_still_vision_evidence_groups_hotfix.py").read_text(encoding="utf-8")
assert "required_viewpoint" not in source
assert "subject_proof_priority" not in source
assert "final_prompt_signature" not in source

# Budget/authority guards: no extra calls, generations, retries, or reason-based acceptance.
assert "STILL_IMAGE_MAX_PER_VIDEO" not in source
assert "AI_MAX_GENERATIONS_PER_VIDEO" not in source
assert "V3_MAX_API_CALLS" not in source
assert "reason is diagnostics only" in source
assert '"jet engine"' in source
assert '"nacelle", "nozzle"' not in source.split('"engine": {', 1)[1].split('}', 1)[0]

print("RUN 33301914013 COMPONENT GROUP MAPPING REGRESSION: PASS")
