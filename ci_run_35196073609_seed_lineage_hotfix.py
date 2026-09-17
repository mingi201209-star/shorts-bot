from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "# RUN_35196073609_SEED_LINEAGE_PRESERVATION_V1"

PATCH = r'''

# RUN_35196073609_SEED_LINEAGE_PRESERVATION_V1
# Authority: publish-stable Run 35196073609. A deterministic repo-owned
# spoiler seed survived Candidate Pool Handoff with its exact host-owned record
# identity, but the later generic Canonical Subject Grounding Supply wrapper
# re-matched its prose against PRODUCTION records and changed the canonical
# subject to the overlapping trailing-edge flap family before Writer.
#
# Preserve the existing trust boundary: only an in-process object reference
# that is literally one of the active trusted registry records may narrow this
# late resupply. Model/JSON candidates cannot forge Python object identity.
# Ordinary candidates keep the previous generic supply behavior unchanged.
#
# Some focused grounding regressions intentionally install canonical supply
# without installing Candidate Pool Handoff. Keep that supported composition:
# if the repo-owned seed capability is absent, this wrapper is a strict no-op.
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding
import quality.grounding_aware_candidate_supply as _run_35196073609_grounding_supply

_run_35196073609_previous_validate_explorer_output = validate_explorer_output


def _run_35196073609_restore_seed_identity(candidate):
    if not isinstance(candidate, dict):
        return candidate

    all_records_fn = getattr(
        _run_35196073609_grounding_supply,
        "all_trusted_candidate_records",
        None,
    )
    repo_record_fn = getattr(
        _run_35196073609_grounding_supply,
        "repo_owned_seed_trusted_record",
        None,
    )
    ref_field = getattr(
        _run_35196073609_grounding_supply,
        "REPO_OWNED_SEED_RECORD_REF_FIELD",
        "_repo_owned_seed_record_ref",
    )
    if not callable(all_records_fn) or not callable(repo_record_fn):
        return candidate

    trusted_records = all_records_fn()
    repo_seed_record = repo_record_fn(
        candidate,
        trusted_records=trusted_records,
    )
    if repo_seed_record is None:
        return candidate

    supplied = supply_trusted_subject_grounding(
        candidate,
        trusted_records=(repo_seed_record,),
    )
    supplied[ref_field] = repo_seed_record
    print(
        "[RUN_35196073609_SEED_LINEAGE] "
        "restored_exact_record canonical="
        f"{supplied.get('canonical_subject', '')}"
    )
    return supplied


def validate_explorer_output(data):
    result = _run_35196073609_previous_validate_explorer_output(data)
    if (
        not isinstance(result, dict)
        or str(result.get("status") or "").strip().upper() != "SELECTED"
    ):
        return result

    winner = result.get("winner")
    if isinstance(winner, dict):
        result["winner"] = _run_35196073609_restore_seed_identity(winner)

    runner_up = result.get("runner_up")
    if isinstance(runner_up, dict):
        result["runner_up"] = _run_35196073609_restore_seed_identity(runner_up)

    return result
'''


def main() -> None:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ Run 35196073609 seed-lineage preservation already applied")
        return
    if "CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1" not in text:
        raise RuntimeError(
            "Run 35196073609 seed-lineage hotfix requires canonical supply first"
        )
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print(
        "✅ Run 35196073609 deterministic seed lineage preserved after canonical supply; "
        "ordinary candidates and all quality/budget limits unchanged"
    )


main()
