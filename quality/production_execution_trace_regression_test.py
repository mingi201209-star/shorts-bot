from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.production_execution_trace import (
    fingerprint_file,
    input_fingerprint,
    record_event,
    snapshot_runtime_state,
    write_summary,
)
from quality.production_execution_trace_compare import compare


def main() -> None:
    old_diag = os.environ.get("SHORTS_DIAGNOSTICS_DIR")
    old_label = os.environ.get("SHORTS_TRACE_RUN_LABEL")
    old_append = os.environ.get("SHORTS_TRACE_APPEND")
    old_topic = os.environ.get("SHORTS_TOPIC")
    old_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    try:
        root = Path(tmp)
        os.chdir(root)
        os.environ["SHORTS_TOPIC"] = "trace fixture topic"

        run1 = root / "run1"
        run1.mkdir()
        os.environ["SHORTS_DIAGNOSTICS_DIR"] = str(run1)
        os.environ["SHORTS_TRACE_RUN_LABEL"] = "run1"
        os.environ.pop("SHORTS_TRACE_APPEND", None)
        Path("final_shorts_fixture.mp4").write_bytes(b"mp4-one")
        Path("final_visual_semantic_qa.json").write_text(
            json.dumps({"status": "PASS", "scenes": []}), encoding="utf-8"
        )
        Path("visual_diversity_preflight.json").write_text(
            json.dumps({"pass": True}), encoding="utf-8"
        )
        Path("final_director_qa.json").write_text(
            json.dumps({"overall_pass": True}), encoding="utf-8"
        )
        record_event("fixture_start", input=input_fingerprint())
        first_summary = write_summary("success")
        assert first_summary["runtime_state"]["final_mp4_candidates"][0]["sha256"] == fingerprint_file(
            "final_shorts_fixture.mp4"
        )["sha256"]

        run2 = root / "run2"
        run2.mkdir()
        os.environ["SHORTS_DIAGNOSTICS_DIR"] = str(run2)
        os.environ["SHORTS_TRACE_RUN_LABEL"] = "run2"
        os.environ.pop("SHORTS_TRACE_APPEND", None)
        record_event("fixture_start", input=input_fingerprint())
        second_summary = write_summary("success")
        assert second_summary["status"] == "success"

        same = compare(
            run1 / "production_execution_trace_summary.json",
            run2 / "production_execution_trace_summary.json",
        )
        assert same["status"] == "MATCH", same

        Path("final_shorts_fixture.mp4").write_bytes(b"mp4-two")
        run3 = root / "run3"
        run3.mkdir()
        os.environ["SHORTS_DIAGNOSTICS_DIR"] = str(run3)
        os.environ["SHORTS_TRACE_RUN_LABEL"] = "run3"
        record_event("fixture_start", input=input_fingerprint())
        write_summary("success")
        different = compare(
            run1 / "production_execution_trace_summary.json",
            run3 / "production_execution_trace_summary.json",
        )
        assert different["status"] == "DIFF", different
        assert "nondeterminism" in different["classifications"], different
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(tmp, ignore_errors=True)
        if old_diag is None:
            os.environ.pop("SHORTS_DIAGNOSTICS_DIR", None)
        else:
            os.environ["SHORTS_DIAGNOSTICS_DIR"] = old_diag
        if old_label is None:
            os.environ.pop("SHORTS_TRACE_RUN_LABEL", None)
        else:
            os.environ["SHORTS_TRACE_RUN_LABEL"] = old_label
        if old_append is None:
            os.environ.pop("SHORTS_TRACE_APPEND", None)
        else:
            os.environ["SHORTS_TRACE_APPEND"] = old_append
        if old_topic is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = old_topic
    print("PRODUCTION EXECUTION TRACE REGRESSION: PASS")


if __name__ == "__main__":
    main()
