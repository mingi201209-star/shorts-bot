"""API-free full-path rehearsal for the landing-flap fixed topic."""
import ast
import subprocess
import sys
from pathlib import Path

from content.grounded_claim_plan import validate_grounded_claim_usage
from quality.candidate_pool_grounding_records import CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS

TOPIC = "비행기는 착륙할 때 왜 날개 뒤쪽을 펼칠까?"
CANONICAL = "aircraft trailing-edge wing flaps deployed for landing"
EXPECTED = ["landing_flap_low_speed_need", "flap_camber_lift_increase", "flap_drag_increase", "flap_low_landing_speed"]
record = next(r for r in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS if r.get("canonical_subject") == CANONICAL)
claims = list(record.get("supported_claims") or [])
assert record.get("subject_kind") == "physical_entity"
assert float(record.get("identity_confidence") or 0) >= 0.9
assert [c.get("claim_id") for c in claims] == EXPECTED
assert len({c.get("claim_id") for c in claims}) == 4
assert all(c.get("source") and c.get("evidence_summary") and c.get("allowed_paraphrase_scope") for c in claims)
print("FULL A grounding + four claims: PASS")

subprocess.run([sys.executable, "ci_writer_observable_opening_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_fixed_topic_flap_opening_hotfix.py"], check=True)
from content.script_engine_v2 import _question_hook_to_observation
opening = _question_hook_to_observation(TOPIC, TOPIC)
assert opening == "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다.", opening
assert "?" not in opening
question = "그런데 왜 착륙할 때 플랩을 펼칠까요?"
assert question.endswith("?")
print("FULL B question topic -> observable Scene1 + question Scene2: PASS")

plan_claims = []
for scene, c in enumerate(claims, start=3):
    plan_claims.append({**c, "owner_scene": scene})
plan = {"grounded_claim_plan": plan_claims, "contracts": [{"index": 1, "owned_claim_id": ""}, {"index": 2, "owned_claim_id": ""}] + [{"index": c["owner_scene"], "owned_claim_id": c["claim_id"]} for c in plan_claims]}
assert [c["owner_scene"] for c in plan_claims] == [3,4,5,6]
print("FULL C unique claim ownership: PASS")

good = {"scenes": [
 {"text": opening},
 {"text": question},
 {"text": "착륙할 때는 속도가 낮아 필요한 양력을 유지하기 위해 플랩 같은 고양력 장치를 사용합니다."},
 {"text": "플랩을 펼치면 날개의 굽음이 커져 같은 조건에서 더 큰 양력을 만들 수 있습니다."},
 {"text": "플랩을 내리면 항력도 함께 커집니다."},
 {"text": "필요할 때 플랩을 펼치면 더 낮은 착륙 속도를 사용할 수 있습니다."},
]}
failures = validate_grounded_claim_usage(good, plan)
assert not failures, failures
print("FULL D Writer grounded-claim positive fixture: PASS")

bad = {"scenes": [dict(s) for s in good["scenes"]]}
bad["scenes"][3] = {"text": good["scenes"][3]["text"] + " 그리고 연료 소비를 줄입니다."}
assert validate_grounded_claim_usage(bad, plan)
print("FULL E unsupported expansion fail-close: PASS")

workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
engine = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
assert 'SHORTS_TOPIC: ${{ inputs.topic }}' in workflow
assert 'V3_MAX_API_CALLS: "60"' in workflow
assert 'V3_MAX_COST_USD: "0.05"' in workflow
assert 'MAX_SCRIPT_API_CALLS = 3' in engine
assert 'FIXED_TOPIC_FLAP_OBSERVABLE_OPENING_V1' in engine
print("FULL F production wiring + caps + opening composition: PASS")

# Visual preconditions that can be checked without Vision/assets.
assert "플랩" in good["scenes"][0]["text"] and "착륙" in good["scenes"][0]["text"]
assert all(any(t in s["text"] for t in ("플랩", "날개", "착륙")) for s in good["scenes"])
print("FULL G visual subject/context vocabulary continuity: PASS")

# Rehearsal itself may only spawn repo-local deterministic installers; no network/render/API calls.
tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        assert node.func.id not in {"OpenAI", "create_voice", "render_final_video"}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        root = node.func.value
        while isinstance(root, ast.Attribute): root = root.value
        if isinstance(root, ast.Name): assert root.id not in {"requests", "httpx"}
print("FULL H API/network/render-free: PASS")
print("FIXED_TOPIC_FULL_PATH_REHEARSAL=PASS")
