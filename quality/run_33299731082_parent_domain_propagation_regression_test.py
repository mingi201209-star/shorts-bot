"""Run 33299731082 trusted parent-domain propagation regression.

No image, Vision, network, or production call is made. This fixture isolates the
still-verifier boundary after #259 structured parsing and verifies that the
existing #256 trusted parent-domain branch runs before final consistency.
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
    "text": "비행기 엔진 뒤는 톱니처럼 생겼습니다.",
    "visual_goal": "톱니 모양의 엔진 배기구",
    "keyword": "aircraft jet engine nacelle nozzle chevron serrated",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron"],
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
        "grounding_source": "trusted-live-fixture",
    },
}

LIVE = {
    "pass": True,
    "required_subject_groups": ["aircraft", "engine", "chevron"],
    "visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
    "visible_components": ["engine", "chevron"],
    "schema_parser_consistency": False,
    "evidence_inconsistencies": [
        "structured_group_component_disagree:aircraft:group=true:component=false"
    ],
    "reason": "The chevron structure of the jet engine is clearly visible, large, and dominant in the frame.",
    "obvious_generation_artifact": False,
    "factual_visual_contradiction": False,
}


def _fixture_downloader_module():
    """Supply the exact anchor contract already established upstream by #253-#255.

    Their own regressions validate query extraction/fallback behavior. This test
    starts at the documented verifier handoff so failures identify only the
    parent-domain propagation boundary.
    """
    module = ModuleType("video.video_downloader")
    aliases = {
        "aircraft": {"aircraft", "airplane", "plane", "aviation", "jet"},
        "engine": {"engine", "turbofan", "nacelle", "nozzle"},
        "chevron": {"chevron", "chevrons", "serrated"},
    }
    module._anchor_aliases = lambda anchor: aliases.get(anchor, {anchor})
    module.extract_query_anchors = lambda query: ["aircraft", "engine", "chevron"]
    return module


def verify(scene, result):
    original_eval = dominance.evaluate_hook_subject_dominance
    original_module = sys.modules.get("video.video_downloader")
    dominance.evaluate_hook_subject_dominance = lambda candidate, supplied_scene: deepcopy(result)
    sys.modules["video.video_downloader"] = _fixture_downloader_module()
    try:
        return still._verify_motion_clip(deepcopy(scene), "fixture.mp4")
    finally:
        dominance.evaluate_hook_subject_dominance = original_eval
        if original_module is None:
            sys.modules.pop("video.video_downloader", None)
        else:
            sys.modules["video.video_downloader"] = original_module


# A. Exact Run 33299731082 positive fixture.
ok, result = verify(SCENE, LIVE)
assert ok is True
assert result["raw_visible_subject_groups"] == {
    "aircraft": False, "engine": True, "chevron": True
}
assert result["parent_domain_satisfied"] == ["aircraft"]
assert result["effective_subject_groups"] == {
    "aircraft": True, "engine": True, "chevron": True
}
assert result["missing_subject_groups"] == []
assert result["schema_parser_consistency"] is True
assert result["evidence_inconsistencies"] == []
assert result["resolved_evidence_inconsistencies"] == [
    "structured_group_component_disagree:aircraft:group=true:component=false"
]

# B. Engine without structured chevron remains rejected.
case = deepcopy(LIVE)
case["visible_subject_groups"]["chevron"] = False
case["visible_components"] = ["engine"]
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
assert verify(SCENE, case)[0] is False

# C. Engine+wing cannot substitute for chevron.
case = deepcopy(LIVE)
case["visible_subject_groups"]["chevron"] = False
case["visible_components"] = ["engine", "wing"]
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
assert verify(SCENE, case)[0] is False

# D. Vision pass=False remains an immediate reject even with engine+chevron.
case = deepcopy(LIVE)
case["pass"] = False
assert verify(SCENE, case)[0] is False

# E. No trusted canonical profile means no parent-domain inference.
scene = deepcopy(SCENE)
scene.pop("_canonical_visual_supply")
case = deepcopy(LIVE)
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
assert verify(scene, case)[0] is False

# F. Reason-only chevron cannot rescue structured chevron=False.
case = deepcopy(LIVE)
case["visible_subject_groups"]["chevron"] = False
case["visible_components"] = ["engine"]
case["schema_parser_consistency"] = False
case["evidence_inconsistencies"] = ["reason_claims_missing_structured_group:chevron"]
case["reason"] = "The chevron is clearly visible."
assert verify(SCENE, case)[0] is False

# G. #259 approved serrated-nozzle alias becomes structured chevron evidence;
# reason text is not needed for this canonicalization.
payload = {
    "visible_components": ["engine", "serrated nozzle"],
    "visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
    "reason": "",
}
normalized = dominance._still_vision_apply_structured_evidence(
    {}, payload, ["aircraft", "engine", "chevron"]
)
assert normalized["visible_subject_groups"]["chevron"] is True
assert "chevron" in normalized["visible_components"]

# H. Generic engine canonical identity cannot infer the aircraft parent domain.
scene = deepcopy(SCENE)
scene["_canonical_visual_supply"]["canonical_subject"] = "generic engine"
case = deepcopy(LIVE)
case["visible_subject_groups"]["chevron"] = False
case["visible_components"] = ["engine"]
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
assert verify(scene, case)[0] is False

# Any unrelated structured inconsistency remains fail-closed.
case = deepcopy(LIVE)
case["evidence_inconsistencies"].append(
    "structured_group_component_disagree:chevron:group=true:component=false"
)
assert verify(SCENE, case)[0] is False

# I. #261 generation subject-proof contract is not modified by this fix.
parent_source = (ROOT / "ci_still_parent_domain_propagation_hotfix.py").read_text(encoding="utf-8")
assert "required_viewpoint" not in parent_source
assert "subject_proof_priority" not in parent_source
assert "final_prompt_signature" not in parent_source

# No generation budget/API/retry contract is modified by this regression fix.
assert "STILL_IMAGE_MAX_PER_VIDEO" not in parent_source
assert "requests." not in parent_source
assert "OPENAI" not in parent_source
assert "raw_visible_subject_groups" in parent_source
assert "effective_subject_groups" in parent_source

print("RUN 33299731082 PARENT DOMAIN PROPAGATION REGRESSION: PASS")
