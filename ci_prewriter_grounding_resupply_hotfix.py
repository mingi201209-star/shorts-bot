from pathlib import Path


MAIN_PATH = Path("main.py")
MARKER = "# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1"

PATCH = r'''

# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1
# Candidate Explorer retries and fixed-topic advisory may replace the winner
# object after the original validation/supply wrapper has run. Re-apply only
# repo-owned trusted grounding immediately before the existing pre-Writer gate.
# This is deterministic: no API call, retry, threshold, or budget change.
#
# Run 34573647770 ("비행기 창문 모서리는 왜 둥글까"): PRODUCTION_TRUSTED_SUBJECT_
# IDENTITY_RECORDS alone has no aircraft-window record, so this gate blocked a
# subject whose FAA-backed, already-regression-tested identity record already
# exists in the separate Candidate Pool registry (quality/candidate_pool_
# grounding_records.py), which quality/candidate_pool_handoff.py already safely
# reads together with this one via all_trusted_candidate_records(). Reusing
# that exact existing combinator here (instead of PRODUCTION_TRUSTED_SUBJECT_
# IDENTITY_RECORDS alone) closes that coverage gap for the fixed-topic
# pre-Writer path too -- no new identity record, no confidence/threshold
# change, and no change to the match/fail-closed logic itself. Verified against
# the full production hotfix composition that this does not create a competing
# match for any existing PRODUCTION-registry subject (chevron/flap/wick): each
# subject's own PRODUCTION record still resolves alone, exactly as before.
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding
from quality.grounding_aware_candidate_supply import all_trusted_candidate_records

_original_generate_script_before_trusted_grounding_resupply = generate_script


def generate_script(topic_info, candidate):
    if isinstance(candidate, dict):
        supplied = supply_trusted_subject_grounding(
            candidate,
            trusted_records=all_trusted_candidate_records(),
        )
        # Preserve object identity because downstream wrappers may retain the
        # original Candidate reference. Only deterministic trusted supply data
        # is copied back; unresolved candidates remain fail-closed.
        candidate.clear()
        candidate.update(supplied)

    return _original_generate_script_before_trusted_grounding_resupply(
        topic_info,
        candidate,
    )
'''


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ pre-Writer trusted grounding resupply already applied")
        return
    if "CANONICAL_SUBJECT_GROUNDING_GATE_V1" not in text:
        raise RuntimeError("Canonical Subject Grounding Gate V1 must be installed first")
    MAIN_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ pre-Writer trusted grounding resupply applied")


main()
