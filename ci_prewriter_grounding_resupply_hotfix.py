from pathlib import Path


MAIN_PATH = Path("main.py")
MARKER = "# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1"

PATCH = r'''

# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1
# Candidate Explorer retries and fixed-topic advisory may replace the winner
# object after the original validation/supply wrapper has run. Re-apply only
# repo-owned trusted grounding immediately before the existing pre-Writer gate.
# This is deterministic: no API call, retry, threshold, or budget change.
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)

_original_generate_script_before_trusted_grounding_resupply = generate_script


def generate_script(topic_info, candidate):
    if isinstance(candidate, dict):
        supplied = supply_trusted_subject_grounding(
            candidate,
            trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
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
