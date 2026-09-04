"""Authority regression for Run 33845975703 Scene 1.

The production asset still-0fe192df975c4011 was HUMAN-QA rejected because the
fan face/blades are visible head-on, while the existing same-call structured
Vision response incorrectly reported rear=True and front=False.  This test does
not make a Vision, LLM, image-generation, network, or production call.  It locks
the verifier contract needed to prevent that physical false-positive class.
"""
from pathlib import Path


AUTHORITY_RUN = 33845975703
AUTHORITY_ASSET = "still-0fe192df975c4011"
AUTHORITY_AUTO = {
    "rear_nozzle_or_trailing_edge_identifiable": True,
    "chevron_attached_to_rear_nozzle_or_trailing_edge": True,
    "front_intake_or_fan_side_dominant": False,
    "mobile_structure_identifiable": True,
}
AUTHORITY_HUMAN_OBSERVATION = "fan blades clearly visible head-on"

source = (
    Path(__file__).resolve().parents[1]
    / "ci_run_33377519851_scene1_viewpoint_structure_hotfix.py"
).read_text(encoding="utf-8")

# Preserve #269's four-field acceptance boundary and fail-close precedence.
for field in AUTHORITY_AUTO:
    assert field in source, field
assert 'and not evidence["front_intake_or_fan_side_dominant"]' in source

# Run 33845975703 proved that generic "fan face" wording was not discriminative
# enough.  The SAME existing Vision call must be explicitly forced to treat a
# head-on visible fan/blade/hub cue as a front-side contradiction, regardless of
# a serrated-looking outer rim.  No new structured field or model call is needed.
contract = source.lower()
assert "fan blades are clearly visible head-on" in contract
assert "fan hub" in contract
assert "must set front_intake_or_fan_side_dominant=true" in contract
assert "must set rear_nozzle_or_trailing_edge_identifiable=false" in contract
assert "must set chevron_attached_to_rear_nozzle_or_trailing_edge=false" in contract

# Ambiguous front-vs-rear identity must not be promoted into positive rear proof.
assert "if front-versus-rear identity is ambiguous" in contract
assert "fail closed" in contract

# Guardrails: the contract must still explicitly allow real rear/rear-quarter
# nozzle views and must not weaken #269's mobile readability requirement.
assert "rear or rear-quarter close-up of the trailing edge" in source
assert 'and evidence["mobile_structure_identifiable"]' in source

# Cost/call invariants for this focused fix.
for forbidden in (
    "authorize_call(",
    "client.images.generate(",
    "chat.completions.create(",
    "responses.create(",
):
    assert forbidden not in source, forbidden

print(
    "RUN 33845975703 FRONT FAN CONTRADICTION REGRESSION: PASS "
    f"run={AUTHORITY_RUN} asset={AUTHORITY_ASSET}"
)
