from quality.canonical_subject_grounding import (
    evaluate_candidate_subject_grounding,
    fact_identity_precheck,
)


RUN_33230137096_COUNTEREXAMPLE = {
    "topic": "비행기 날개 끝의 작은 막대는 왜 달려 있을까",
    "angle": "날개 끝의 눈에 띄는 작은 구조물의 목적",
    "core_question": "왜 비행기 날개 끝에 작은 막대를 달아 놓았을까?",
    "micro_narrative": {
        "hook": "날개 끝의 작은 막대",
        "core_question": "왜 달려 있을까?",
        "reveal": "날개 끝 소용돌이를 줄여 유도항력을 낮춘다",
        "payoff": "연료 효율을 높인다",
    },
    "fact_check_focus": [
        "작은 막대가 날개 끝 소용돌이를 줄인다",
        "작은 막대가 유도항력을 줄인다",
    ],
    "visual_proof": ["비행기 날개 끝의 작은 막대"],
    "selection_reason": "익숙하지만 이유를 모르는 구조",
    "subject_kind": "physical_entity",
    "canonical_subject": "UNKNOWN",
    "subject_identity_confidence": 0.0,
    "grounding_evidence": [],
}


def _physical_candidate(topic, canonical_subject, confidence, evidence):
    return {
        "topic": topic,
        "subject_kind": "physical_entity",
        "canonical_subject": canonical_subject,
        "subject_identity_confidence": confidence,
        "grounding_evidence": evidence,
    }


def _source_evidence(subject):
    return [
        {
            "evidence_type": "source_backed_identity",
            "supports_subject": subject,
            "source": "verified-test-source",
            "detail": f"The source identifies the physical subject as {subject}.",
        }
    ]


def test_run_33230137096_unknown_small_rod_blocks_mechanism():
    result = evaluate_candidate_subject_grounding(RUN_33230137096_COUNTEREXAMPLE)
    assert result["status"] == "BLOCK"
    assert result["failure_type"] == "SUBJECT_IDENTITY_UNRESOLVED"
    assert result["mechanism_inference_allowed"] is False


def test_ambiguous_surface_description_can_proceed_after_real_grounding():
    candidate = _physical_candidate(
        "비행기 날개 끝의 작은 막대는 왜 달려 있을까",
        "static discharger",
        0.96,
        _source_evidence("static discharger"),
    )
    result = evaluate_candidate_subject_grounding(candidate)
    assert result["status"] == "PASS"
    assert result["mechanism_inference_allowed"] is True


def test_explicit_winglet_with_grounding_keeps_existing_path():
    candidate = _physical_candidate(
        "비행기 윙렛은 왜 위로 꺾여 있을까",
        "winglet",
        0.99,
        _source_evidence("winglet"),
    )
    assert evaluate_candidate_subject_grounding(candidate)["status"] == "PASS"


def test_explicit_flap_with_grounding_keeps_existing_path():
    candidate = _physical_candidate(
        "비행기 플랩은 착륙할 때 왜 펼쳐질까",
        "flap",
        0.99,
        _source_evidence("flap"),
    )
    assert evaluate_candidate_subject_grounding(candidate)["status"] == "PASS"


def test_non_physical_transition_does_not_false_positive():
    candidate = {
        "topic": "공항 탑승 절차가 왜 여러 단계로 나뉠까",
        "subject_kind": "non_physical_concept",
        "canonical_subject": "NOT_APPLICABLE",
        "subject_identity_confidence": 1.0,
        "grounding_evidence": [],
    }
    result = evaluate_candidate_subject_grounding(candidate)
    assert result["status"] == "PASS"
    assert result["mechanism_inference_allowed"] is True


def test_fact_cannot_pass_unknown_identity_on_mechanism_plausibility():
    script_data = {
        "topic": RUN_33230137096_COUNTEREXAMPLE["topic"],
        "subject_grounding": {
            "subject_kind": "physical_entity",
            "canonical_subject": "UNKNOWN",
            "subject_identity_confidence": 0.0,
            "grounding_evidence": [],
        },
        "scenes": [
            {
                "narration": "이 막대는 소용돌이를 줄여 유도항력을 감소시킵니다.",
            }
        ],
    }
    result = fact_identity_precheck(script_data)
    assert result is not None
    assert result["judge_type"] == "fact"
    assert result["critical_risk"] is True
    assert result["failure_type"] == "SUBJECT_IDENTITY_UNRESOLVED"


def test_fact_allows_grounded_identity_to_reach_normal_fact_judge():
    script_data = {
        "topic": "비행기 윙렛은 왜 위로 꺾여 있을까",
        "subject_grounding": {
            "subject_kind": "physical_entity",
            "canonical_subject": "winglet",
            "subject_identity_confidence": 0.99,
            "grounding_evidence": _source_evidence("winglet"),
        },
        "scenes": [],
    }
    assert fact_identity_precheck(script_data) is None


if __name__ == "__main__":
    tests = [
        test_run_33230137096_unknown_small_rod_blocks_mechanism,
        test_ambiguous_surface_description_can_proceed_after_real_grounding,
        test_explicit_winglet_with_grounding_keeps_existing_path,
        test_explicit_flap_with_grounding_keeps_existing_path,
        test_non_physical_transition_does_not_false_positive,
        test_fact_cannot_pass_unknown_identity_on_mechanism_plausibility,
        test_fact_allows_grounded_identity_to_reach_normal_fact_judge,
    ]
    for test in tests:
        test()
    print("CANONICAL SUBJECT GROUNDING GATE V1 REGRESSION: PASS")
