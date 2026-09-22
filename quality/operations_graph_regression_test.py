"""Regression coverage for the Operations Graph V1 (operations/validate.py,
operations/query.py) and for AGENTS.md's existence/core-invariant presence.

All fixtures are synthetic, built in a temp directory per test -- nothing here reads or
depends on the real operations/incidents/*.json seed data, so a future edit to the seed
incidents cannot break this suite (and vice versa). No network access, no LLM call, no
external API of any kind.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.validate import validate_incidents_dir  # noqa: E402
from operations.query import load_incidents, _matches, _cmd_related  # noqa: E402

SCHEMA_PATH = ROOT / "operations" / "schema.json"


def _base_incident(**overrides) -> dict:
    incident = {
        "incident_id": "INC-2099-001-FIXTURE",
        "timestamp": "2099-01-01",
        "repository": "mingi201209-star/shorts-bot",
        "authority_main_sha": "1" * 40,
        "workflow": "example.yml",
        "run_id": 1000,
        "job_id": 2000,
        "failure_stage": "PROVIDER",
        "failure_signature": "RuntimeError: example failure",
        "symptoms": ["example symptom"],
        "root_cause": {
            "category": "PROVIDER_AVAILABILITY",
            "summary": "example root cause summary",
            "evidence": [{"kind": "run_id", "value": "1000"}],
        },
        "affected_files": ["example/file.py"],
        "fix": {
            "commits": ["a" * 40],
            "files": ["example/file.py"],
            "summary": "example fix summary",
        },
        "regressions": {
            "test_files": ["quality/example_regression_test.py"],
            "counterexample": "test_example",
            "result": "PASS",
        },
        "pull_requests": [{"number": 1, "status": "MERGED", "merge_commit": "b" * 40}],
        "verification": {
            "workflow_runs": [{"run_id": 1001, "job_id": 2001, "conclusion": "success"}],
            "result": "PASS",
            "verified_sha": "c" * 40,
        },
        "relationships": [],
        "status": "RESOLVED",
        "confidence": "VERIFIED",
    }
    incident.update(overrides)
    return incident


def _write_incidents(tmp_path: Path, incidents: list[dict]) -> Path:
    incidents_dir = tmp_path / "incidents"
    incidents_dir.mkdir()
    for incident in incidents:
        path = incidents_dir / f"{incident['incident_id']}.json"
        path.write_text(json.dumps(incident, ensure_ascii=False, indent=2), encoding="utf-8")
    return incidents_dir


def _validate(incidents: list[dict]):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        incidents_dir = _write_incidents(tmp_path, incidents)
        return validate_incidents_dir(incidents_dir, SCHEMA_PATH, base_dir=tmp_path)


# ---------------------------------------------------------------------------
# 1. valid VERIFIED incident -> PASS
# ---------------------------------------------------------------------------

def test_valid_verified_incident_passes():
    errors, count = _validate([_base_incident()])
    assert errors == [], errors
    assert count == 1


# ---------------------------------------------------------------------------
# 2. VERIFIED + no verification evidence -> FAIL
# ---------------------------------------------------------------------------

def test_verified_without_verification_evidence_fails():
    incident = _base_incident()
    incident["verification"] = {"workflow_runs": [], "result": "NOT_VERIFIED", "verified_sha": None}
    errors, _ = _validate([incident])
    assert any("missing verification evidence" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 3. VERIFIED + no fix commit -> FAIL
# ---------------------------------------------------------------------------

def test_verified_without_fix_commit_fails():
    incident = _base_incident()
    incident["fix"] = {"commits": [], "files": ["example/file.py"], "summary": "no commit yet"}
    errors, _ = _validate([incident])
    assert any("missing fix evidence" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 4. duplicate incident ID -> FAIL
# ---------------------------------------------------------------------------

def test_duplicate_incident_id_fails():
    first = _base_incident()
    second = _base_incident(timestamp="2099-02-01")
    # Same incident_id, different filename would normally be impossible since the
    # filename is derived from incident_id -- simulate the real failure mode instead:
    # two files whose incident_id field collides even though one's filename differs
    # (e.g. a copy-paste of an existing incident that forgot to change the id).
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        incidents_dir = tmp_path / "incidents"
        incidents_dir.mkdir()
        (incidents_dir / f"{first['incident_id']}.json").write_text(
            json.dumps(first, ensure_ascii=False), encoding="utf-8"
        )
        (incidents_dir / "INC-2099-001-FIXTURE-COPY.json").write_text(
            json.dumps(second, ensure_ascii=False), encoding="utf-8"
        )
        errors, _ = validate_incidents_dir(incidents_dir, SCHEMA_PATH, base_dir=tmp_path)
    assert any("duplicate incident_id" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 5. invalid SHA -> FAIL
# ---------------------------------------------------------------------------

def test_invalid_sha_fails():
    incident = _base_incident(authority_main_sha="not-a-real-sha")
    errors, _ = _validate([incident])
    assert any("malformed SHA" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 6. unknown relationship type -> FAIL
# ---------------------------------------------------------------------------

def test_unknown_relationship_type_fails():
    incident = _base_incident(
        relationships=[{"type": "CAUSED_MAGIC", "target_incident_id": "INC-2099-001-FIXTURE"}]
    )
    errors, _ = _validate([incident])
    assert any("relationships[0].type" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 7. dangling relationship -> FAIL
# ---------------------------------------------------------------------------

def test_dangling_relationship_fails():
    incident = _base_incident(
        relationships=[{"type": "RELATED_TO", "target_incident_id": "INC-2099-999-NOWHERE"}]
    )
    errors, _ = _validate([incident])
    assert any("dangling" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 8. PARTIAL incident -> allowed-missing-field policy
# ---------------------------------------------------------------------------

def test_partial_incident_allows_missing_fix_and_regression_and_verification():
    incident = _base_incident(
        confidence="PARTIAL",
        status="OPEN",
        fix={"commits": [], "files": [], "summary": "not yet fixed"},
        regressions={"test_files": [], "counterexample": None, "result": None},
        verification={"workflow_runs": [], "result": "NOT_VERIFIED", "verified_sha": None},
    )
    errors, count = _validate([incident])
    assert errors == [], errors
    assert count == 1


def test_partial_incident_still_requires_failure_signature_and_root_cause():
    incident = _base_incident(
        confidence="PARTIAL",
        status="OPEN",
        failure_signature="",
        fix={"commits": [], "files": [], "summary": ""},
        regressions={"test_files": [], "counterexample": None, "result": None},
        verification={"workflow_runs": [], "result": "NOT_VERIFIED", "verified_sha": None},
    )
    errors, _ = _validate([incident])
    assert any("PARTIAL but failure_signature is empty" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 9. query by failure signature -> expected incident
# ---------------------------------------------------------------------------

def test_query_by_failure_signature_finds_expected_incident():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target = _base_incident(failure_signature="RuntimeError: needle failure XYZ")
        other = _base_incident(
            incident_id="INC-2099-002-OTHER",
            failure_signature="AssertionError: unrelated",
        )
        incidents_dir = _write_incidents(tmp_path, [target, other])
        incidents = load_incidents(incidents_dir)

        class Args:
            incident_id = None
            failure_signature = "needle failure"
            file = None
            root_cause = None
            status = None
            confidence = None

        matches = [i for i in incidents if _matches(i, Args())]
    assert [m["incident_id"] for m in matches] == ["INC-2099-001-FIXTURE"]


# ---------------------------------------------------------------------------
# 10. query by affected file -> expected incident
# ---------------------------------------------------------------------------

def test_query_by_affected_file_finds_expected_incident():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target = _base_incident(affected_files=["video/video_engine.py"])
        other = _base_incident(
            incident_id="INC-2099-002-OTHER", affected_files=["content/script_generator.py"]
        )
        incidents_dir = _write_incidents(tmp_path, [target, other])
        incidents = load_incidents(incidents_dir)

        class Args:
            incident_id = None
            failure_signature = None
            file = "video/video_engine.py"
            root_cause = None
            status = None
            confidence = None

        matches = [i for i in incidents if _matches(i, Args())]
    assert [m["incident_id"] for m in matches] == ["INC-2099-001-FIXTURE"]


# ---------------------------------------------------------------------------
# 11. related incident traversal -> expected relationships
# ---------------------------------------------------------------------------

def test_related_traversal_finds_outgoing_and_incoming_edges(capsys):
    a = _base_incident(
        incident_id="INC-2099-001-FIXTURE",
        relationships=[{"type": "REGRESSION_OF", "target_incident_id": "INC-2099-002-OTHER"}],
    )
    b = _base_incident(incident_id="INC-2099-002-OTHER", relationships=[])
    c = _base_incident(
        incident_id="INC-2099-003-THIRD",
        relationships=[{"type": "RELATED_TO", "target_incident_id": "INC-2099-001-FIXTURE"}],
    )
    incidents = [a, b, c]

    exit_code = _cmd_related(incidents, "INC-2099-001-FIXTURE")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "INC-2099-001-FIXTURE --REGRESSION_OF--> INC-2099-002-OTHER" in out
    assert "INC-2099-003-THIRD --RELATED_TO--> INC-2099-001-FIXTURE" in out


# ---------------------------------------------------------------------------
# 12. AGENTS.md exists and contains the core safety invariants
# ---------------------------------------------------------------------------

def test_agents_md_exists_and_contains_core_invariants():
    agents_md = ROOT / "AGENTS.md"
    assert agents_md.exists(), "AGENTS.md must exist at the repository root"
    text = agents_md.read_text(encoding="utf-8")

    required_phrases = [
        "MUST NOT",
        "create_scene",
        "protected landing",
        "LAND-APPROVED",
        "YouTube",
        "Jev",
        "evidence",
        "operations/",
    ]
    for phrase in required_phrases:
        assert phrase in text, f"AGENTS.md missing expected phrase: {phrase!r}"


if __name__ == "__main__":
    import traceback

    tests = [
        (name, obj)
        for name, obj in list(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failures = 0
    for name, fn in tests:
        try:
            if "capsys" in fn.__code__.co_varnames[: fn.__code__.co_argcount]:
                # capsys is a pytest fixture; provide a minimal stand-in when run
                # directly as a script (python quality/operations_graph_regression_test.py)
                # instead of via pytest.
                import io
                import contextlib

                class _FakeCapsys:
                    def readouterr(self):
                        return _Captured(buf.getvalue())

                class _Captured:
                    def __init__(self, out):
                        self.out = out

                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    fn(_FakeCapsys())
            else:
                fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
