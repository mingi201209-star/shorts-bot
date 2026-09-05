from content.grounded_claim_plan import assign_claim_owners, validate_grounded_claim_usage


def claim(cid, ctype, summary, scope):
    return {
        "claim_id": cid, "claim_type": ctype, "evidence_summary": summary,
        "source": "trusted-fixture", "detail": "Run 33962777328 regression",
        "allowed_paraphrase_scope": scope, "provenance_present": True,
    }


claims = assign_claim_owners([
    claim("squarish_window_stress_concentration", "constraint",
          "각진 창문 모서리에는 압력 반복으로 응력이 집중됩니다.",
          ["각진 창문 모서리에 응력이 집중됩니다", "모서리 응력 집중"]),
    claim("rounded_window_stress_distribution", "mechanism_change",
          "둥근 모서리는 응력을 더 넓게 분산시킵니다.",
          ["둥근 모서리가 응력을 분산합니다", "응력 분포를 넓힙니다"]),
    claim("squarish_window_fatigue_rupture", "primary_result",
          "반복된 응력 집중은 금속 피로와 동체 파열 위험으로 이어질 수 있습니다.",
          ["반복 응력은 금속 피로를 키울 수 있습니다", "동체 파열 위험으로 이어질 수 있습니다"]),
])
contracts = [
    {"index": 1, "owned_claim_id": ""}, {"index": 2, "owned_claim_id": ""},
] + [{"index": c["owner_scene"], "owned_claim_id": c["claim_id"]} for c in claims]
plan = {"grounded_claim_plan": claims, "contracts": contracts}

# The production failure shape: all scenes discuss the same aircraft-window causal chain,
# but each scene owns a distinct supported fact. Shared words must not create false duplicates.
script = {"scenes": [
    {"text": "비행기 창문 모서리는 둥글게 보입니다."},
    {"text": "그런데 왜 모서리를 둥글게 만들까요?"},
    {"text": "각진 창문 모서리에는 기압 변화가 반복되면서 응력이 집중됩니다."},
    {"text": "둥근 모서리는 그 응력을 한곳에 모으지 않고 더 넓게 분산시킵니다."},
    {"text": "반복된 응력 집중은 금속 피로를 키워 동체 파열 위험으로 이어질 수 있습니다."},
]}
failures = validate_grounded_claim_usage(script, plan)
assert not failures, failures
print("CASE A Run 33962777328 distinct related claims: PASS")

# A real foreign-claim migration must still fail closed.
bad = {"scenes": [dict(s) for s in script["scenes"]]}
bad["scenes"][3] = {"text": "둥근 모서리는 응력을 분산시키고 금속 피로와 동체 파열 위험도 줄입니다."}
failures = validate_grounded_claim_usage(bad, plan)
assert any("duplicate claim squarish_window_fatigue_rupture" in f["reason"] for f in failures), failures
print("CASE B real foreign claim migration blocked: PASS")

# Unsupported outcome relation remains hard-failed.
bad2 = {"scenes": [dict(s) for s in script["scenes"]]}
bad2["scenes"][3] = {"text": "둥근 모서리는 응력을 분산시키고 연료 소비를 줄입니다."}
failures = validate_grounded_claim_usage(bad2, plan)
assert any("unplanned factual claim" in f["reason"] for f in failures), failures
print("CASE C unsupported outcome remains blocked: PASS")
print("RUN 33962777328 CLAIM OWNERSHIP REGRESSION: PASS")
