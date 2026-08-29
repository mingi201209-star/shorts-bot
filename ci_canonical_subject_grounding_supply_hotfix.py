from pathlib import Path


MARKER = "# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1"
EXPLORER_PATH = Path("content/candidate_explorer.py")


PATCH = r'''

# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1
# Deterministic trusted provenance supplier. Runs after all model/schema repair
# output and before Candidate validation/Gate evaluation. No API call or retry.
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)

_original_validate_candidate_before_grounding_supply = validate_candidate


def validate_candidate(candidate, *, prefix, runner_up=False):
    if isinstance(candidate, dict):
        supplied = supply_trusted_subject_grounding(
            candidate,
            trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
        # Preserve object identity for downstream callers that keep a reference
        # to the parsed Candidate dict. Private provenance is attached only by
        # the deterministic supplier above, never by model output.
        candidate.clear()
        candidate.update(supplied)
    return _original_validate_candidate_before_grounding_supply(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )
'''


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Canonical Subject Grounding Supply already applied")
        return
    if "CANONICAL_SUBJECT_GROUNDING_GATE_V1" not in text:
        raise RuntimeError("Canonical Subject Grounding Gate V1 must be installed first")
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ Canonical Subject Grounding Supply V1 applied")


if __name__ == "__main__":
    main()
