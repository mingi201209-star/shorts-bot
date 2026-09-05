"""API-free full-path rehearsal for the landing-flap fixed-topic production path.

This deliberately exercises every deterministic boundary we can validate before
spending a production run. It does not relax any runtime quality gate.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from content.grounded_claim_plan import validate_grounded_claim_usage
from quality.candidate_pool_grounding_records import CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS

TOPIC = "비행기는 착륙할 때 왜 날개 뒤쪽을 펼칠까?"
CANONICAL = "aircraft trailing-edge wing flaps deployed for landing"
EXPECTED_CLAIMS = [
    "landing_flap_low_speed_need",
    "flap_camber_lift_increase",
    "flap_drag_increase",
    "flap_low_landing_speed",
]


def record_for(subject: str):
    return next(r for r in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS if r.get("canonical_subject") == subject)


def topic_to_observable(topic: str) -> str:
    """Mirror the deterministic pre-Writer question repair for this fixed-topic shape."""
    value = re.sub(r"^(?:그런데\s+)?왜\s+", "", topic.strip()).rstrip().rstrip(".?!")
    repairs = (
        (r"었을까$", "었습니다"), (r"았을까$", "았습니다"), (r"였을까$", "였습니다"),
        (r"있을까$", "있습니다"), (r"없을까$", "없습니다"), (r"일까$", "입니다"),
        (r"될까$", "됩니다"), (r"할까$", "합니다"),
    )
    for pattern, ending in repairs:
        converted, count = re.subn(pattern, ending, value)
        if count:
            return converted + "."
    # The flap topic is an explicit Korean why-question whose predicate is 펼칠까.
    # A generic suffix table cannot safely infer 펼칩니다, so fixed-topic production
    # must supply an evidence-neutral observable opening rather than invent a reason.
    if "날개 뒤쪽" in value and "펼칠까" in value:
        return "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다."
    return ""


record = record_for(CANONICAL)
assert record["subject_kind"] == "physical_entity"
assert float(record["identity_confidence"]) >= 0.9
assert record["source"]
claims = list(record.get("supported_claims") or [])
claim_ids = [c["claim_id"] for c in claims]
assert claim_ids == EXPECTED_CLAIMS, claim_ids
assert len(set(claim_ids)) == 4
assert all(c.get("source") and c.get("evidence_summary") and c.get("allowed_paraphrase_scope") for c in claims)
print("FULL REHEARSAL A canonical grounding + 4 trusted claims: PASS")

opening = topic_to_observable(TOPIC)
assert opening == "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다.", opening
assert "?" not in opening and not opening.endswith(("까", "까요", "나요"))
scene2 = "그런데 왜 착륙할 때 플랩을 펼칠까요?"
assert scene2.endswith("?") and "왜" in scene2
print("FULL REHEARSAL B question topic -> observable Scene 1 + curiosity Scene 2: PASS")

# Four claims are owned by four distinct factual scenes after the two opening scenes.
plan_claims = []
for owner_scene, claim in enumerate(claims, start=3):
    plan_claims.append({
        "claim_id": claim["claim_id"],
        "owner_scene": owner_scene,
        "claim_type": claim["claim_type"],
        "evidence_summary": claim["evidence_summary"],
        "source": claim["source"],
        "detail": claim.get("detail", ""),
        "allowed_paraphrase_scope": claim["allowed_paraphrase_scope"],
    })
contracts = [{"index": 1, "owned_claim_id": ""}, {"index": 2, "owned_claim_id": ""}] + [
    {"index": c["owner_scene"], "owned_claim_id": c["claim_id"]} for c in plan_claims
]
plan = {"grounded_claim_plan": plan_claims, "contracts": contracts}
assert len({c["owner_scene"] for c in plan_claims}) == 4
print("FULL REHEARSAL C unique claim ownership scenes 3-6: PASS")

good = {"scenes": [
    {"text": opening},
    {"text": scene2},
    {"text": "착륙할 때는 속도가 낮아 필요한 양력을 유지하기 위해 플랩 같은 고양력 장치를 사용합니다."},
    {"text": "플랩을 펼치면 날개의 굽음이 커져 같은 조건에서 더 큰 양력을 만들 수 있습니다."},
    {"text": "플랩을 내리면 항력도 함께 커집니다."},
    {"text": "필요할 때 플랩을 펼치면 더 낮은 착륙 속도를 사용할 수 있습니다."},
]}
failures = validate_grounded_claim_usage(good, plan)
assert not failures, failures
print("FULL REHEARSAL D Writer/grounded-claim positive fixture: PASS")

bad = {"scenes": [dict(s) for s in good["scenes"]]}
bad["scenes"][3]["text"] += " 그리고 연료 소비도 줄입니다."
failures = validate_grounded_claim_usage(bad, plan)
assert failures, "unsupported factual expansion must fail closed"
print("FULL REHEARSAL E unsupported expansion remains fail-close: PASS")

# Production composition invariants and downstream contract presence.
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
opening_installer = Path("ci_writer_observable_opening_hotfix.py").read_text(encoding="utf-8")
engine = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
assert 'SHORTS_TOPIC: ${{ inputs.topic }}' in workflow
assert 'V3_MAX_API_CALLS: "60"' in workflow
assert 'V3_MAX_COST_USD: "0.05"' in workflow
assert 'MAX_SCRIPT_API_CALLS = 3' in engine
assert 'scene 1 hook must be an observable statement, not a question' in opening_installer
assert 'WRITER_OBSERVABLE_OPENING_V1' in opening_installer
print("FULL REHEARSAL F production wiring/caps/opening fail-close authority: PASS")

# Make sure the fixture already carries concrete visualizable subject language.
for idx, scene in enumerate(good["scenes"], start=1):
    text = scene["text"]
    if idx in (1, 2, 4, 5, 6):
        assert any(token in text for token in ("플랩", "날개")), (idx, text)
assert "착륙" in good["scenes"][0]["text"]
print("FULL REHEARSAL G visual subject/context vocabulary continuity: PASS")

# This test must stay deterministic/API-free/render-free.
tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
forbidden_names = {"OpenAI", "create_voice", "render_final_video"}
forbidden_roots = {"requests", "httpx"}
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    func = node.func
    if isinstance(func, ast.Name):
        assert func.id not in forbidden_names, func.id
    elif isinstance(func, ast.Attribute):
        root = func.value
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            assert root.id not in forbidden_roots, root.id
print("FULL REHEARSAL H API/network/render-free: PASS")
print("FIXED_TOPIC_FULL_PATH_REHEARSAL=PASS")
