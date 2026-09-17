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
# Important ordering detail from Run 35196073609: the generic supplier deep-copies
# its candidate before this outer wrapper receives the SELECTED result. The dict
# contents of the private ref survive that copy, but Python object identity does
# not. Therefore authenticate repo-owned seed capability on the INPUT payload,
# before calling the previous validator/supplier, and carry forward only that
# already-authenticated host record. A textual fingerprint is used only to bind
# the returned winner to that authenticated input. If a trusted seed has any
# same-fingerprint twin in the input pool, fail closed and grant no late scope.
#
# Some focused grounding regressions intentionally install canonical supply
# without installing Candidate Pool Handoff. Keep that supported composition:
# when the repo-owned seed capability helpers are absent, this wrapper is a
# strict no-op around the existing validator.
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding
import quality.grounding_aware_candidate_supply as _run_35196073609_grounding_supply

_run_35196073609_previous_validate_explorer_output = validate_explorer_output


def _run_35196073609_seed_fingerprint(candidate):
    if not isinstance(candidate, dict):
        return None
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    def _norm(value):
        return " ".join(str(value or "").strip().split())

    return (
        _norm(candidate.get("topic")),
        _norm(candidate.get("angle")),
        _norm(candidate.get("core_question")),
        _norm(micro.get("hook")),
        _norm(micro.get("core_question")),
        _norm(micro.get("reveal")),
        _norm(micro.get("payoff")),
    )


def _run_35196073609_registry_helpers():
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
        return None, None, ref_field
    return all_records_fn, repo_record_fn, ref_field


def _run_35196073609_input_candidates(data):
    if not isinstance(data, dict):
        return []
    status = str(data.get("status") or "").strip().upper()
    if status == "CANDIDATE_POOL":
        candidates = data.get("candidates") or []
        return [item for item in candidates if isinstance(item, dict)]
    if status == "SELECTED":
        return [
            item
            for item in (data.get("winner"), data.get("runner_up"))
            if isinstance(item, dict)
        ]
    return []


def _run_35196073609_capture_authenticated_seed_records(data):
    all_records_fn, repo_record_fn, _ = _run_35196073609_registry_helpers()
    if not callable(all_records_fn) or not callable(repo_record_fn):
        return {}

    trusted_records = all_records_fn()
    buckets = {}
    for candidate in _run_35196073609_input_candidates(data):
        fingerprint = _run_35196073609_seed_fingerprint(candidate)
        if fingerprint is None:
            continue
        bucket = buckets.setdefault(
            fingerprint,
            {"count": 0, "trusted_records": []},
        )
        bucket["count"] += 1
        repo_seed_record = repo_record_fn(
            candidate,
            trusted_records=trusted_records,
        )
        if repo_seed_record is not None:
            bucket["trusted_records"].append(repo_seed_record)

    captured = {}
    for fingerprint, bucket in buckets.items():
        records = bucket["trusted_records"]
        if bucket["count"] == 1 and len(records) == 1:
            captured[fingerprint] = records[0]
    return captured


def _run_35196073609_restore_seed_identity(candidate, repo_seed_record=None):
    if not isinstance(candidate, dict):
        return candidate

    all_records_fn, repo_record_fn, ref_field = _run_35196073609_registry_helpers()
    if not callable(all_records_fn) or not callable(repo_record_fn):
        return candidate

    trusted_records = all_records_fn()
    if repo_seed_record is None:
        repo_seed_record = repo_record_fn(
            candidate,
            trusted_records=trusted_records,
        )
    elif not any(repo_seed_record is record for record in trusted_records):
        return candidate

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
    authenticated_seed_records = (
        _run_35196073609_capture_authenticated_seed_records(data)
    )
    result = _run_35196073609_previous_validate_explorer_output(data)
    if (
        not isinstance(result, dict)
        or str(result.get("status") or "").strip().upper() != "SELECTED"
    ):
        return result

    winner = result.get("winner")
    if isinstance(winner, dict):
        record = authenticated_seed_records.get(
            _run_35196073609_seed_fingerprint(winner)
        )
        result["winner"] = _run_35196073609_restore_seed_identity(
            winner,
            repo_seed_record=record,
        )

    runner_up = result.get("runner_up")
    if isinstance(runner_up, dict):
        record = authenticated_seed_records.get(
            _run_35196073609_seed_fingerprint(runner_up)
        )
        result["runner_up"] = _run_35196073609_restore_seed_identity(
            runner_up,
            repo_seed_record=record,
        )

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
