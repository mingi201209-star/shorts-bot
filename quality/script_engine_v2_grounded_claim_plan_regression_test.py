"""Grounded Claim Plan regression for Run 33239832517 and cross-topic cases.

This is intentionally deterministic: no model/network call is made. The production
counterexample must be impossible to accept because Writer facts are owned by a
source-backed claim plan before narration is written.
"""
import importlib
import runpy


# Reproduce the production Writer composition before importing the V2 modules.
runpy.run_path("ci_writer_compliance_plan_hotfix.py", run_name="__main__")
runpy.run_path("ci_grounded_claim_plan_hotfix.py", run_name="__main__")

import content.script_engine_v2 as engine
import content.script_engine_v2_runner as runner
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)

engine = importlib.reload(engine)
runner = importlib.reload(runner)


def _scene(text, keyword="aircraft mechanism detail"):
    return {
        "text": text,
        "visual_goal": "실제 구조와 작동 관계를 가까이 보여주는 장면입니다.",
        "keyword": keyword,
    }


def run_332398_candidate():
    # Preserve the exact live drift inputs as hostile Candidate-owned material.
    # Trusted claim supply must outrank these plausible-but-unsupported effects.
    raw = {
        "topic": "비행기 엔진 뒤는 왜 톱니처럼 생겼을까",
        "angle": "비행기 엔진 뒤 톱니 모양의 작동 원리",
        "core_question": "비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까?",
        "specific_observation": "비행기 엔진 뒤쪽의 톱니 모양 가장자리",
        "fact_check_focus": [
            "톱니 모양은 공기 흐름을 개선합니다.",
            "이 디자인은 항력을 줄이는 데 도움을 줍니다.",
            "엔진 뒤쪽 소용돌이를 줄이면 항력 감소에 기여합니다.",
            "연료 효율과 비행 안정성이 향상됩니다.",
        ],
        "visual_proof": ["비행기 엔진 뒤쪽의 톱니 모양 가장자리"],
        "micro_narrative": {
            "hook": "비행기 엔진 뒤는 톱니처럼 생겼습니다.",
            "core_question": "비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까?",
            "reveal": (
                "톱니 모양은 엔진 뒤쪽에서 발생하는 소용돌이를 줄이기 위해 디자인되었고, "
                "이는 항공기 후방에서의 항력 감소에 기여합니다."
            ),
            "payoff": (
                "결과적으로, 이러한 디자인 덕분에 비행기의 연료 효율이 향상되고 "
                "비행 안정성이 증가합니다."
            ),
        },
    }
    return supply_trusted_subject_grounding(
        raw,
        trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )


def _synthetic_candidate(topic, hook, question, claims):
    return {
        "topic": topic,
        "angle": "grounded physical mechanism",
        "core_question": question,
        "fact_check_focus": [item["evidence_summary"] for item in claims],
        "visual_proof": [topic],
        "micro_narrative": {
            "hook": hook,
            "core_question": question,
            # Hostile legacy locks must not become factual authority.
            "reveal": "마지막이라서 성능이 전반적으로 좋아집니다.",
            "payoff": "결과적으로 모든 면에서 더 효율적이고 안정적입니다.",
        },
        "subject_kind": "physical_entity",
        "canonical_subject": topic,
        "subject_identity_confidence": 0.95,
        "_trusted_grounding_evidence": [{
            "evidence_type": "source_backed_identity",
            "supports_subject": topic,
            "source": "fixture://identity",
            "detail": "synthetic identity fixture",
        }],
        "_trusted_grounded_claims": claims,
    }


def _claim(claim_id, claim_type, evidence_summary, paraphrases):
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "evidence_summary": evidence_summary,
        "source": "fixture://claims",
        "detail": "synthetic grounded claim fixture",
        "allowed_paraphrase_scope": list(paraphrases),
    }


def assert_run_332398_plan_and_rejection():
    candidate = run_332398_candidate()
    assert candidate["canonical_subject"] == "jet engine nacelle/nozzle chevrons"
    assert candidate["subject_identity_confidence"] >= 0.80
    assert candidate.get("_trusted_grounded_claims"), candidate

    plan = engine.build_narrative_plan(candidate)
    assert plan["version"] == "script-engine-v2-grounded-claim-plan"
    assert plan["target_scene_count"] == 6, plan
    assert 5 <= plan["target_scene_count"] <= 8

    claim_plan = plan["grounded_claim_plan"]
    ids = [item["claim_id"] for item in claim_plan]
    assert ids == [
        "flow_interface",
        "chevron_flow_mixing",
        "mixing_transition",
        "noise_reduction",
    ], ids
    assert all(item.get("owner_scene") for item in claim_plan)
    assert len({item["owner_scene"] for item in claim_plan}) == len(claim_plan)
    assert all(item.get("provenance_present") is True for item in claim_plan)

    # Candidate-authored drift never becomes a planned claim.
    serialized = str(claim_plan)
    for forbidden in ("항력", "연료 효율", "비행 안정성"):
        assert forbidden not in serialized, serialized

    contracts = plan["contracts"]
    for contract in contracts[2:]:
        assert contract.get("owned_claim_id"), contract
        assert contract.get("supporting_evidence_summary"), contract
        assert contract.get("grounding_provenance_present") is True, contract

    payload = engine.writer_payload(candidate, plan)
    assert payload["grounded_claim_plan"] == claim_plan
    assert payload["rules"]["writer_does_not_choose_facts"] is True
    assert payload["rules"]["reject_unplanned_factual_claims"] is True
    assert payload["rules"]["use_each_owned_claim_exactly_once"] is True
    # Raw Candidate fact strings are not factual authority anymore.
    assert "facts" not in payload

    live_bad = {
        "title": "비행기 엔진 뒤의 톱니 형태",
        "scenes": [
            _scene("비행기 엔진 뒤는 톱니처럼 생겼습니다."),
            _scene("그런데 비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까요?"),
            _scene("톱니 모양은 공기 흐름을 개선합니다."),
            _scene("이 디자인은 항력을 줄이는 데 도움을 줍니다."),
            _scene(
                "톱니 모양은 엔진 뒤쪽에서 발생하는 소용돌이를 줄이기 위해 디자인되었고, "
                "이는 항공기 후방에서의 항력 감소에 기여합니다."
            ),
            _scene(
                "결과적으로, 이러한 디자인 덕분에 비행기의 연료 효율이 향상되고 "
                "비행 안정성이 증가합니다."
            ),
        ],
    }
    live_bad = engine.apply_locked_scenes(live_bad, plan)
    validation = runner._combined_validation(live_bad, plan)
    assert validation["valid"] is False, validation
    reasons = " | ".join(validation["reasons"])
    assert "duplicate claim" in reasons and "항력" in reasons, reasons
    assert "unplanned factual claim" in reasons, reasons
    assert "연료" in reasons or "효율" in reasons, reasons
    assert "안정" in reasons, reasons

    # A bounded Writer response that only realizes owned grounded claims is accepted.
    good = {
        "title": "비행기 엔진 뒤 톱니의 이유",
        "scenes": [
            _scene("비행기 엔진 뒤는 톱니처럼 생겼습니다.", "aircraft jet engine chevron"),
            _scene("그런데 비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까요?", "jet engine chevron detail"),
            _scene("엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥 공기 흐름이 서로 만납니다.", "jet exhaust flow interface"),
            _scene("톱니 가장자리는 이 두 흐름이 섞이는 방식을 바꿉니다.", "chevron exhaust flow mixing"),
            _scene("그래서 두 흐름 사이의 급격한 경계가 더 점진적인 전환으로 바뀝니다.", "chevron gradual flow transition"),
            _scene("그 결과 셰브론의 주된 효과는 제트 소음을 줄이는 것입니다.", "jet engine noise reduction"),
        ],
    }
    good = engine.apply_locked_scenes(good, plan)
    good_validation = runner._combined_validation(good, plan)
    assert good_validation["valid"] is True, good_validation


def assert_cross_topic_generalization():
    winglet = _synthetic_candidate(
        "aircraft winglets",
        "비행기 날개 끝은 위로 꺾여 있습니다.",
        "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
        [
            _claim("pressure_difference", "mechanism_input", "날개 위아래에는 압력 차이가 생깁니다.", ["날개 위아래의 압력 차이", "pressure difference across the wing"]),
            _claim("wingtip_vortex", "mechanism_change", "날개 끝에서는 압력 차이 때문에 소용돌이가 만들어집니다.", ["날개 끝 소용돌이가 만들어집니다", "wingtip vortex forms"]),
            _claim("induced_drag_reduction", "result", "윙렛은 날개 끝 소용돌이를 약하게 해 유도항력을 줄입니다.", ["유도항력을 줄입니다", "reduces induced drag"]),
        ],
    )
    flap = _synthetic_candidate(
        "aircraft trailing-edge flaps",
        "착륙할 때 비행기 날개 뒤쪽이 아래로 내려갑니다.",
        "왜 착륙할 때 날개 뒤쪽이 내려갈까요?",
        [
            _claim("camber_change", "mechanism_input", "플랩을 내리면 날개의 캠버가 커집니다.", ["날개 캠버가 커집니다", "increases wing camber"]),
            _claim("lift_increase", "mechanism_change", "커진 캠버는 같은 속도에서 더 큰 양력을 만듭니다.", ["더 큰 양력을 만듭니다", "increases lift at the same speed"]),
            _claim("lower_speed_operation", "result", "그래서 이착륙 때 더 낮은 속도로 비행할 수 있습니다.", ["더 낮은 속도로 비행", "operate at lower speed"]),
        ],
    )

    for candidate in (winglet, flap):
        plan = engine.build_narrative_plan(candidate)
        ids = [item["claim_id"] for item in plan["grounded_claim_plan"]]
        assert len(ids) == len(set(ids)) == 3, plan
        owners = [item["owner_scene"] for item in plan["grounded_claim_plan"]]
        assert len(owners) == len(set(owners)), plan
        assert 5 <= plan["target_scene_count"] <= 8, plan
        for contract in plan["contracts"][2:]:
            assert contract["owned_claim_id"] in ids, contract


def main():
    assert_run_332398_plan_and_rejection()
    assert_cross_topic_generalization()
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("GROUNDED CLAIM PLAN REGRESSION: PASS")


if __name__ == "__main__":
    main()
