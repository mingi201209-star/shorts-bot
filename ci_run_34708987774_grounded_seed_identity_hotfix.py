from pathlib import Path
import subprocess
import sys


GROUNDING_PATH = Path("quality/grounding_aware_candidate_supply.py")
HANDOFF_PATH = Path("quality/candidate_pool_handoff.py")
GROUNDING_MARKER = "# RUN_34708987774_REPO_OWNED_SEED_IDENTITY_V1"
HANDOFF_MARKER = "# RUN_34708987774_REPO_OWNED_SEED_HANDOFF_V1"


def _patch_grounding_supply() -> None:
    text = GROUNDING_PATH.read_text(encoding="utf-8")
    if GROUNDING_MARKER in text:
        print("✅ Run 34708987774 repo-owned seed identity marker already installed")
        return

    seed_anchor = '''        grounded_seed["specific_observation"] = (
            f"{feature_phrase}. {context_phrase}."
        )
'''
    seed_replacement = '''        grounded_seed["specific_observation"] = (
            f"{feature_phrase}. {context_phrase}."
        )
        # RUN_34708987774_REPO_OWNED_SEED_IDENTITY_V1
        # This is an in-memory object reference, not model-visible provenance.
        # JSON/model output can copy the field name or record contents but cannot
        # reproduce object identity with one of the host's trusted registry records.
        grounded_seed[REPO_OWNED_SEED_RECORD_REF_FIELD] = record
'''
    if text.count(seed_anchor) != 1:
        raise RuntimeError(
            "Run 34708987774 grounding seed anchor mismatch: "
            f"{text.count(seed_anchor)}"
        )
    text = text.replace(seed_anchor, seed_replacement, 1)

    helper = r'''

# RUN_34708987774_REPO_OWNED_SEED_IDENTITY_V1
# Deterministic seeds are constructed in-process from a specific trusted record.
# Preserve that exact provenance as an object identity reference so Candidate Pool
# Handoff can NARROW trust to the originating record instead of asking the generic
# text matcher to choose among overlapping aviation records. This never broadens
# trust: only an object that is literally one of the active registry records is
# accepted. Model/JSON output cannot forge Python object identity.
REPO_OWNED_SEED_RECORD_REF_FIELD = "_repo_owned_seed_record_ref"


def repo_owned_seed_trusted_record(
    candidate: Dict[str, Any],
    *,
    trusted_records: Sequence[Dict[str, Any]],
) -> Dict[str, Any] | None:
    if not isinstance(candidate, dict):
        return None
    record_ref = candidate.get(REPO_OWNED_SEED_RECORD_REF_FIELD)
    if not isinstance(record_ref, dict):
        return None
    for record in trusted_records or ():
        if record_ref is record:
            return record
    return None
'''
    text = text.rstrip() + helper + "\n"
    GROUNDING_PATH.write_text(text, encoding="utf-8")
    print("✅ Run 34708987774 repo-owned seed identity provenance installed")


def _patch_candidate_pool_handoff() -> None:
    text = HANDOFF_PATH.read_text(encoding="utf-8")
    if HANDOFF_MARKER in text:
        print("✅ Run 34708987774 repo-owned seed handoff already installed")
        return

    import_anchor = '''from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
'''
    import_replacement = '''from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.grounding_aware_candidate_supply import (
    repo_owned_seed_trusted_record,
)
'''
    if text.count(import_anchor) != 1:
        raise RuntimeError(
            "Run 34708987774 handoff import anchor mismatch: "
            f"{text.count(import_anchor)}"
        )
    text = text.replace(import_anchor, import_replacement, 1)

    supply_anchor = '''        grounded = supply_trusted_subject_grounding(
            validated,
            trusted_records=combined_trusted_records,
        )
'''
    supply_replacement = '''        # RUN_34708987774_REPO_OWNED_SEED_HANDOFF_V1
        # A repo-owned deterministic seed already has an exact host-owned record
        # provenance. Restrict the supplier to that ONE record so broad text overlap
        # with another trusted aviation family cannot create a false ambiguity.
        # Ordinary model Candidate pools still use the unchanged full registry and
        # remain fail-closed on competing identities.
        repo_seed_record = repo_owned_seed_trusted_record(
            raw,
            trusted_records=combined_trusted_records,
        )
        candidate_trusted_records = (
            (repo_seed_record,)
            if repo_seed_record is not None
            else combined_trusted_records
        )
        if repo_seed_record is not None:
            diag["trusted_seed_scope"] = str(
                repo_seed_record.get("canonical_subject") or ""
            )

        grounded = supply_trusted_subject_grounding(
            validated,
            trusted_records=candidate_trusted_records,
        )
'''
    if text.count(supply_anchor) != 1:
        raise RuntimeError(
            "Run 34708987774 handoff supply anchor mismatch: "
            f"{text.count(supply_anchor)}"
        )
    text = text.replace(supply_anchor, supply_replacement, 1)
    HANDOFF_PATH.write_text(text, encoding="utf-8")
    print("✅ Run 34708987774 repo-owned seed handoff scoping installed")


def main() -> None:
    _patch_grounding_supply()
    _patch_candidate_pool_handoff()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "quality.run_34708987774_grounded_seed_identity_regression_test",
        ],
        check=True,
    )


# Production composition imports this installer from
# ci_grounding_aware_candidate_supply_hotfix.py. Execute on import so the on-disk
# runtime modules are actually patched before the generator starts.
main()
