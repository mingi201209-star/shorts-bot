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

# Run-specific extensions: retain the previous FAA-backed flap record for the
# separate trailing-edge flap family, and add the FAA-backed static-discharge
# wick identity for the exact wing-tip small-rod observation. The Gate,
# confidence floor, and fail-close behavior are unchanged.
import ci_flap_canonical_grounding_hotfix
import ci_static_wick_canonical_grounding_hotfix

# Candidate retries can replace the validated winner object after Explorer
# supply has already run. Re-supply the same repo-owned provenance immediately
# before the existing pre-Writer fail-close gate.
import ci_prewriter_grounding_resupply_hotfix


# Run 35193333727 repeatedly produced otherwise concrete aviation Candidates
# that arrived at the host canonical-grounding boundary without a complete
# model-authored identity envelope. Backport only the already-proven PR #386
# output contract and missing-kind normalization. This does not invent a
# canonical subject, trust model-authored sources, relax the grounding Gate, or
# add an API call/retry.
POST_MARKER = "# RUN_35193333727_GROUNDING_OUTPUT_V1"
POST_PATCH = r'''

# RUN_35193333727_GROUNDING_OUTPUT_V1
CANDIDATE_EXPLORER_PROMPT += r"""

============================================================
RUN 35193333727 — REQUIRED GROUNDING OUTPUT CONTRACT
============================================================
For every SELECTED winner and runner_up, the following four fields are
MANDATORY and must not be omitted:
- subject_kind
- canonical_subject
- subject_identity_confidence
- grounding_evidence

If the subject is a named physical entity already explicit in the Candidate
story, preserve that exact explicit name as canonical_subject and use only
explicit_candidate_identity evidence that points back to the Candidate text.
If physical identity is genuinely unresolved, return canonical_subject=UNKNOWN
with confidence 0.0 and empty grounding_evidence. Never invent an identity,
source, or mechanism merely to fill these fields.
"""

_run_35193333727_previous_validate_candidate = validate_candidate


def _run_35193333727_candidate_text(candidate):
    if not isinstance(candidate, dict):
        return ""
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}
    values = (
        candidate.get("topic"),
        candidate.get("angle"),
        candidate.get("core_question"),
        micro.get("hook"),
        micro.get("core_question"),
        micro.get("reveal"),
        micro.get("payoff"),
    )
    return " ".join(str(value or "").strip() for value in values).lower()


def validate_candidate(candidate, *, prefix, runner_up=False):
    result = _run_35193333727_previous_validate_candidate(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )
    if result.get("subject_kind") in (
        "physical_entity",
        "non_physical_concept",
    ):
        return result

    raw = normalize_candidate_subject_metadata(candidate)
    canonical = str(raw.get("canonical_subject") or "").strip()
    canonical_key = " ".join(canonical.lower().split())
    confidence = float(raw.get("subject_identity_confidence") or 0.0)
    evidence = raw.get("grounding_evidence") or []

    if canonical_key == "not_applicable" and confidence >= 1.0:
        raw["subject_kind"] = "non_physical_concept"
        result.update(raw)
        return result

    unknown = {"", "unknown", "unresolved", "none", "null", "n/a"}
    candidate_text = _run_35193333727_candidate_text(candidate)
    explicit_support = any(
        isinstance(item, dict)
        and str(item.get("evidence_type") or "").strip().lower()
            == "explicit_candidate_identity"
        and " ".join(str(item.get("supports_subject") or "").strip().lower().split())
            == canonical_key
        for item in evidence
    )

    if (
        canonical_key not in unknown
        and canonical_key in candidate_text
        and explicit_support
    ):
        raw["subject_kind"] = "physical_entity"
        result.update(raw)
        print(
            "🧭 CANONICAL_SUBJECT_KIND normalized from explicit Candidate identity "
            f"canonical={canonical}"
        )

    return result
'''


post_text = EXPLORER_PATH.read_text(encoding="utf-8")
if POST_MARKER in post_text:
    print("ℹ️ Run 35193333727 grounding-output compatibility already applied")
else:
    EXPLORER_PATH.write_text(post_text.rstrip() + POST_PATCH + "\n", encoding="utf-8")
    print(
        "✅ Run 35193333727 explicit grounding output + missing-kind "
        "normalization applied; Gate and limits unchanged"
    )
