"""Run 35283712910: chevron seed was never actually tried.

Authority: after PR #400 completed seed_candidate for the jet-engine chevron
record (seed_priority=70, the lowest of all 7 trusted aviation seeds), Run
35283712910 re-ran Publish Stable Engine on candidate_scope=aviation. Chevron
was never selected as a Winner in that run's full log: grounded_seed_candidate_pool()
ranks by descending seed_priority and returns at most 3 candidates per call,
so with static wick (100) and spoiler (95) still unused, chevron (70) never
surfaced before the 7-attempt budget ran out.

This is a pure test-instrumentation fix, not a production behavior change:
raise chevron's seed_priority above every other trusted seed (110 > 100) so
the very next grounded-seed fallback call tries chevron FIRST, giving a clean
read on whether a genuinely new grounded aviation subject scores differently
on Novelty than the original six well-known ones -- the open question PR #400
was meant to answer but Run 35283712910 could not, because chevron was never
actually attempted.
"""
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.grounding_aware_candidate_supply import grounded_seed_candidate_pool


def case_a_chevron_outranks_every_other_trusted_seed():
    chevron_priority = PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS[0]["seed_priority"]
    other_priorities = [
        record.get("seed_priority", 0)
        for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    ]
    assert other_priorities, "expected the existing six seeded records"
    assert chevron_priority > max(other_priorities), (
        chevron_priority,
        other_priorities,
    )
    print("CASE A chevron seed_priority outranks all other trusted seeds: PASS")


def case_b_chevron_is_first_in_an_unfiltered_fallback_call():
    result = grounded_seed_candidate_pool(max_candidates=3)
    assert result["status"] == "CANDIDATE_POOL", result
    assert result["candidates"][0]["topic"] == "비행기 엔진 뒤쪽의 톱니 모양 가장자리", result


    print("CASE B chevron is now the first candidate an unfiltered fallback call returns: PASS")


def main():
    case_a_chevron_outranks_every_other_trusted_seed()
    case_b_chevron_is_first_in_an_unfiltered_fallback_call()
    print("RUN 35283712910 CHEVRON SEED PRIORITY REGRESSION: PASS")


if __name__ == "__main__":
    main()
