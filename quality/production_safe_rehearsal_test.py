"""API-free rehearsal for the production-safe fixed-topic path."""
from pathlib import Path

from content.grounded_claim_plan import validate_grounded_claim_usage
from quality.production_safe_topic_pool import inspect_safe_topic

TOPIC = "비행기 창문 모서리는 왜 둥글게 만들어졌을까"

result = inspect_safe_topic(TOPIC)
assert result["eligible"], result
assert result["canonical_subject"] == "modern aircraft passenger window with rounded/oval corners"
assert len(result["claim_ids"]) == 3, result["claim_ids"]
assert len(set(result["claim_ids"])) == 3
assert result["owner_scenes"] == [3, 4, 5], result["owner_scenes"]
print("REHEARSAL A trusted identity + 3 distinct claims + unique ownership: PASS")

claims = result["grounded_claim_plan"]
contracts = [
    {"index": 1, "owned_claim_id": ""},
    {"index": 2, "owned_claim_id": ""},
] + [{"index": item["owner_scene"], "owned_claim_id": item["claim_id"]} for item in claims]
plan = {"grounded_claim_plan": claims, "contracts": contracts}

# Source-faithful fixture: every factual scene realizes exactly its owned claim.
good = {"scenes": [
    {"text": "비행기 창문 모서리는 둥글게 보입니다."},
    {"text": "그런데 왜 창문 모서리를 둥글게 만들까요?"},
    {"text": "초기 Comet의 각진 창문 모서리에는 높은 응력이 집중됐습니다."},
    {"text": "현대의 둥근 창문은 곡선 가장자리로 응력이 흐르게 합니다."},
    {"text": "각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 이어질 수 있었습니다."},
]}
failures = validate_grounded_claim_usage(good, plan)
assert not failures, failures
print("REHEARSAL B Writer claim-ownership contract positive fixture: PASS")

# A true cross-scene migration remains blocked.
bad = {"scenes": [dict(scene) for scene in good["scenes"]]}
bad["scenes"][3] = {"text": "둥근 창문은 곡선으로 응력이 흐르고 재료 피로와 동체 파열로 이어질 수 있었습니다."}
failures = validate_grounded_claim_usage(bad, plan)
assert failures, "foreign/duplicate factual migration must fail closed"
print("REHEARSAL C foreign claim migration fail-close: PASS")

# An unsupported factual relation remains blocked.
bad2 = {"scenes": [dict(scene) for scene in good["scenes"]]}
bad2["scenes"][3] = {"text": "둥근 창문은 곡선으로 응력이 흐르고 연료 소비를 줄입니다."}
failures = validate_grounded_claim_usage(bad2, plan)
assert any("unplanned factual claim" in item["reason"] for item in failures), failures
print("REHEARSAL D unsupported factual expansion fail-close: PASS")

# Production composition/safety invariants: fixed topic exists already, automatic mode remains available,
# and this rehearsal introduces no network/model call or threshold relaxation.
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
topic_hotfix = Path("ci_topic_input_hotfix.py").read_text(encoding="utf-8")
script_engine = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
assert 'SHORTS_TOPIC: ${{ inputs.topic }}' in workflow
assert 'Optional fixed production topic (blank = automatic selection)' in workflow
assert 'V3_MAX_API_CALLS: "60"' in workflow
assert 'V3_MAX_COST_USD: "0.05"' in workflow
assert 'forced_topic = os.environ.get(' in topic_hotfix
assert 'MAX_SCRIPT_API_CALLS = 3' in script_engine
print("REHEARSAL E fixed-topic wiring + automatic dev path + caps unchanged: PASS")

# Keep the rehearsal deterministic and API-free by construction.
source = Path(__file__).read_text(encoding="utf-8")
for forbidden in ("OpenAI(", "requests.", "httpx.", "create_voice(", "render_final_video("):
    assert forbidden not in source, forbidden
print("REHEARSAL F API-free deterministic boundary: PASS")
print("PRODUCTION_SAFE_FIXED_TOPIC_REHEARSAL=PASS")
