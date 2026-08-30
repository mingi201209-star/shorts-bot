"""Run 33301914013 structured component -> canonical subject-group regression.

No image generation, Vision, network, production, or parent-domain policy call is
made. This fixture isolates the first canonical mapping loss observed in Run
33301914013. The unchanged #262 parent-domain behavior is verified separately by
its existing exact regression.
"""
from copy import deepcopy
from importlib import reload
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_still_image_verifier_contract_hotfix import main as install_verifier  # noqa: E402
from ci_still_vision_evidence_groups_hotfix import main as install_groups  # noqa: E402

install_verifier()
install_groups()

from video import hook_visual_dominance as dominance  # noqa: E402
reload(dominance)


def normalize(payload):
    return dominance._still_vision_apply_structured_evidence(
        {"pass": bool(payload.get("pass", True))},
        deepcopy(payload),
        ["aircraft", "engine", "chevron"],
    )


# A. Exact Run 33301914013 structured payload at the first-loss boundary.
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

# The mapped output is exactly the precondition consumed by unchanged #262:
# aircraft=False, engine=True, chevron=True. Its existing regression verifies
# trusted canonical parent-domain propagation from that state.
assert result["effective_raw_subject_groups"] == {
    "aircraft": False, "engine": True, "chevron": True
}

# B. Canonical component label engine is approved structured engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["engine", "chevron"],
    "reason": "",
})
assert case["component_derived_subject_groups"]["engine"] is True
assert case["effective_raw_subject_groups"]["engine"] is True

# C. Multi-token approved alias jet engine is approved structured engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["jet engine", "chevron"],
    "reason": "",
})
assert case["component_derived_subject_groups"]["engine"] is True
assert case["effective_raw_subject_groups"]["engine"] is True

# D. Fan blades + nacelle + chevron do not synthesize engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["fan blades", "nacelle", "chevron"],
    "reason": "",
})
assert case["component_derived_subject_groups"]["engine"] is False
assert case["effective_raw_subject_groups"]["engine"] is False

# E. Wing + chevron cannot substitute for engine.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["wing", "chevron"],
    "reason": "",
})
assert case["effective_raw_subject_groups"]["engine"] is False

# F. Free-text reason is diagnostics only and cannot manufacture engine evidence.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["chevron"],
    "reason": "A jet engine is clearly visible.",
})
assert case["component_derived_subject_groups"]["engine"] is False
assert case["effective_raw_subject_groups"]["engine"] is False

# G. pass=False is preserved; mapping does not turn a failed Vision result into pass.
case = normalize({
    "pass": False,
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": True},
    "visible_components": ["jet engine", "chevron"],
    "reason": "",
})
assert case["pass"] is False

# H. This mapper does not contain trusted-canonical parent-domain policy logic.
# Keep the guard scoped to policy signals rather than diagnostic field names.
source = (ROOT / "ci_still_vision_evidence_groups_hotfix.py").read_text(encoding="utf-8")
assert "trusted_jet_engine_parent" not in source
assert "canonical_confidence >= 0.80" not in source

# I. Structured chevron=False + jet engine only remains chevron-negative.
case = normalize({
    "visible_subject_groups": {"aircraft": False, "engine": False, "chevron": False},
    "visible_components": ["jet engine"],
    "reason": "The chevron is visible.",
})
assert case["effective_raw_subject_groups"]["engine"] is True
assert case["effective_raw_subject_groups"]["chevron"] is False
assert case["schema_parser_consistency"] is False
assert "reason_claims_missing_structured_group:chevron" in case["evidence_inconsistencies"]

# J. #261 subject-proof prompt contract remains outside this mapper patch.
assert "required_viewpoint" not in source
assert "subject_proof_priority" not in source
assert "final_prompt_signature" not in source

# Budget/authority guards: no extra calls, generations, retries, or broadened engine aliases.
assert "STILL_IMAGE_MAX_PER_VIDEO" not in source
assert "AI_MAX_GENERATIONS_PER_VIDEO" not in source
assert "V3_MAX_API_CALLS" not in source
assert "reason is diagnostics only" in source
engine_alias_block = source.split('"engine": {', 1)[1].split('}', 1)[0]
assert '"engine", "jet engine"' in engine_alias_block
assert '"nacelle"' not in engine_alias_block
assert '"nozzle"' not in engine_alias_block

print("RUN 33301914013 COMPONENT GROUP MAPPING REGRESSION: PASS")
