"""Focused regression for Canonical Subject Grounding Supply V1.

Production counterexample: Run 33232632149 selected the fixed chevron topic,
passed the editorial Candidate Gate, then reached the Canonical Subject Grounding
Gate with UNKNOWN identity because no trusted provenance was attached.
"""

from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding


def _base_candidate(topic: str):
    return {
        "topic": topic,
        "angle": "why this visible feature exists",
        "core_question": topic,
        "micro_narrative": {"hook": topic, "reveal": "", "payoff": ""},
        "subject_kind": "unresolved",
        "canonical_subject": "UNKNOWN",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }


def _trusted_record(canonical: str, *, feature: str, context: str, source: str):
    return {
        "record_type": "trusted_subject_identity",
        "canonical_subject": canonical,
        "subject_kind": "physical_entity",
        "identity_confidence": 0.97,
        "feature_description": feature,
        "context_description": context,
        "source": source,
        "detail": f"trusted source explicitly identifies {feature} as {canonical}",
    }


def run():
    # BEFORE / Run 33232632149 fixture: editorially valid but no trusted identity.
    before = _base_candidate("비행기 엔진 뒤는 왜 톱니처럼 생겼을까")
    assert evaluate_candidate_subject_grounding(before)["status"] == "BLOCK"
    print("CASE BEFORE run-33232632149 unresolved identity: PASS")

    # A. Ambiguous surface description resolves only because trusted evidence
    # explicitly binds the visible feature + aviation engine context to chevrons.
    chevron = _base_candidate("비행기 엔진 뒤는 왜 톱니처럼 생겼을까")
    supplied = supply_trusted_subject_grounding(
        chevron,
        trusted_records=[
            _trusted_record(
                "jet engine nacelle/nozzle chevrons",
                feature="sawtooth or serrated trailing edges",
                context="jet engine nacelle or nozzle on an aircraft",
                source="NASA: nasa.gov/image-article/nasa-contribution-chevrons/",
            )
        ],
    )
    grounded = evaluate_candidate_subject_grounding(supplied)
    assert grounded["status"] == "PASS", grounded
    assert supplied["canonical_subject"] == "jet engine nacelle/nozzle chevrons"
    assert supplied["subject_identity_confidence"] >= 0.80
    assert supplied.get("_trusted_grounding_evidence")
    print("CASE A chevrons + trusted evidence resolves and passes: PASS")

    # B. Small rod with no trusted evidence stays UNKNOWN/BLOCK.
    small_rod = _base_candidate("비행기 날개 끝의 작은 막대는 왜 달려 있을까")
    unchanged = supply_trusted_subject_grounding(small_rod, trusted_records=[])
    assert unchanged["canonical_subject"] == "UNKNOWN"
    assert evaluate_candidate_subject_grounding(unchanged)["status"] == "BLOCK"
    print("CASE B small rod without trusted identity remains blocked: PASS")

    # C. Model-authored source claim is not trusted provenance.
    fake = _base_candidate("비행기 날개 끝의 작은 막대는 왜 달려 있을까")
    fake.update({
        "subject_kind": "physical_entity",
        "canonical_subject": "invented component",
        "subject_identity_confidence": 0.99,
        "grounding_evidence": [{
            "evidence_type": "source_backed_identity",
            "supports_subject": "invented component",
            "source": "NASA",
            "detail": "model-authored claim",
        }],
    })
    assert evaluate_candidate_subject_grounding(fake)["status"] == "BLOCK"
    print("CASE C self-authored source remains blocked: PASS")

    # D. Explicit flap can pass when trusted evidence actually identifies it.
    flap = _base_candidate("비행기 날개의 플랩은 왜 내려올까")
    flap_supplied = supply_trusted_subject_grounding(
        flap,
        trusted_records=[
            _trusted_record(
                "aircraft trailing-edge flap",
                feature="flap on the trailing edge of an aircraft wing",
                context="aircraft wing high-lift device",
                source="FAA Airplane Flying Handbook",
            )
        ],
    )
    assert evaluate_candidate_subject_grounding(flap_supplied)["status"] == "PASS"
    print("CASE D flap + trusted evidence passes: PASS")

    # E. Unrelated trusted evidence must not resolve an ambiguous physical feature.
    unrelated = _base_candidate("비행기 엔진 뒤는 왜 톱니처럼 생겼을까")
    unrelated_result = supply_trusted_subject_grounding(
        unrelated,
        trusted_records=[
            _trusted_record(
                "aircraft trailing-edge flap",
                feature="flap on the trailing edge of an aircraft wing",
                context="aircraft wing high-lift device",
                source="FAA Airplane Flying Handbook",
            )
        ],
    )
    assert unrelated_result["canonical_subject"] == "UNKNOWN"
    assert evaluate_candidate_subject_grounding(unrelated_result)["status"] == "BLOCK"
    print("CASE E unrelated evidence cannot resolve subject: PASS")

    # F. Non-physical concepts remain outside the physical identity gate.
    process = _base_candidate("비행기가 착륙할 때 감속 과정은 어떻게 이어질까")
    process.update({
        "subject_kind": "non_physical_concept",
        "canonical_subject": "NOT_APPLICABLE",
        "subject_identity_confidence": 1.0,
    })
    process_result = supply_trusted_subject_grounding(process, trusted_records=[])
    assert evaluate_candidate_subject_grounding(process_result)["status"] == "PASS"
    print("CASE F non-physical concept unchanged: PASS")

    print("CANONICAL SUBJECT GROUNDING SUPPLY V1 REGRESSION: PASS")


if __name__ == "__main__":
    run()
