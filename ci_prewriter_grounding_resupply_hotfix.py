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
#
# Run 34742040475 (#545) exposed a second fixed-topic-only gap: the LLM winner
# retained topic="착륙 직후 날개 위로 솟는 스포일러" and canonical="스포일러", but
# it was not the deterministic seed object and therefore had no in-memory seed
# record reference. Generic text matching then failed closed even though the
# exact pinned topic is already owned by one FAA-backed repo seed record. For an
# explicit SHORTS_TOPIC only, bind the Candidate to that record iff Candidate
# topic == SHORTS_TOPIC == exactly one repo-owned seed_candidate.topic. The
# record is still run through the unchanged trusted supplier using only its own
# evidence-owned seed/feature/context data. Unknown/altered/ambiguous topics
# continue to the unchanged generic fail-closed resolver.
import os as _prewriter_os

from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding
from quality.fixed_topic_seed_grounding import supply_exact_fixed_topic_seed_grounding
from quality.grounding_aware_candidate_supply import (
    REPO_OWNED_SEED_RECORD_REF_FIELD,
    all_trusted_candidate_records,
    repo_owned_seed_trusted_record,
)

_original_generate_script_before_trusted_grounding_resupply = generate_script


def generate_script(topic_info, candidate):
    if isinstance(candidate, dict):
        trusted_records = all_trusted_candidate_records()
        repo_seed_record = repo_owned_seed_trusted_record(
            candidate,
            trusted_records=trusted_records,
        )

        fixed_topic = _prewriter_os.environ.get("SHORTS_TOPIC", "").strip()
        candidate_topic = str(candidate.get("topic") or "").strip()
        fixed_topic_candidate = bool(
            fixed_topic
            and candidate_topic == fixed_topic
        )

        exact_fixed_topic_supply = None
        if repo_seed_record is None:
            exact_fixed_topic_supply = supply_exact_fixed_topic_seed_grounding(
                candidate,
                fixed_topic,
                trusted_records=trusted_records,
            )

        if exact_fixed_topic_supply is not None:
            supplied, exact_fixed_topic_record = exact_fixed_topic_supply
            # Host-authorized exact fixed-topic binding creates the same
            # unforgeable in-process record capability for later wrappers.
            supplied[REPO_OWNED_SEED_RECORD_REF_FIELD] = exact_fixed_topic_record
            print(
                "[PREWRITER_GROUNDING_RESUPPLY] "
                "source=exact_fixed_topic_seed canonical="
                f"{supplied.get('canonical_subject', '')}"
            )
        elif fixed_topic_candidate and repo_seed_record is None:
            # RUN_35413574652_FIXED_TOPIC_FALSE_GROUNDING_GUARD
            # A pinned topic that is not owned by an exact repo seed must never
            # be rebound to an unrelated trusted record merely because generic
            # words overlap (e.g. a wing-flex topic becoming a static wick).
            # Preserve the Candidate's existing identity metadata exactly as-is;
            # the already-installed canonical pre-Writer gate below either
            # validates that explicit identity or fails closed.
            supplied = dict(candidate)
            print(
                "[PREWRITER_GROUNDING_RESUPPLY] "
                "source=fixed_topic_existing_grounding_only canonical="
                f"{supplied.get('canonical_subject', '')}"
            )
        else:
            candidate_trusted_records = (
                (repo_seed_record,)
                if repo_seed_record is not None
                else trusted_records
            )
            supplied = supply_trusted_subject_grounding(
                candidate,
                trusted_records=candidate_trusted_records,
            )
            if repo_seed_record is not None:
                # Keep the unforgeable exact record identity across supplier deepcopy.
                supplied[REPO_OWNED_SEED_RECORD_REF_FIELD] = repo_seed_record

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