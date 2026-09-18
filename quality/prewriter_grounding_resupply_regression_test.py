"""Regression for pre-Writer trusted grounding resupply.

A fixed-topic retry may produce a new Candidate after the Explorer validation
wrapper already supplied trusted identity. The production chain must re-apply
repo-owned trusted grounding before the existing pre-Writer gate, without
weakening that gate or adding calls/retries.

Run 34742040475 (#545) added a narrower counterexample: an LLM winner can retain
the exact pinned repo seed topic while lacking the deterministic seed object's
private record reference. The exact fixed-topic bridge may reuse the existing
repo record only when Candidate topic == SHORTS_TOPIC == one unique repo-owned
seed topic; everything else remains fail-closed.
"""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.fixed_topic_seed_grounding import (
    exact_fixed_topic_seed_record,
    project_exact_fixed_topic_seed_opening,
    supply_exact_fixed_topic_seed_grounding,
    supply_fixed_topic_scoped_trusted_grounding,
)
from quality.grounding_aware_candidate_supply import all_trusted_candidate_records


SPOILER_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"
WING_FLEX_TOPIC = "비행기 날개는 왜 비행 중에 휘어질까"


def _run_34742040475_llm_candidate():
    return {
        "topic": SPOILER_TOPIC,
        "angle": "착륙 직후 올라오는 판이 양력을 줄여 바퀴 제동을 돕는 이유",
        "core_question": "왜 착륙하자마자 날개 위 판을 올릴까?",
        "micro_narrative": {
            "hook": "착륙 직후 날개 위 판이 올라옵니다.",
            "core_question": "왜 양력을 만드는 날개에서 판을 세울까요?",
            "reveal": "스포일러는 날개 위 흐름을 깨뜨립니다.",
            "payoff": "착륙 뒤 바퀴 제동을 돕습니다.",
        },
        "fact_check_focus": ["착륙 후 스포일러 기능"],
        "visual_proof": ["착륙 직후 날개 위에서 올라온 패널"],
        "selection_reason": "fixed-topic LLM winner regression",
        "subject_kind": "physical_entity",
        "canonical_subject": "스포일러",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }


def run():
    records = all_trusted_candidate_records()
    candidate = _run_34742040475_llm_candidate()

    # Run #545 authority: this is NOT a deterministic seed object and therefore
    # has no host-owned record reference. Exact fixed-topic seed ownership is the
    # only new authority allowed to recover its existing repo grounding.
    resolved = exact_fixed_topic_seed_record(
        candidate,
        SPOILER_TOPIC,
        trusted_records=records,
    )
    assert resolved is not None
    assert resolved.get("canonical_subject") == "aircraft wing spoilers"
    assert (resolved.get("seed_candidate") or {}).get("topic") == SPOILER_TOPIC

    exact_supply = supply_exact_fixed_topic_seed_grounding(
        candidate,
        SPOILER_TOPIC,
        trusted_records=records,
    )
    assert exact_supply is not None
    supplied, supplied_record = exact_supply
    assert supplied_record is resolved
    assert supplied.get("canonical_subject") == "aircraft wing spoilers"
    assert supplied.get("_trusted_grounding_evidence")
    assert supplied.get("_trusted_grounded_claims")
    assert supplied.get("angle") == candidate.get("angle")
    print("CASE #545 exact fixed-topic spoiler seed grounding: PASS")

    # Exact means exact: punctuation/wording drift, a different fixed topic, or
    # duplicate repo ownership must never gain this capability.
    altered = deepcopy(candidate)
    altered["topic"] = SPOILER_TOPIC + "!"
    assert exact_fixed_topic_seed_record(
        altered,
        SPOILER_TOPIC,
        trusted_records=records,
    ) is None

    unknown = deepcopy(candidate)
    unknown["topic"] = "등록되지 않은 고정 주제"
    assert supply_exact_fixed_topic_seed_grounding(
        unknown,
        "등록되지 않은 고정 주제",
        trusted_records=records,
    ) is None

    duplicate_records = tuple(records) + (deepcopy(resolved),)
    assert exact_fixed_topic_seed_record(
        candidate,
        SPOILER_TOPIC,
        trusted_records=duplicate_records,
    ) is None
    print("CASE exact-topic bridge remains unique and fail-closed: PASS")

    # Run 35320620429: this exact fixed topic reached pre-Writer with trusted
    # static-wick identity/claims even though the operator pinned wing bending.
    # The repo now owns one NASA-backed exact seed for the wing-flex subject.
    wing_candidate = {
        "topic": WING_FLEX_TOPIC,
        "angle": "비행 중 주날개의 탄성 굽힘과 공력 결합",
        "core_question": "왜 비행기 날개는 비행 중에 휘어지는 걸까?",
        "micro_narrative": {
            "hook": "비행기 날개는 비행 중 실제로 탄성 굽힘을 일으킵니다.",
            "core_question": "단단한 날개가 왜 비행 중 휘어질까요?",
            "reveal": "비행 하중을 받는 유연한 구조에는 탄성 굽힘이 생깁니다.",
            "payoff": "그 변형은 공력과 다시 맞물리는 에어로엘라스틱 반응의 일부입니다.",
        },
        "fact_check_focus": ["wing bending flexibility"],
        "visual_proof": ["비행 중 위로 휘어진 주날개"],
        "selection_reason": "Run 35320620429 exact fixed-topic regression",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft static discharger (static wick)",
        "subject_identity_confidence": 0.99,
        "grounding_evidence": [],
        "_trusted_grounding_evidence": [
            {
                "evidence_type": "source_backed_identity",
                "supports_subject": "aircraft static discharger (static wick)",
                "source": "stale-wrong-trust",
                "detail": "Run 35320620429 contamination fixture",
            }
        ],
        "_trusted_grounded_claims": [
            {"claim_id": "static_charge_dissipation"}
        ],
    }

    wing_record = exact_fixed_topic_seed_record(
        wing_candidate,
        WING_FLEX_TOPIC,
        trusted_records=records,
    )
    assert wing_record is not None
    assert wing_record.get("canonical_subject") == "flexible aircraft main wing"

    wing_supply = supply_exact_fixed_topic_seed_grounding(
        wing_candidate,
        WING_FLEX_TOPIC,
        trusted_records=records,
    )
    assert wing_supply is not None
    wing_supplied, wing_supplied_record = wing_supply
    assert wing_supplied_record is wing_record
    assert wing_supplied.get("canonical_subject") == "flexible aircraft main wing"
    claim_ids = {
        str(item.get("claim_id") or "")
        for item in (wing_supplied.get("_trusted_grounded_claims") or [])
        if isinstance(item, dict)
    }
    assert {
        "flight_load_bending_response",
        "elastic_flapwise_bending",
        "aeroelastic_deflection_coupling",
    }.issubset(claim_ids)
    assert "static_charge_dissipation" not in claim_ids
    print("CASE Run 35320620429 exact wing-flex topic replaces static-wick trust: PASS")

    # Run 35323852030: after grounding was fixed, FACT=8 and Visual=8 passed,
    # but Scene 1 stayed a bare observation ("...관찰됩니다" / "...볼 수 있습니다")
    # before and after the one allowed Rewrite, keeping Hook at 6/10. Exact
    # fixed-topic production may replace only that weak opening with the same
    # record's repo-owned, source-backed opening pair.
    weak_opening = deepcopy(wing_supplied)
    weak_opening["core_question"] = "비행 중 날개가 휘어지는 이유는 무엇일까?"
    weak_opening["micro_narrative"] = deepcopy(
        weak_opening.get("micro_narrative") or {}
    )
    weak_opening["micro_narrative"]["hook"] = (
        "비행 중 비행기 날개가 아래로 휘어지는 모습을 볼 수 있습니다."
    )
    weak_opening["micro_narrative"]["core_question"] = (
        "비행 중 날개가 휘어지는 이유는 무엇일까요?"
    )

    projected, projected_record = project_exact_fixed_topic_seed_opening(
        weak_opening,
        WING_FLEX_TOPIC,
        trusted_records=records,
    )
    assert projected_record is wing_record
    assert (
        projected["micro_narrative"]["hook"]
        == "비행기 날개는 완전한 강체가 아니라, 비행 중 탄성으로 휘어지는 구조입니다."
    )
    assert (
        projected["core_question"]
        == "그런데 어떤 비행 하중이 이 날개를 실제로 휘게 만들까요?"
    )
    assert projected["micro_narrative"]["core_question"] == projected["core_question"]
    # Trusted claims and body locks remain exactly the supplied authority.
    assert projected.get("_trusted_grounded_claims") == wing_supplied.get(
        "_trusted_grounded_claims"
    )
    assert projected["micro_narrative"]["reveal"] == weak_opening[
        "micro_narrative"
    ]["reveal"]
    assert projected["micro_narrative"]["payoff"] == weak_opening[
        "micro_narrative"
    ]["payoff"]

    strong_opening = deepcopy(projected)
    strong_opening["micro_narrative"]["hook"] = (
        "비행기 날개는 하중을 받으면 탄성으로 휘어집니다."
    )
    untouched, untouched_record = project_exact_fixed_topic_seed_opening(
        strong_opening,
        WING_FLEX_TOPIC,
        trusted_records=records,
    )
    assert untouched_record is wing_record
    assert untouched["micro_narrative"]["hook"] == strong_opening[
        "micro_narrative"
    ]["hook"]

    unrelated_opening = deepcopy(weak_opening)
    unrelated_opening["topic"] = "등록되지 않은 다른 고정 주제"
    unrelated_projected, unrelated_record = project_exact_fixed_topic_seed_opening(
        unrelated_opening,
        unrelated_opening["topic"],
        trusted_records=records,
    )
    assert unrelated_record is None
    assert unrelated_projected["micro_narrative"]["hook"] == weak_opening[
        "micro_narrative"
    ]["hook"]
    print("CASE Run 35323852030 weak Hook gets trusted exact-topic opening only: PASS")

    # Systemic safety: even when Candidate details resemble another registered
    # component, an unrelated fixed topic cannot inherit that component's
    # private trust merely from downstream prose overlap.
    unrelated_topic = "비행기 날개 표면은 왜 햇빛에 반짝일까"
    misleading = deepcopy(wing_candidate)
    misleading["topic"] = unrelated_topic
    misleading["angle"] = "날개 뒤 가느다란 정전기 방전기와 무전 간섭"
    misleading["core_question"] = "날개 뒤 작은 막대는 왜 달려 있을까?"
    misleading["micro_narrative"] = {
        "hook": "날개 뒤쪽에는 가느다란 스태틱 윅이 있습니다.",
        "core_question": "왜 이런 막대를 달아둘까요?",
        "reveal": "정전기를 공기 중으로 방전합니다.",
        "payoff": "무선 간섭을 줄이는 데 도움이 됩니다.",
    }
    scoped = supply_fixed_topic_scoped_trusted_grounding(
        misleading,
        unrelated_topic,
        trusted_records=records,
    )
    assert not scoped.get("_trusted_grounding_evidence")
    assert not scoped.get("_trusted_grounded_claims")
    assert not scoped.get("_repo_owned_seed_record_ref")
    print("CASE fixed-topic scope strips unrelated trusted-subject contamination: PASS")

    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)

    main_source = Path("main.py").read_text(encoding="utf-8")
    assert main_source.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1
    assert "supply_trusted_subject_grounding(" in main_source
    assert "supply_exact_fixed_topic_seed_grounding(" in main_source
    assert "project_exact_fixed_topic_seed_opening(" in main_source
    assert "source=exact_fixed_topic_seed status=projected" in main_source
    assert '_prewriter_os.environ.get("SHORTS_TOPIC", "")' in main_source
    assert "source=exact_fixed_topic_seed" in main_source
    assert "source=fixed_topic_scoped" in main_source
    assert "supply_fixed_topic_scoped_trusted_grounding(" in main_source
    assert "candidate.clear()" in main_source
    assert "candidate.update(supplied)" in main_source
    assert main_source.index("# CANONICAL_SUBJECT_GROUNDING_GATE_V1") < main_source.index(
        "# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1"
    )

    supply_source = Path("quality/canonical_subject_grounding_supply.py").read_text(
        encoding="utf-8"
    )
    assert supply_source.count("# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1") == 1

    # Idempotence: the production installer chain may be exercised repeatedly
    # by composition/regression jobs and must not stack wrappers.
    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)
    main_source_2 = Path("main.py").read_text(encoding="utf-8")
    assert main_source_2.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1

    # Safety invariants: this fix does not alter the canonical gate itself and
    # introduces no model/API call, retry, threshold, or budget override.
    hotfix_source = Path("ci_prewriter_grounding_resupply_hotfix.py").read_text(
        encoding="utf-8"
    )
    helper_source = Path("quality/fixed_topic_seed_grounding.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "openai.chat",
        "authorize_call(",
        "MAX_TOPIC_REGENERATIONS",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
    )
    for token in forbidden:
        assert token not in hotfix_source, token
        assert token not in helper_source, token

    assert "seed_candidate" in helper_source
    assert "len(matches) != 1" in helper_source
    assert "supply_trusted_subject_grounding(" in helper_source
    assert "supply_fixed_topic_scoped_trusted_grounding" in helper_source
    assert "project_exact_fixed_topic_seed_opening" in helper_source
    assert "RUN_35323852030_FIXED_TOPIC_TRUSTED_OPENING_V1" in helper_source
    assert "_TRUSTED_GROUNDING_FIELDS" in helper_source

    print("PREWRITER TRUSTED GROUNDING RESUPPLY REGRESSION: PASS")


if __name__ == "__main__":
    run()