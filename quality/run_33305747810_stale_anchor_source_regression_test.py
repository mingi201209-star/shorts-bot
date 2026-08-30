"""Run 33305747810 stale parent-domain anchor-source regression.

No image generation, Vision, network, or production call is made. This fixture
isolates the final still-verifier composition and proves that an already
established authoritative subject contract cannot be weakened by a stale Scene
keyword while preserving the legacy fallback and all fail-closed guards.
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

STALE_KEYWORD = "aircraft wing mechanism stage 1"
CANONICAL_QUERY = "aircraft jet engine nacelle nozzle chevron serrated"

SCENE = {
    "scene_id": 1,
    "role": "phenomenon",
    "text": "비행기 엔진 뒤는 톱니처럼 생겼습니다.",
    "visual_goal": "톱니 모양의 엔진 구조",
    "keyword": STALE_KEYWORD,
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
    "visible_components": ["jet engine", "chevron", "engine"],
    "schema_parser_consistency": False,
    "evidence_inconsistencies": [
        "structured_group_component_disagree:aircraft:group=true:component=false"
    ],
    "reason": "The chevron structure of the jet engine is clearly visible and dominant in the frames.",
    "obvious_generation_artifact": False,
    "factual_visual_contradiction": False,
}


def _anchors(query):
    words = set(str(query or "").lower().replace("-", " ").replace("/", " ").split())
    found = []
    if words & {"aircraft", "airplane", "aviation", "jet"}:
        found.append("aircraft")
    if words & {"engine", "turbofan", "nacelle", "nozzle"}:
        found.append("engine")
    if words & {"chevron", "chevrons", "serrated"}:
        found.append("chevron")
    if "wing" in words:
        if "aircraft" not in found:
            found.insert(0, "aircraft")
        found.append("wing")
    return list(dict.fromkeys(found))[:3]


def _fixture_downloader_module(contract=None):
    module = ModuleType("video.video_downloader")
    aliases = {
        "aircraft": {"aircraft", "airplane", "plane", "aviation", "jet"},
        "engine": {"engine", "jet engine", "turbofan", "nacelle", "nozzle"},
        "chevron": {"chevron", "chevrons", "serrated", "serrated nozzle"},
        "wing": {"wing", "wings"},
    }
    module._anchor_aliases = lambda anchor: aliases.get(anchor, {anchor})
    module.extract_query_anchors = _anchors
    module.get_current_visual_subject_anchor_contract = lambda: deepcopy(contract or {})
    return module


def verify(scene, result, *, contract=None):
    original_eval = dominance.evaluate_hook_subject_dominance
    original_module = sys.modules.get("video.video_downloader")
    dominance.evaluate_hook_subject_dominance = lambda candidate, supplied_scene: deepcopy(result)
    sys.modules["video.video_downloader"] = _fixture_downloader_module(contract)
    try:
        return still._verify_motion_clip(deepcopy(scene), "fixture.mp4")
    finally:
        dominance.evaluate_hook_subject_dominance = original_eval
        if original_module is None:
            sys.modules.pop("video.video_downloader", None)
        else:
            sys.modules["video.video_downloader"] = original_module


# A. Exact Run 33305747810 counterexample.
ok, result = verify(SCENE, LIVE)
assert ok is True
assert result["parent_domain_anchor_source"] == "required_subject_groups"
assert result["raw_visible_subject_groups"] == {
    "aircraft": False, "engine": True, "chevron": True
}
assert result["parent_domain_satisfied"] == ["aircraft"]
assert result["effective_subject_groups"] == {
    "aircraft": True, "engine": True, "chevron": True
}
assert result["missing_subject_groups"] == []
assert result["schema_parser_consistency"] is True

# B. Same stale keyword, but structured chevron=False remains rejected.
case = deepcopy(LIVE)
case["visible_subject_groups"]["chevron"] = False
case["visible_components"] = ["jet engine", "engine"]
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
assert verify(SCENE, case)[0] is False

# C. Missing chevron requirement must not activate parent inference.
case = deepcopy(LIVE)
case["required_subject_groups"] = ["aircraft", "engine"]
case["visible_subject_groups"] = {"aircraft": False, "engine": True}
case["visible_components"] = ["jet engine", "engine"]
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
ok, result = verify(SCENE, case)
assert ok is False
assert result.get("parent_domain_satisfied") in (None, [])

# D. Trusted canonical identity remains mandatory.
scene = deepcopy(SCENE)
scene.pop("_canonical_visual_supply")
case = deepcopy(LIVE)
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
assert verify(scene, case)[0] is False

# E. Vision pass=False remains fail-closed.
case = deepcopy(LIVE)
case["pass"] = False
assert verify(SCENE, case)[0] is False

# F. Legacy scenes without authoritative data retain keyword parsing.
legacy_scene = deepcopy(SCENE)
legacy_scene["keyword"] = "aircraft wing"
legacy_scene.pop("_canonical_visual_supply")
legacy = {
    "pass": True,
    "required_subject_groups": [],
    "visible_subject_groups": {},
    "visible_components": ["aircraft", "wing"],
    "schema_parser_consistency": True,
    "evidence_inconsistencies": [],
    "reason": "aircraft wing visible",
    "obvious_generation_artifact": False,
    "factual_visual_contradiction": False,
}
ok, result = verify(legacy_scene, legacy)
assert ok is True
assert result["parent_domain_anchor_source"] == "legacy_scene_keyword"

# G. Required groups override conflicting stale keyword.
ok, result = verify(SCENE, LIVE)
assert ok is True
assert _anchors(STALE_KEYWORD) == ["aircraft", "wing"]
assert result["parent_domain_anchor_source"] == "required_subject_groups"

# Priority 2: a Scene-matching visual subject contract is authoritative.
case = deepcopy(LIVE)
case["required_subject_groups"] = []
case["schema_parser_consistency"] = True
case["evidence_inconsistencies"] = []
contract = {
    "required_anchors": ["aircraft", "engine", "chevron"],
    "original_query": STALE_KEYWORD,
    "effective_query": "aircraft engine chevron wing mechanism stage 1",
}
ok, result = verify(SCENE, case, contract=contract)
assert ok is True
assert result["parent_domain_anchor_source"] == "visual_subject_contract"

# Priority 3: a Scene-matching authoritative effective query is next.
contract = {
    "required_anchors": [],
    "original_query": STALE_KEYWORD,
    "effective_query": CANONICAL_QUERY,
}
ok, result = verify(SCENE, case, contract=contract)
assert ok is True
assert result["parent_domain_anchor_source"] == "effective_query"

# A stale contract belonging to another Scene must not override this Scene.
stale_contract = {
    "required_anchors": ["engine"],
    "original_query": "jet engine flow interface",
    "effective_query": "jet engine flow interface",
}
ok, result = verify(SCENE, case, contract=stale_contract)
assert result["parent_domain_anchor_source"] == "legacy_scene_keyword"

# H. #263 component mapping remains intact.
payload = {
    "visible_components": ["jet engine", "chevron"],
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "reason": "",
}
normalized = dominance._still_vision_apply_structured_evidence(
    {}, payload, ["aircraft", "engine", "chevron"]
)
assert normalized["visible_subject_groups"]["engine"] is True
assert normalized["component_derived_subject_groups"]["engine"] is True
assert normalized["visible_subject_groups"]["chevron"] is True

# I. #259 remains structured-authority; reason-only chevron fails.
case = deepcopy(LIVE)
case["visible_subject_groups"]["chevron"] = False
case["visible_components"] = ["jet engine", "engine"]
case["schema_parser_consistency"] = False
case["evidence_inconsistencies"] = ["reason_claims_missing_structured_group:chevron"]
case["reason"] = "The chevron is clearly visible."
assert verify(SCENE, case)[0] is False

# J/K/L. No adjacent contracts/budgets touched.
source = (ROOT / "ci_still_parent_domain_propagation_hotfix.py").read_text(encoding="utf-8")
assert "required_viewpoint" not in source
assert "subject_proof_priority" not in source
assert "final_prompt_signature" not in source
assert "FLOW_INTERFACE" not in source
assert "CHEVRON_FLOW_MIXING" not in source
assert "STILL_IMAGE_MAX_PER_VIDEO" not in source
assert "OPENAI_KEY" not in source
assert "requests." not in source
assert "parent_domain_anchor_source" in source
assert "required_subject_groups" in source
assert "legacy_scene_keyword" in source

print("RUN 33305747810 STALE ANCHOR SOURCE REGRESSION: PASS")
