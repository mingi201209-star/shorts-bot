"""Canonical Subject Grounding Supply V1 regressions.

Production counterexample: Run 33234851380 selected the fixed chevron topic,
then reached Canonical Subject Grounding with UNKNOWN identity because the
trusted supplier was not actually installed on the live Candidate path.
"""

from pathlib import Path
import importlib
import subprocess
import sys

from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding


FIXED_CHEVRON_TOPIC = "비행기 엔진 뒤는 왜 톱니처럼 생겼을까"
EXPECTED_CHEVRON_CANONICAL = "jet engine nacelle/nozzle chevrons"


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


def _production_candidate(topic: str):
    return {
        "topic": topic,
        "angle": "엔진 뒤쪽의 톱니 모양 가장자리가 왜 필요한지 설명",
        "core_question": "왜 비행기 엔진 뒤는 톱니처럼 생겼을까?",
        "micro_narrative": {
            "hook": "비행기 엔진 뒤쪽은 톱니처럼 잘려 있습니다.",
            "core_question": "왜 비행기 엔진 뒤는 톱니처럼 생겼을까?",
            "reveal": "뒤쪽 가장자리가 공기 흐름을 섞는 방식과 관련 있습니다.",
            "payoff": "눈에 띄는 톱니 모양이 실제 제트 엔진 설계 요소입니다.",
        },
        "fact_check_focus": ["톱니 모양 가장자리의 정확한 명칭과 위치를 확인"],
        "visual_proof": ["비행기 제트 엔진 뒤쪽의 톱니 모양 가장자리"],
        "selection_reason": "실제 눈에 보이는 항공기 구조를 구체적인 질문으로 설명할 수 있음",
    }


def _trusted_record(canonical: str, *, feature_descriptions, context_descriptions, source: str):
    return {
        "record_type": "trusted_subject_identity",
        "canonical_subject": canonical,
        "subject_kind": "physical_entity",
        "identity_confidence": 0.97,
        "feature_descriptions": list(feature_descriptions),
        "context_descriptions": list(context_descriptions),
        "source": source,
        "detail": f"trusted source explicitly identifies the documented feature as {canonical}",
    }


def _apply_production_candidate_wiring():
    # Mirror the live Candidate repair/normalization ordering up through the
    # existing Candidate grounded-recovery installer. The Supply installer is
    # reached through that same import chain, not called directly.
    scripts = (
        "ci_topic_input_hotfix.py",
        "ci_aviation_candidate_context_hotfix.py",
        "ci_aviation_candidate_specificity_hotfix.py",
        "ci_aviation_context_signature_compat_hotfix.py",
        "ci_aviation_specificity_output_repair_hotfix.py",
        "ci_aviation_specificity_projection_hotfix.py",
        "ci_candidate_grounded_recovery_hotfix.py",
    )
    for script in scripts:
        subprocess.run([sys.executable, script], check=True)

    explorer_source = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
    assert "# CANONICAL_SUBJECT_GROUNDING_GATE_V1" in explorer_source
    assert "# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1" in explorer_source


def run():
    before = _base_candidate(FIXED_CHEVRON_TOPIC)
    assert evaluate_candidate_subject_grounding(before)["status"] == "BLOCK"
    print("CASE BEFORE run-33234851380 unresolved identity: PASS")

    chevron = _base_candidate(FIXED_CHEVRON_TOPIC)
    supplied = supply_trusted_subject_grounding(
        chevron,
        trusted_records=[
            _trusted_record(
                EXPECTED_CHEVRON_CANONICAL,
                feature_descriptions=(
                    "sawtooth or serrated trailing edges on a jet engine nacelle or nozzle",
                    "비행기 엔진 뒤는 톱니처럼 생긴 가장자리",
                ),
                context_descriptions=(
                    "jet engine nacelle or nozzle on an aircraft",
                    "비행기 엔진 뒤는",
                ),
                source="NASA: nasa.gov/image-article/nasa-contribution-chevrons/",
            )
        ],
    )
    grounded = evaluate_candidate_subject_grounding(supplied)
    assert grounded["status"] == "PASS", grounded
    assert supplied["canonical_subject"] == EXPECTED_CHEVRON_CANONICAL
    assert supplied["subject_identity_confidence"] >= 0.80
    assert supplied.get("_trusted_grounding_evidence")
    print("CASE A chevrons + trusted evidence resolves and passes: PASS")

    small_rod = _base_candidate("비행기 날개 끝의 작은 막대는 왜 달려 있을까")
    unchanged = supply_trusted_subject_grounding(small_rod, trusted_records=[])
    assert unchanged["canonical_subject"] == "UNKNOWN"
    assert evaluate_candidate_subject_grounding(unchanged)["status"] == "BLOCK"
    print("CASE B small rod without trusted identity remains blocked: PASS")

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

    flap = _base_candidate("비행기 날개의 플랩은 왜 내려올까")
    flap_supplied = supply_trusted_subject_grounding(
        flap,
        trusted_records=[
            _trusted_record(
                "aircraft trailing-edge flap",
                feature_descriptions=(
                    "flap on the trailing edge of an aircraft wing",
                    "비행기 날개의 플랩",
                ),
                context_descriptions=(
                    "aircraft wing high-lift device",
                    "비행기 날개의",
                ),
                source="FAA Airplane Flying Handbook",
            )
        ],
    )
    assert evaluate_candidate_subject_grounding(flap_supplied)["status"] == "PASS"
    print("CASE D flap + trusted evidence passes: PASS")

    unrelated = _base_candidate(FIXED_CHEVRON_TOPIC)
    unrelated_result = supply_trusted_subject_grounding(
        unrelated,
        trusted_records=[
            _trusted_record(
                "aircraft trailing-edge flap",
                feature_descriptions=("비행기 날개의 플랩",),
                context_descriptions=("비행기 날개의",),
                source="FAA Airplane Flying Handbook",
            )
        ],
    )
    assert unrelated_result["canonical_subject"] == "UNKNOWN"
    assert evaluate_candidate_subject_grounding(unrelated_result)["status"] == "BLOCK"
    print("CASE E unrelated evidence cannot resolve subject: PASS")

    process = _base_candidate("비행기가 착륙할 때 감속 과정은 어떻게 이어질까")
    process.update({
        "subject_kind": "non_physical_concept",
        "canonical_subject": "NOT_APPLICABLE",
        "subject_identity_confidence": 1.0,
    })
    process_result = supply_trusted_subject_grounding(process, trusted_records=[])
    assert evaluate_candidate_subject_grounding(process_result)["status"] == "PASS"
    print("CASE F non-physical concept unchanged: PASS")

    # Production-path regression: run the real Candidate hotfix wiring, then
    # traverse validate_explorer_output's actual normalization/copy path.
    _apply_production_candidate_wiring()
    import content.candidate_explorer as candidate_explorer
    candidate_explorer = importlib.reload(candidate_explorer)

    parsed = {
        "status": "SELECTED",
        "winner": _production_candidate(FIXED_CHEVRON_TOPIC),
        "runner_up": None,
    }
    production_result = candidate_explorer.validate_explorer_output(parsed)
    winner = production_result["winner"]

    assert winner["canonical_subject"] == EXPECTED_CHEVRON_CANONICAL, winner
    assert winner["subject_kind"] == "physical_entity", winner
    assert winner["subject_identity_confidence"] >= 0.80, winner
    assert winner.get("_trusted_grounding_evidence"), winner
    gate_result = evaluate_candidate_subject_grounding(winner)
    assert gate_result["status"] == "PASS", gate_result
    print("CASE G production repair/normalization path preserves trusted grounding to Gate: PASS")

    print("CANONICAL SUBJECT GROUNDING SUPPLY V1 REGRESSION: PASS")


if __name__ == "__main__":
    run()
