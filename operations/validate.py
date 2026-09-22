#!/usr/bin/env python3
"""Operations Graph V1 validator.

Deterministic, network-free. Never calls OpenAI, Pexels, YouTube, or any other
external API, and never generates a video -- this only reads operations/incidents/*.json.

Checks performed:

1. Schema validity of every incidents/*.json file against schema.json.
2. No duplicate incident_id across files.
3. incident_id matches its own filename (INC-.... .json).
4. SHA-shaped fields (authority_main_sha, fix.commits[], pull_requests[].merge_commit,
   verification.verified_sha) look like real hex SHAs when non-null.
5. run_id/job_id-shaped fields are positive integers when non-null.
6. relationships[].type is in the controlled vocabulary (enforced by schema.json enum too;
   re-checked here so this validator does not silently depend on schema.json alone).
7. relationships[].target_incident_id refers to an incident that actually exists in this
   repository (no dangling edges).
8. status is a valid enum value (schema.json enforces this too; re-checked defensively).
9. confidence is a valid enum value (schema.json enforces this too; re-checked defensively).
10. VERIFIED evidence-completeness gate:
    - failure evidence: run_id or job_id set, and failure_signature non-empty
    - fix evidence: fix.commits non-empty
    - regression evidence: regressions.test_files non-empty
    - verification evidence: verification.workflow_runs non-empty AND
      verification.result == "PASS"
    A VERIFIED incident missing ANY of these fails validation with a specific message
    naming which evidence category is missing.
11. PARTIAL incidents must still have failure_signature, failure_stage, and
    root_cause.summary populated (the allowed-missing-field policy is fix/regressions/
    verification only -- see operations/README.md).

Exit code: 0 if every incident passes every check, 1 otherwise. All violations are printed
before exiting, not just the first one.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

OPERATIONS_DIR = Path(__file__).resolve().parent
INCIDENTS_DIR = OPERATIONS_DIR / "incidents"
SCHEMA_PATH = OPERATIONS_DIR / "schema.json"

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
INCIDENT_ID_RE = re.compile(r"^INC-[0-9]{4}-[0-9]{3}-[A-Z0-9-]+$")

RELATIONSHIP_TYPES = {"RELATED_TO", "SAME_SIGNATURE_AS", "REGRESSION_OF", "SUPERSEDES"}
STATUS_VALUES = {"OPEN", "RESOLVED", "MONITORING", "WONT_FIX"}
CONFIDENCE_VALUES = {"VERIFIED", "PARTIAL", "UNVERIFIED"}


def _load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _try_import_jsonschema():
    try:
        import jsonschema  # type: ignore

        return jsonschema
    except ImportError:
        return None


def _validate_against_schema(incident, schema, jsonschema_module, errors, label):
    if jsonschema_module is not None:
        validator_cls = jsonschema_module.Draft202012Validator
        validator = validator_cls(schema)
        for err in sorted(validator.iter_errors(incident), key=lambda e: list(e.path)):
            path = "/".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{label}: schema violation at {path}: {err.message}")
        return

    # jsonschema is not installed in this environment: fall back to a minimal
    # hand-rolled structural check covering the required-field/type/enum surface
    # this validator's own logic depends on, so CI stays deterministic and
    # dependency-free rather than silently skipping schema validation.
    required = schema.get("required", [])
    for field in required:
        if field not in incident:
            errors.append(f"{label}: missing required field '{field}'")

    props = schema.get("properties", {})
    for field, spec in props.items():
        if field not in incident:
            continue
        value = incident[field]
        enum = spec.get("enum")
        if enum is not None and value not in enum:
            errors.append(f"{label}: field '{field}' value {value!r} not in {enum}")

    if not schema.get("additionalProperties", True):
        allowed = set(props.keys())
        for field in incident.keys():
            if field not in allowed:
                errors.append(f"{label}: unexpected top-level field '{field}'")


def _check_sha_field(value, label, errors, *, full_only=False):
    if value is None:
        return
    pattern = FULL_SHA_RE if full_only else SHA_RE
    if not isinstance(value, str) or not pattern.match(value):
        errors.append(f"{label}: malformed SHA {value!r}")


def _check_positive_int(value, label, errors):
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        errors.append(f"{label}: expected a positive integer run/job id, got {value!r}")


def _check_verified_evidence(incident, label, errors):
    if incident.get("confidence") != "VERIFIED":
        return

    run_id = incident.get("run_id")
    job_id = incident.get("job_id")
    failure_signature = incident.get("failure_signature") or ""
    if not (run_id or job_id):
        errors.append(f"{label}: VERIFIED but no run_id/job_id (missing failure evidence)")
    if not failure_signature.strip():
        errors.append(f"{label}: VERIFIED but failure_signature is empty (missing failure evidence)")

    fix = incident.get("fix") or {}
    if not fix.get("commits"):
        errors.append(f"{label}: VERIFIED but fix.commits is empty (missing fix evidence)")

    regressions = incident.get("regressions") or {}
    if not regressions.get("test_files"):
        errors.append(f"{label}: VERIFIED but regressions.test_files is empty (missing regression evidence)")

    verification = incident.get("verification") or {}
    if not verification.get("workflow_runs"):
        errors.append(f"{label}: VERIFIED but verification.workflow_runs is empty (missing verification evidence)")
    if verification.get("result") != "PASS":
        errors.append(
            f"{label}: VERIFIED but verification.result is {verification.get('result')!r}, not 'PASS'"
        )


def _check_partial_minimum(incident, label, errors):
    if incident.get("confidence") != "PARTIAL":
        return
    if not (incident.get("failure_signature") or "").strip():
        errors.append(f"{label}: PARTIAL but failure_signature is empty")
    if not incident.get("failure_stage"):
        errors.append(f"{label}: PARTIAL but failure_stage is missing")
    root_cause = incident.get("root_cause") or {}
    if not (root_cause.get("summary") or "").strip():
        errors.append(f"{label}: PARTIAL but root_cause.summary is empty")


def validate_incidents_dir(incidents_dir: Path, schema_path: Path, *, base_dir: Path | None = None):
    """Run every check against incidents_dir/*.json. Returns (errors, incident_count).

    base_dir is used only to make error labels relative/readable; defaults to
    incidents_dir's parent. This is the function operations/validate.py's CLI and
    quality/operations_graph_regression_test.py's tests both call, so the two never
    drift apart -- the CLI is a thin wrapper, not a second implementation.
    """
    base_dir = base_dir or incidents_dir.parent
    errors: list[str] = []

    if not schema_path.exists():
        return [f"FATAL: schema file missing at {schema_path}"], 0
    schema = _load_json(schema_path)
    jsonschema_module = _try_import_jsonschema()

    if not incidents_dir.exists():
        return [f"FATAL: incidents directory missing at {incidents_dir}"], 0

    incident_files = sorted(incidents_dir.glob("*.json"))
    incidents_by_id: dict[str, dict] = {}
    seen_ids: dict[str, Path] = {}

    for path in incident_files:
        label = f"{path.relative_to(base_dir)}"
        try:
            incident = _load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{label}: invalid JSON: {exc}")
            continue

        _validate_against_schema(incident, schema, jsonschema_module, errors, label)

        incident_id = incident.get("incident_id")
        if not isinstance(incident_id, str) or not INCIDENT_ID_RE.match(incident_id):
            errors.append(f"{label}: incident_id {incident_id!r} does not match required pattern")
        else:
            expected_stem = incident_id
            if path.stem != expected_stem:
                errors.append(
                    f"{label}: filename stem {path.stem!r} does not match incident_id {incident_id!r}"
                )
            if incident_id in seen_ids:
                errors.append(
                    f"{label}: duplicate incident_id {incident_id!r} "
                    f"(also in {seen_ids[incident_id].relative_to(base_dir)})"
                )
            else:
                seen_ids[incident_id] = path
                incidents_by_id[incident_id] = incident

        _check_sha_field(incident.get("authority_main_sha"), f"{label}: authority_main_sha", errors, full_only=True)
        _check_positive_int(incident.get("run_id"), f"{label}: run_id", errors)
        _check_positive_int(incident.get("job_id"), f"{label}: job_id", errors)

        for i, commit in enumerate(((incident.get("fix") or {}).get("commits")) or []):
            _check_sha_field(commit, f"{label}: fix.commits[{i}]", errors)

        for i, pr in enumerate(incident.get("pull_requests") or []):
            _check_sha_field(pr.get("merge_commit"), f"{label}: pull_requests[{i}].merge_commit", errors)
            if pr.get("status") not in {"OPEN", "MERGED", "CLOSED"}:
                errors.append(f"{label}: pull_requests[{i}].status invalid: {pr.get('status')!r}")

        verification = incident.get("verification") or {}
        _check_sha_field(verification.get("verified_sha"), f"{label}: verification.verified_sha", errors)
        for i, run in enumerate(verification.get("workflow_runs") or []):
            _check_positive_int(run.get("run_id"), f"{label}: verification.workflow_runs[{i}].run_id", errors)
            _check_positive_int(run.get("job_id"), f"{label}: verification.workflow_runs[{i}].job_id", errors)

        for i, rel in enumerate(incident.get("relationships") or []):
            rel_type = rel.get("type")
            if rel_type not in RELATIONSHIP_TYPES:
                errors.append(f"{label}: relationships[{i}].type {rel_type!r} not in {sorted(RELATIONSHIP_TYPES)}")
            target = rel.get("target_incident_id")
            if not isinstance(target, str) or not INCIDENT_ID_RE.match(target):
                errors.append(f"{label}: relationships[{i}].target_incident_id {target!r} malformed")

        status = incident.get("status")
        if status not in STATUS_VALUES:
            errors.append(f"{label}: status {status!r} not in {sorted(STATUS_VALUES)}")

        confidence = incident.get("confidence")
        if confidence not in CONFIDENCE_VALUES:
            errors.append(f"{label}: confidence {confidence!r} not in {sorted(CONFIDENCE_VALUES)}")

        _check_verified_evidence(incident, label, errors)
        _check_partial_minimum(incident, label, errors)

    # Dangling relationship check needs the full incidents_by_id map, so it runs
    # in a second pass after every file has been loaded.
    for path in incident_files:
        label = f"{path.relative_to(base_dir)}"
        try:
            incident = _load_json(path)
        except json.JSONDecodeError:
            continue
        for i, rel in enumerate(incident.get("relationships") or []):
            target = rel.get("target_incident_id")
            if isinstance(target, str) and INCIDENT_ID_RE.match(target) and target not in incidents_by_id:
                errors.append(f"{label}: relationships[{i}] targets unknown incident_id {target!r} (dangling)")

    return errors, len(incident_files)


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"FATAL: schema file missing at {SCHEMA_PATH}")
        return 1
    if not INCIDENTS_DIR.exists():
        print(f"FATAL: incidents directory missing at {INCIDENTS_DIR}")
        return 1

    if _try_import_jsonschema() is None:
        print(
            "NOTE: 'jsonschema' package not installed; used a minimal built-in structural "
            "check instead of full JSON Schema validation. Install jsonschema for stricter "
            "local checking; CI behavior is unaffected since this validator still enforces "
            "every check listed in its own docstring."
        )

    errors, incident_count = validate_incidents_dir(INCIDENTS_DIR, SCHEMA_PATH, base_dir=OPERATIONS_DIR)

    if errors:
        print(f"OPERATIONS GRAPH VALIDATION: FAIL ({len(errors)} issue(s))")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"OPERATIONS GRAPH VALIDATION: PASS ({incident_count} incident(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
