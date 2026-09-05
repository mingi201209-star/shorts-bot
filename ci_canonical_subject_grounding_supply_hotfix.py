from pathlib import Path


MARKER = "# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1"
EXPLORER_PATH = Path("content/candidate_explorer.py")
SUPPLY_PATH = Path("quality/canonical_subject_grounding_supply.py")
EXACT_CANONICAL_MARKER = "# RUN_33479576919_EXACT_CANONICAL_IDENTITY"
OVERLAP_MARKER = "# RUN_33479576919_DESCRIPTION_COVERAGE"


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
    result = _original_validate_explorer_output_before_grounding_supply(data)
    if not isinstance(result, dict) or str(result.get("status", "")).strip().upper() != "SELECTED":
        return result
    winner = result.get("winner")
    if isinstance(winner, dict):
        result["winner"] = supply_trusted_subject_grounding(
            winner, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
    runner_up = result.get("runner_up")
    if isinstance(runner_up, dict):
        result["runner_up"] = supply_trusted_subject_grounding(
            runner_up, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
    return result
'''


def _install_grounding_match_stability():
    text = SUPPLY_PATH.read_text(encoding="utf-8")

    if OVERLAP_MARKER not in text:
        old_overlap = '''def _overlap_ratio(left: str, right: str) -> float:\n    a = _phrase_tokens(left)\n    b = _phrase_tokens(right)\n    if not a or not b:\n        return 0.0\n    return len(a & b) / float(min(len(a), len(b)))\n'''
        new_overlap = '''def _overlap_ratio(left: str, right: str) -> float:\n    a = _phrase_tokens(left)\n    b = _phrase_tokens(right)\n    if not a or not b:\n        return 0.0\n    # RUN_33479576919_DESCRIPTION_COVERAGE\n    # Calls at this boundary are candidate_text -> authoritative description.\n    # Measure how much of the evidence-owned description is actually present;\n    # a short generic phrase such as "비행기 엔진" must not score 1.0 merely\n    # because every one of its few tokens appears in a richer description.\n    return len(a & b) / float(len(b))\n'''
        if old_overlap not in text:
            raise RuntimeError("canonical grounding overlap boundary changed")
        text = text.replace(old_overlap, new_overlap, 1)

    if EXACT_CANONICAL_MARKER not in text:
        old_match = '''    feature_match = any(\n        _overlap_ratio(candidate_text, _text(description)) >= 0.60\n        for description in feature_descriptions\n        if _text(description)\n    )\n'''
        new_match = '''    # RUN_33479576919_EXACT_CANONICAL_IDENTITY\n    # A fixed topic may already be the repo-owned canonical physical identity.\n    # Exact canonical identity is stronger than surface-description overlap and\n    # still inherits only this record's authoritative provenance.\n    canonical = _normalize(record.get("canonical_subject"))\n    if canonical and canonical in candidate_text:\n        return True\n\n    feature_match = any(\n        _overlap_ratio(candidate_text, _text(description)) >= 0.60\n        for description in feature_descriptions\n        if _text(description)\n    )\n'''
        if old_match not in text:
            raise RuntimeError("canonical grounding supply match boundary changed")
        text = text.replace(old_match, new_match, 1)

    SUPPLY_PATH.write_text(text, encoding="utf-8")


def main():
    _install_grounding_match_stability()
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Canonical Subject Grounding Supply already applied")
        return
    if "CANONICAL_SUBJECT_GROUNDING_GATE_V1" not in text:
        raise RuntimeError("Canonical Subject Grounding Gate V1 must be installed first")
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ Canonical Subject Grounding Supply V1 applied")


main()

# Run-specific extension: add only the FAA-backed physical identity needed by
# the fixed flap topic. The Gate, confidence floor, and fail-close behavior are
# unchanged. This rewrites the supply module before the next production process
# imports candidate_explorer and its trusted record tuple.
import ci_flap_canonical_grounding_hotfix
