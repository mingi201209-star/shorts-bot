"""Regression for Run 35201870755 spoiler Scene 1 claim-ownership collision.

The deterministic spoiler seed opening must stay observational. The grounded
mechanism claim that spoilers reduce lift belongs to Scene 3, so saying the
same decrease:양력 relation in Scene 1 creates a duplicate claim relation.
"""
from quality.candidate_pool_grounding_records import CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
from content.grounded_claim_plan import assign_claim_owners, validate_grounded_claim_usage


record = next(
    item for item in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    if item.get("canonical_subject") == "aircraft wing spoilers"
)
hook = record["seed_candidate"]["micro_narrative"]["hook"]

# The opening owns only the visible observation. Mechanism/effect/payoff facts
# remain available to their grounded owner scenes.
assert hook == "착륙 직후 날개 윗면의 판이 갑자기 위로 솟아오릅니다.", hook
for stolen_claim_term in ("양력", "항력", "바퀴", "제동"):
    assert stolen_claim_term not in hook, (stolen_claim_term, hook)

claims = []
for raw in record["supported_claims"]:
    item = dict(raw)
    item["provenance_present"] = True
    claims.append(item)
claims = assign_claim_owners(claims, first_scene=3)
contracts = [
    {"index": 1, "owned_claim_id": ""},
    {"index": 2, "owned_claim_id": ""},
] + [
    {"index": claim["owner_scene"], "owned_claim_id": claim["claim_id"]}
    for claim in claims
]
plan = {"grounded_claim_plan": claims, "contracts": contracts}

script = {"scenes": [
    {"text": hook},
    {"text": "비행을 위해 만든 양력을 왜 땅에 닿자마자 없애는 걸까요?"},
    {"text": claims[0]["evidence_summary"]},
    {"text": claims[1]["evidence_summary"]},
    {"text": claims[2]["evidence_summary"]},
]}
failures = validate_grounded_claim_usage(script, plan)
assert not any("duplicate claim relation=decrease:양력" in f["reason"] for f in failures), failures
print("CASE A observation-only spoiler opening preserves Scene 3 lift ownership: PASS")

# Exact production counterexample must remain blocked by the validator. This
# proves the fix is the seed wording, not a weakened claim-ownership gate.
bad = {"scenes": [dict(scene) for scene in script["scenes"]]}
bad["scenes"][0]["text"] = "착륙 직후 날개 위 판이 올라오면 비행기는 일부러 양력을 줄입니다."
bad_failures = validate_grounded_claim_usage(bad, plan)
assert any(
    "duplicate claim relation=decrease:양력 owner_scene=1 offending_scene=3" in f["reason"]
    for f in bad_failures
), bad_failures
print("CASE B Run 35201870755 duplicate decrease:양력 counterexample stays blocked: PASS")
print("RUN 35201870755 SPOILER OPENING OWNERSHIP REGRESSION: PASS")
