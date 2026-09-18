"""Publish the generator's failure diagnosis into the GitHub job summary.

Why this exists: on 2026-09-18 every one of the 17 failed Shorts Generator
dispatch runs died in 49-338s with no `final_shorts_*.mp4`, i.e. before render.
Which gate killed each run is recorded in `artifacts/diagnostics/`, but reading
it means downloading the `production-diagnostics-*` artifact by hand. Actions
logs and artifacts are served from blob storage, so an agent working through the
GitHub API cannot reach them at all -- only step conclusions are visible, which
say "Run Shorts Generator V3.2: failure" and nothing more.

A job summary IS exposed through the check-run API, so writing the diagnosis
there makes every future failure diagnosable without downloading anything.

Ordering matters: a check-run reader pages `output.text` in small windows, so the
exception, the budget counters and the progress stage come first and the bounded
traceback tail last.

Secrets: `diagnostics/failure_diagnostics` already redacts through
`_sanitize_value` / `redact_text` before writing these files. This module applies
`redact_text` again to everything it emits, as defence in depth, and never reads
the environment or the full generator log.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from diagnostics.failure_diagnostics import (
    FAILURE_SUMMARY_PATH,
    PROGRESS_PATH,
    SCENE_TRACE_PATH,
    TRACEBACK_PATH,
    redact_text,
)

#: Keep the traceback tail inside a couple of check-run text windows.
MAX_TRACEBACK_BYTES = 4000
#: Last N scene-trace records to echo.
MAX_TRACE_RECORDS = 5
#: Hard ceiling for the whole summary, far below GitHub's 1 MiB job-summary cap.
MAX_SUMMARY_BYTES = 60000

#: Emitted first, in this order: the answer, then the budget, then where it got to.
_SUMMARY_FIELDS = [
    ("exception_type", "Exception"),
    ("exception_message", "Message"),
    ("api_calls_used", "API calls used"),
    ("api_calls_limit", "API call limit"),
    ("openai_cost_usd", "Cost (USD)"),
    ("cost_limit_usd", "Cost limit (USD)"),
    ("last_scene_index", "Last scene index"),
    ("last_scene_role", "Last scene role"),
    ("last_source_type", "Last source type"),
    ("ai_video_enabled", "AI visual fallback enabled"),
]

_PROGRESS_FIELDS = [
    ("current_stage", "Current stage"),
    ("last_completed_stage", "Last completed stage"),
    ("retrieval_stage", "Retrieval stage"),
    ("director_stage", "Director stage"),
]


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cell(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    # Pipes would break the markdown table; newlines would break the row.
    return redact_text(str(value)).replace("|", "\\|").replace("\n", " ")[:300] or "-"


def _table(rows) -> list[str]:
    out = ["| field | value |", "| --- | --- |"]
    out += [f"| {label} | {_cell(value)} |" for label, value in rows]
    return out


def _traceback_tail() -> list[str]:
    try:
        text = TRACEBACK_PATH.read_text(encoding="utf-8")
    except Exception:
        return []
    raw = text.encode("utf-8")
    truncated = len(raw) > MAX_TRACEBACK_BYTES
    if truncated:
        text = raw[-MAX_TRACEBACK_BYTES:].decode("utf-8", errors="replace")
    head = f"### Traceback ({'tail, ' if truncated else ''}{len(raw)} bytes)"
    return ["", head, "", "```", redact_text(text).rstrip(), "```"]


def _scene_trace_tail() -> list[str]:
    try:
        lines = SCENE_TRACE_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    tail = [line for line in lines if line.strip()][-MAX_TRACE_RECORDS:]
    if not tail:
        return []
    return ["", f"### Last {len(tail)} scene trace records", "", "```"] + [
        redact_text(line)[:500] for line in tail
    ] + ["```"]


def build_summary() -> str:
    summary = _read_json(FAILURE_SUMMARY_PATH)
    progress = _read_json(PROGRESS_PATH)

    if not isinstance(summary, dict):
        # Success, or the generator died before it could write a summary.
        lines = ["## Generator diagnostics", ""]
        if isinstance(progress, dict):
            lines.append(
                "No failure summary was written. Progress at exit:"
            )
            lines += [""] + _table(
                [(label, progress.get(key)) for key, label in _PROGRESS_FIELDS]
            )
        else:
            lines.append(
                "No failure summary and no progress file: the generator did not "
                "reach `initialize_progress()`."
            )
        return "\n".join(lines) + "\n"

    lines = ["## Generator failure diagnosis", ""]
    lines += _table([(label, summary.get(key)) for key, label in _SUMMARY_FIELDS])

    if isinstance(progress, dict):
        lines += ["", "### Progress at failure", ""]
        lines += _table([(label, progress.get(key)) for key, label in _PROGRESS_FIELDS])

    lines += _scene_trace_tail()
    lines += _traceback_tail()

    text = "\n".join(lines) + "\n"
    if len(text.encode("utf-8")) > MAX_SUMMARY_BYTES:
        text = text.encode("utf-8")[:MAX_SUMMARY_BYTES].decode("utf-8", errors="replace")
        text += "\n\n_[summary truncated]_\n"
    return text


def main() -> int:
    text = build_summary()
    target = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if target:
        try:
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(text)
        except Exception as exc:
            # Never let diagnostics reporting change a job's conclusion.
            print(f"[STEP_SUMMARY] could not write job summary: {type(exc).__name__}")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
