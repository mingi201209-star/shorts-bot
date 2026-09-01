from pathlib import Path


MARKER = "# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1"
EXPLORER_PATH = Path("content/candidate_explorer.py")
SUPPLY_PATH = Path("quality/canonical_subject_grounding_supply.py")
EXACT_CANONICAL_MARKER = "# RUN_33479576919_EXACT_CANONICAL_IDENTITY"


PATCH = r'''

# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1
# Deterministic trusted provenance supplier. Runs after all model/schema repair
# output and before Candidate Gate evaluation. No API call or retry.
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)

_original_validate_explorer_output_before_grounding_supply = validate_explorer_output


def validate_explorer_output(data):
    # Let the complete production validation/repair/normalization chain finish
    # first. Earlier wrappers are allowed to rebuild Candidate dicts; supplying
    # trusted metadata before that point would be lost by those copies.
    result = _original_validate_explorer_output_before_grounding_supply(data)

    if not isinstance(result, dict) or str(result.get("status", "")).strip().upper() != "SELECTED":
        return result

    winner = result.get("winner")
    if isinstance(winner, dict):
        result["winner"] = supply_trusted_subject_grounding(
            winner,
            trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )

    runner_up = result.get("runner_up")
    if isinstance(runner_up, dict):
        result["runner_up"] = supply_trusted_subject_grounding(
            runner_up,
            trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )

    return result
'''


def _install_exact_canonical_identity_match():
    text = SUPPLY_PATH.read_text(encoding="utf-8")
    if EXACT_CANONICAL_MARKER in text:
        return
    old = '''    feature_match = any(\n        _overlap_ratio(candidate_text, _text(description)) >= 0.60\n        for description in feature_descriptions\n        if _text(description)\n    )\n'''
    new = '''    # RUN_33479576919_EXACT_CANONICAL_IDENTITY\n    # A fixed topic may already be the repo-owned canonical physical identity.\n    # Exact canonical identity is stronger than surface-description overlap and\n    # still inherits only this record's authoritative provenance.\n    canonical = _normalize(record.get("canonical_subject"))\n    if canonical and canonical in candidate_text:\n        return True\n\n    feature_match = any(\n        _overlap_ratio(candidate_text, _text(description)) >= 0.60\n        for description in feature_descriptions\n        if _text(description)\n    )\n'''
    if old not in text:
        raise RuntimeError("canonical grounding supply match boundary changed")
    SUPPLY_PATH.write_text(text.replace(old, new, 1), encoding="utf-8")


def main():
    _install_exact_canonical_identity_match()
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Canonical Subject Grounding Supply already applied")
        return
    if "CANONICAL_SUBJECT_GROUNDING_GATE_V1" not in text:
        raise RuntimeError("Canonical Subject Grounding Gate V1 must be installed first")
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ Canonical Subject Grounding Supply V1 applied")


# This installer is imported by the existing production Candidate hotfix chain.
# Execute on import so the production wiring actually installs the supplier.
main()
