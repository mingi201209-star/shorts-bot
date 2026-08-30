"""Run 33298087222 Scene 1 generated-still subject-proof regression.

No image or Vision API call is made. This fixture guards the generation prompt
boundary that lost trusted canonical chevron composition evidence in production.
Verification strictness is covered by the existing structured Vision regressions.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video import still_image_fallback as still  # noqa: E402


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
        "grounding_source": "trusted-fixture",
    },
}

contract = still._canonical_still_contract(SCENE)
prompt = still._prompt(SCENE).lower()
source = (ROOT / "video/still_image_fallback.py").read_text(encoding="utf-8")

# Run 33298087222 loss boundary: trusted metadata must now control composition,
# rather than surviving only inside the stock search query.
assert contract["canonical_subject"] == "jet engine nacelle/nozzle chevrons"
assert contract["trusted_visual_discriminators"] == ["nacelle", "nozzle", "chevron", "serrated"]
assert contract["required_viewpoint"] == "rear or rear-quarter close-up of the trailing edge"
assert contract["subject_proof_priority"][:4] == ["nozzle", "nacelle", "chevron", "serrated"]

# A. Front intake + fan blades dominant was the production counterexample.
# Generation must explicitly demote that composition; Vision remains fail-close.
assert "front fan intake dominant" in prompt
assert "engine interior blades as primary subject" in prompt

# B. Generic side/turbine framing must not outrank the rear proof component.
assert "generic turbine close-up" in prompt
assert "required viewpoint from trusted physical evidence: rear or rear-quarter close-up" in prompt

# C. Positive supply target: rear nozzle/nacelle and serrated chevron proof must
# be the first/highest-priority composition tokens, with aircraft context secondary.
assert "subject-proof priority, highest first: nozzle, nacelle, chevron, serrated" in prompt
assert "externally visible component must occupy a large central portion" in prompt
assert "aircraft context may remain visible but must be secondary" in prompt

# D. Small/distant chevron is discouraged at generation time without lowering
# any verifier threshold.
assert "immediately identifiable on a phone screen" in prompt

# E. The prompt still requires the exact real-world physical subject; a serrated
# shape from another domain cannot become acceptable through generation wording.
assert "show the exact physical subject named in the narration clearly and prominently" in prompt
assert "cross-domain metaphors" in prompt

# F. No trusted rear/trailing-edge evidence => no rear viewpoint invention.
GENERIC = {
    "scene_id": 9,
    "role": "phenomenon",
    "text": "비행기 창문은 둥근 모서리입니다.",
    "visual_goal": "aircraft window",
    "keyword": "aircraft window rounded corner",
    "_canonical_visual_supply": {
        "canonical_subject": "aircraft passenger window",
        "identity_confidence": 0.98,
        "canonical_terms": ["aircraft", "passenger", "window"],
        "visual_discriminators": ["window", "rounded"],
        "grounding_source": "trusted-fixture",
    },
}
generic_contract = still._canonical_still_contract(GENERIC)
generic_prompt = still._prompt(GENERIC).lower()
assert generic_contract["required_viewpoint"] == ""
assert "required viewpoint from trusted physical evidence" not in generic_prompt
assert "front fan intake dominant" not in generic_prompt

# G. Trusted canonical rear/nozzle+chevron evidence deterministically activates
# subject-proof composition with no extra generation/retry budget.
assert still.STILL_IMAGE_MAX_PER_VIDEO == 2
assert '"n": 1' in source
assert prompt.count("rear or rear-quarter") == 1
assert "nozzle" in prompt and "chevron" in prompt and "serrated" in prompt

# Diagnostics must expose only a normalized prompt signature, not persist the raw
# prompt. The trace helper is deterministic and does not make any external call.
assert callable(still._trace_canonical_still)
assert "final_prompt_signature" in source

print("RUN 33298087222 SCENE 1 STILL SUBJECT-PROOF REGRESSION: PASS")
