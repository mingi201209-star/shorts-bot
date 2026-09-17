"""Regression for the exhausted grounded-seed-fallback pool (Run 35234305931).

Authority: Run 35234305931 (publish-stable SHA 7f02f006832d5e04c10473a16fef5713e3d6ffa7)
ran all 7 Candidate attempts and terminated with
"Candidate Explorer가 제작 가능한 Winner를 확보하지 못했습니다" on the 7th attempt,
whose actual log line was:
[GROUNDING_SEED_FALLBACK] status=REGENERATE candidates=0 api_calls=0
reason=NO_GROUNDED_SEED_SUPPLY: no unused repo-owned grounded aviation seed is available

Root cause: CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS has 6 fully-sourced
aviation subjects (window, flap, static wick, spoiler, pitot tube, winglet), but
only 4 of them (static wick, spoiler, pitot tube, winglet) carried a
`seed_candidate` block -- the only field `grounded_seed_candidate_pool()`
(quality/grounding_aware_candidate_supply.py) reads to build the zero-API-call
fallback pool. Window and flap already had full FAA-sourced `supported_claims`
but could never be selected as a fallback seed, so a 7-attempt budget only had
4 usable grounded seeds to draw from -- guaranteeing exhaustion whenever the
freshly LLM-proposed candidates keep failing canonical grounding (the normal
case; observed 0-1 survivors out of 20 freshly-proposed candidates across the
7 attempts of this exact run).

Fix: complete `seed_candidate` for the window and flap records using ONLY their
own pre-existing, already-approved `supported_claims`/`detail` text -- no new
facts, no threshold/budget/retry change, no new API call.
"""
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.grounding_aware_candidate_supply import grounded_seed_candidate_pool

ROOT_ORIGINAL_FOUR_TOPICS = [
    "비행기 날개 뒤의 가느다란 스태틱 윅",
    "착륙 직후 날개 위로 솟는 스포일러",
    "비행기 밖으로 튀어나온 작은 피토관",
    "비행기 날개 끝에서 위로 꺾인 윙렛",
]


def case_a_all_six_records_now_carry_a_seed_candidate():
    assert len(CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS) == 6, (
        "this fix must not add or remove trusted identity records, only complete "
        "seed_candidate on the two that already lacked it"
    )
    missing = [
        record["canonical_subject"]
        for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
        if not isinstance(record.get("seed_candidate"), dict)
    ]
    assert not missing, f"records still missing seed_candidate: {missing}"
    print("CASE A all 6 trusted records carry a seed_candidate: PASS")


def case_b_window_and_flap_close_the_run_35234305931_exhaustion_gap():
    # Exact scenario that produced NO_GROUNDED_SEED_SUPPLY on attempt 7: the
    # original 4 seed-bearing topics are already rejected/used this run.
    result = grounded_seed_candidate_pool(
        rejected_topics=ROOT_ORIGINAL_FOUR_TOPICS, max_candidates=3
    )
    assert result["status"] == "CANDIDATE_POOL", result
    topics = {c["topic"] for c in result["candidates"]}
    assert "비행기 창문 모서리는 왜 둥글게 만들어졌을까" in topics, topics
    assert "착륙할 때 날개 뒤로 펼쳐지는 플랩" in topics, topics
    print("CASE B window+flap now supply attempt 7 instead of NO_GROUNDED_SEED_SUPPLY: PASS")


def case_c_all_six_exhausted_still_fails_closed():
    all_topics = [
        record["seed_candidate"]["topic"]
        for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    ]
    result = grounded_seed_candidate_pool(rejected_topics=all_topics, max_candidates=3)
    assert result["status"] == "REGENERATE", result
    assert "NO_GROUNDED_SEED_SUPPLY" in result["reason"], result
    print("CASE C exhausting all 6 still fails closed (no invented supply): PASS")


def case_d_new_seed_candidates_reuse_only_preexisting_claim_content():
    for canonical, fact_focus_substr_list in (
        (
            "modern aircraft passenger window with rounded/oval corners",
            ["응력", "모서리"],
        ),
        (
            "aircraft trailing-edge wing flaps deployed for landing",
            ["양력", "항력"],
        ),
    ):
        record = next(
            r
            for r in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
            if r["canonical_subject"] == canonical
        )
        claim_ids = {c["claim_id"] for c in record["supported_claims"]}
        assert claim_ids, canonical
        fact_focus = " ".join(record["seed_candidate"]["fact_check_focus"])
        for token in fact_focus_substr_list:
            assert token in fact_focus, (canonical, fact_focus)
    print("CASE D new seed_candidate content stays anchored to pre-existing claims: PASS")


def case_e_no_threshold_budget_retry_change():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    text = (root / "quality" / "candidate_pool_grounding_records.py").read_text(
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
    assert not re.search(r"\bapi_calls?\s*=\s*[1-9]", text)
    print("CASE E no quality/budget/retry constant touched: PASS")


def main():
    case_a_all_six_records_now_carry_a_seed_candidate()
    case_b_window_and_flap_close_the_run_35234305931_exhaustion_gap()
    case_c_all_six_exhausted_still_fails_closed()
    case_d_new_seed_candidates_reuse_only_preexisting_claim_content()
    case_e_no_threshold_budget_retry_change()
    print("AVIATION SEED POOL WINDOW/FLAP FALLBACK REGRESSION: PASS")


if __name__ == "__main__":
    main()
