"""Regression for publishing the generator's failure diagnosis to the job summary.

Counterexample: on 2026-09-18 all 17 failed Shorts Generator dispatch runs died
before render (no `final_shorts_*.mp4`, 49-338s). The step conclusions readable
through the GitHub API say only "Run Shorts Generator V3.2: failure"; the gate
that actually killed each run sits in `artifacts/diagnostics/`, reachable only by
downloading the artifact. These cases pin that the diagnosis reaches the job
summary instead, that it stays redacted and bounded, and that `main.yml` runs it
unconditionally.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load(root: Path):
    os.environ["SHORTS_DIAGNOSTICS_DIR"] = str(root)
    import diagnostics.failure_diagnostics as fd
    import diagnostics.step_summary as ss
    importlib.reload(fd)
    importlib.reload(ss)
    return ss


def _write(root: Path, name: str, payload) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def case_budget_failure_leads_with_exception_and_counters():
    """The decisive facts must land in the first check-run text window."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "failure_summary.json", {
            "exception_type": "BudgetExceededError",
            "exception_message": "V3 API 비용 한도 초과: $0.052000/$0.050000",
            "api_calls_used": 7, "api_calls_limit": 60,
            "openai_cost_usd": 0.052, "cost_limit_usd": 0.05,
            "last_scene_index": None, "last_scene_role": None,
        })
        ss = _load(root)
        text = ss.build_summary()
        head = text.encode("utf-8")[:8192].decode("utf-8", errors="replace")
        for needle in ("BudgetExceededError", "0.052", "0.05", "60"):
            assert needle in head, f"{needle!r} must appear in the first window"
        assert "한도 초과" in head, "the original message must survive verbatim"
    print("CASE A budget failure leads with exception and counters: PASS")


def case_gate_failure_reports_stage_and_scene():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "failure_summary.json", {
            "exception_type": "RuntimeError",
            "exception_message": "Candidate Gate를 통과하는 Winner를 확보하지 못했습니다.",
            "last_scene_index": 3, "last_scene_role": "payoff",
        })
        _write(root, "progress.json", {
            "current_stage": "candidate_gate", "last_completed_stage": "candidate_explorer",
            "retrieval_stage": None, "director_stage": None,
        })
        ss = _load(root)
        text = ss.build_summary()
        assert "RuntimeError" in text and "Candidate Gate" in text
        assert "candidate_gate" in text and "candidate_explorer" in text
        assert "payoff" in text
    print("CASE B gate failure reports stage and scene: PASS")


def case_no_failure_summary_falls_back_to_progress():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "progress.json", {"current_stage": "completed",
                                        "last_completed_stage": "generator",
                                        "retrieval_stage": None, "director_stage": None})
        ss = _load(root)
        text = ss.build_summary()
        assert "No failure summary" in text and "completed" in text
    print("CASE C success path falls back to progress: PASS")


def case_no_files_at_all_is_explicit():
    with tempfile.TemporaryDirectory() as tmp:
        ss = _load(Path(tmp))
        text = ss.build_summary()
        assert "initialize_progress" in text, (
            "dying before initialize_progress must be stated, not rendered as an empty table"
        )
    print("CASE D missing diagnostics is stated explicitly: PASS")


def case_secrets_are_redacted_and_tables_survive_pipes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        secret = "sk-proj-abcdefghijklmnop0123456789"
        os.environ["OPENAI_KEY"] = secret
        try:
            _write(root, "failure_summary.json", {
                "exception_type": "RuntimeError",
                "exception_message": "boom | pipe\nand newline",
            })
            _write(root, "traceback.txt", f"Traceback...\nAuthorization: Bearer {secret}\n")
            ss = _load(root)
            text = ss.build_summary()
            assert secret not in text, "a secret must never reach the job summary"
            # One table row must stay one line.
            row = [l for l in text.splitlines() if l.startswith("| Message |")]
            assert len(row) == 1 and "and newline" in row[0], "newlines must not break the row"
            assert "\\|" in row[0], "pipes must be escaped"
        finally:
            os.environ.pop("OPENAI_KEY", None)
    print("CASE E secrets redacted, table rows intact: PASS")


def case_large_traceback_is_bounded():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "failure_summary.json", {"exception_type": "RuntimeError",
                                              "exception_message": "x"})
        _write(root, "traceback.txt", "L" * 500000)
        ss = _load(root)
        text = ss.build_summary()
        assert len(text.encode("utf-8")) <= ss.MAX_SUMMARY_BYTES, "summary must stay bounded"
        assert "tail," in text, "a truncated traceback must say so"
    print("CASE F oversized traceback is bounded: PASS")


def case_main_workflow_runs_the_step_unconditionally():
    workflow = (REPO_ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    assert "python -m diagnostics.step_summary" in workflow, (
        "main.yml must publish the diagnosis to the job summary"
    )
    step = workflow.split("python -m diagnostics.step_summary", 1)[0]
    tail = step[step.rfind("- name:"):]
    assert "if: always()" in tail or "if: ${{ always() }}" in tail, (
        "the summary step must run on failure, which is the case it exists for"
    )
    # It must not be able to fail the job it is diagnosing.
    assert "continue-on-error: true" in tail, (
        "diagnostics reporting must never change a job's conclusion"
    )
    print("CASE G main.yml runs the step unconditionally: PASS")


if __name__ == "__main__":
    case_budget_failure_leads_with_exception_and_counters()
    case_gate_failure_reports_stage_and_scene()
    case_no_failure_summary_falls_back_to_progress()
    case_no_files_at_all_is_explicit()
    case_secrets_are_redacted_and_tables_survive_pipes()
    case_large_traceback_is_bounded()
    case_main_workflow_runs_the_step_unconditionally()
    print("step summary regression: PASS")
