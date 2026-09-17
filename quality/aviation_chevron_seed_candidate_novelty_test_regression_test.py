"""Test addition: complete seed_candidate for the jet-engine chevron record.

Authority: PR #399 fixed the structural NO_GROUNDED_SEED_SUPPLY exhaustion by
completing seed_candidate for window/flap, taking the usable grounded-seed pool
from 4 to 6. Re-running Publish Stable Engine on that fix (Run 35282169005)
confirmed the structural bug is gone (all 7 attempts found a grounded
candidate) but the run still failed -- this time on the editorial Candidate
Gate / Novelty ceiling, since all 6 trusted subjects are well-known textbook
aviation facts. The Novelty Judge's own rejection reasoning ("항공기 관련
정보는 일반적으로 알려진 내용이 많아 의외성이 떨어진다") reads as a
category-level judgment about aviation content in general, not per-topic
recognition -- so it is genuinely uncertain whether a 7th grounded subject
would score any differently.

This change is a single, deliberately small test of that question: complete
seed_candidate for the "jet engine nacelle/nozzle chevrons" record in
quality/canonical_subject_grounding_supply.py, which already has full
NASA-sourced supported_claims/detail (pre-dating this session) but was never
usable by the zero-API-call grounded-seed fallback, exactly like window/flap
before PR #399. No new facts are introduced -- the seed_candidate content is
built only from the record's own pre-existing claim_ids
(flow_interface, chevron_flow_mixing, mixing_transition, noise_reduction).

This does not claim to fix the Novelty ceiling; it only removes the one
remaining mechanical gap (missing seed_candidate) so the question can be
answered empirically on the next production run.
"""
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.grounding_aware_candidate_supply import (
    all_trusted_candidate_records,
    grounded_seed_candidate_pool,
)

EXISTING_SIX_SEED_TOPICS = [
    "비행기 창문 모서리는 왜 둥글게 만들어졌을까",
    "착륙할 때 날개 뒤로 펼쳐지는 플랩",
    "비행기 날개 뒤의 가느다란 스태틱 윅",
    "착륙 직후 날개 위로 솟는 스포일러",
    "비행기 밖으로 튀어나온 작은 피토관",
    "비행기 날개 끝에서 위로 꺾인 윙렛",
]


def case_a_chevron_record_now_carries_a_seed_candidate():
    assert len(PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS) == 1
    record = PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS[0]
    assert record["canonical_subject"] == "jet engine nacelle/nozzle chevrons"
    assert isinstance(record.get("seed_candidate"), dict), "chevron still missing seed_candidate"
    print("CASE A chevron record carries a seed_candidate: PASS")


def case_b_combined_pool_now_has_seven_usable_seeds():
    records = all_trusted_candidate_records()
    with_seed = [r for r in records if isinstance(r.get("seed_candidate"), dict)]
    assert len(records) == 7, records
    assert len(with_seed) == 7, with_seed
    print("CASE B combined trusted pool has 7 records, all seed-usable: PASS")


def case_c_chevron_becomes_the_7th_fallback_after_the_existing_six_are_used():
    result = grounded_seed_candidate_pool(
        rejected_topics=EXISTING_SIX_SEED_TOPICS, max_candidates=3
    )
    assert result["status"] == "CANDIDATE_POOL", result
    topics = {c["topic"] for c in result["candidates"]}
    assert "비행기 엔진 뒤쪽의 톱니 모양 가장자리" in topics, topics
    print("CASE C chevron supplies attempt 7 once the original six are exhausted: PASS")


def case_d_chevron_seed_candidate_reuses_only_its_own_preexisting_claims():
    record = PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS[0]
    claim_ids = {c["claim_id"] for c in record["supported_claims"]}
    assert claim_ids == {
        "flow_interface",
        "chevron_flow_mixing",
        "mixing_transition",
        "noise_reduction",
    }, claim_ids
    fact_focus = " ".join(record["seed_candidate"]["fact_check_focus"])
    assert "흐름" in fact_focus and "소음" in fact_focus, fact_focus
    print("CASE D new seed_candidate content stays anchored to pre-existing chevron claims: PASS")


def case_e_no_threshold_budget_retry_change():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    text = (root / "quality" / "canonical_subject_grounding_supply.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "MAX_TOPIC_REGENERATIONS =",
        "NOVELTY_HARD_REGENERATE_SCORE =",
        "_PREWRITER_NOVELTY_MIN_SCORE =",
    )
    for token in forbidden:
        assert token not in text, f"unexpectedly touched {token}"
    print("CASE E no quality/budget/retry constant touched: PASS")


def main():
    case_a_chevron_record_now_carries_a_seed_candidate()
    case_b_combined_pool_now_has_seven_usable_seeds()
    case_c_chevron_becomes_the_7th_fallback_after_the_existing_six_are_used()
    case_d_chevron_seed_candidate_reuses_only_its_own_preexisting_claims()
    case_e_no_threshold_budget_retry_change()
    print("AVIATION CHEVRON SEED CANDIDATE REGRESSION: PASS")


if __name__ == "__main__":
    main()
