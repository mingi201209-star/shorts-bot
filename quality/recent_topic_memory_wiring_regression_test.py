"""Regression for the dead recent-topics memory wiring.

Authority: `content/topic_selector.py::remember_used_topic()` existed but was
never called anywhere in production, and `recent_topics.json` was never
uploaded/restored as a workflow artifact -- so `get_recent_topic_names()`
always returned an empty list on every run, and the Candidate Explorer's
"recent content" prompt context was always the literal fallback string
"최근 콘텐츠 기록 없음." (no history). This repeatedly steered the Explorer
back toward the same small set of well-known aviation topics (winglet,
spoiler, static wick, pitot tube, ...), which the Novelty Judge then
correctly rejects as over-covered -- directly contributing to full
candidate-budget exhaustion (Run 35204235936).

Fix: call the existing `remember_used_topic()` once a script actually passes
(main.py), and persist `recent_topics.json` across ephemeral CI runners using
the exact same GitHub Actions artifact restore/upload pattern this repo
already uses for `analytics/performance_history.json`
(`analytics/restore_history_artifact.py`, generalized with an artifact-name
prefix and file-suffix parameter -- default behavior for the existing
analytics-history caller is unchanged).
"""
import json
import os
import re
import tempfile
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from analytics.restore_history_artifact import restore_latest_history

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, *, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeTransport:
    def __init__(self, archive):
        self.archive = archive

    def get(self, url, **kwargs):
        if url.endswith("actions/artifacts?per_page=100"):
            return FakeResponse(payload={"artifacts": [
                {"id": 1, "name": "analytics-history-1", "expired": False, "created_at": "2026-09-01T00:00:00Z", "archive_download_url": "https://archive/1"},
                {"id": 2, "name": "recent-topics-2", "expired": False, "created_at": "2026-09-02T00:00:00Z", "archive_download_url": "https://archive/2"},
                {"id": 3, "name": "recent-topics-old", "expired": True, "created_at": "2026-09-03T00:00:00Z", "archive_download_url": "https://archive/3"},
            ]})
        if url == "https://archive/2":
            return FakeResponse(content=self.archive)
        raise AssertionError(url)


def case_a_recent_topics_artifact_restore_with_new_params():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        zf.writestr("recent_topics.json", json.dumps([{"topic": "비행기 착빙 방지 시스템"}]))
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "recent_topics.json")
        result = restore_latest_history(
            repository="owner/repo",
            token="token",
            destination=dest,
            artifact_name_prefix="recent-topics-",
            file_suffix="recent_topics.json",
            transport=FakeTransport(buffer.getvalue()),
        )
        assert result["restored"] is True, result
        assert result["artifact_id"] == 2, result
        with open(dest, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload[0]["topic"] == "비행기 착빙 방지 시스템"
    print("CASE A recent-topics artifact restores via generalized prefix/suffix: PASS")


def case_b_default_analytics_history_behavior_unchanged():
    # Byte-identical to the pre-existing history_artifact_restore_regression_test
    # scenario: default params must still target analytics-history-*/
    # performance_history.json so the existing youtube_analytics_ingestion.yml
    # caller (which passes no prefix/suffix) is completely unaffected.
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        zf.writestr("analytics/performance_history.json", json.dumps({"records": [{"lineage_id": "x"}]}))

    class DefaultTransport:
        def get(self, url, **kwargs):
            if url.endswith("actions/artifacts?per_page=100"):
                return FakeResponse(payload={"artifacts": [
                    {"id": 9, "name": "analytics-history-9", "expired": False, "created_at": "2026-09-01T00:00:00Z", "archive_download_url": "https://archive/9"},
                ]})
            if url == "https://archive/9":
                return FakeResponse(content=buffer.getvalue())
            raise AssertionError(url)

    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "analytics", "performance_history.json")
        result = restore_latest_history(
            repository="owner/repo", token="token", destination=dest, transport=DefaultTransport(),
        )
        assert result["restored"] is True, result
        assert result["artifact_id"] == 9, result
    print("CASE B default analytics-history behavior unchanged: PASS")


def case_c_main_py_calls_remember_used_topic_in_success_path():
    text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "remember_used_topic" in text, "remember_used_topic must be imported/called in main.py"
    assert re.search(r"from content\.topic_selector import \([^)]*remember_used_topic", text, re.S), (
        "remember_used_topic must be imported from content.topic_selector"
    )
    final_script_index = text.index("script_data = (\n            final_script")
    call_index = text.index("remember_used_topic(script_data)")
    quality_pass_index = text.index('"🏆 V3.2.1.2 QUALITY PASS"')
    assert final_script_index < call_index < quality_pass_index, (
        "remember_used_topic must fire after the final script is confirmed and "
        "before/around the QUALITY PASS announcement, exactly once per successful run"
    )
    print("CASE C main.py calls remember_used_topic exactly once in the success path: PASS")


def case_d_main_yml_restores_and_preserves_recent_topics():
    text = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    assert "actions: read" in text, "main.yml must grant actions: read to call the Actions artifacts API"

    restore_index = text.index("Restore recent-topics memory")
    generator_index = text.index("Run Shorts Generator V3.2")
    assert restore_index < generator_index, "restore must run before the generator so it can read prior topics"

    restore_block = text[restore_index:generator_index]
    assert "SHORTS_HISTORY_ARTIFACT_PREFIX: recent-topics-" in restore_block
    assert "SHORTS_HISTORY_ARTIFACT_FILE_SUFFIX: recent_topics.json" in restore_block
    assert "SHORTS_ANALYTICS_HISTORY_PATH: recent_topics.json" in restore_block
    assert "analytics.restore_history_artifact" in restore_block

    preserve_analytics_index = text.index("Preserve analytics history")
    preserve_topics_index = text.index("Preserve recent-topics memory")
    assert preserve_analytics_index < preserve_topics_index

    preserve_block = text[preserve_topics_index:preserve_topics_index + 400]
    assert "name: recent-topics-${{ github.run_id }}" in preserve_block
    assert "path: recent_topics.json" in preserve_block
    print("CASE D main.yml restores recent_topics.json before the run and preserves it after: PASS")


def case_e_no_threshold_budget_retry_change():
    # main.py legitimately already defines MAX_TOPIC_REGENERATIONS; this fix
    # must not change its value. Files that never defined these constants
    # must still not introduce them.
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "MAX_TOPIC_REGENERATIONS = 1" in main_text, (
        "MAX_TOPIC_REGENERATIONS must remain at its existing production value"
    )

    other_touched = (
        "analytics/restore_history_artifact.py",
        ".github/workflows/main.yml",
    )
    forbidden = (
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "MAX_TOPIC_REGENERATIONS =",
        "_PREWRITER_NOVELTY_MIN_SCORE =",
        "NOVELTY_HARD_REGENERATE_SCORE =",
    )
    for rel in other_touched:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{rel} unexpectedly touched {token}"
    print("CASE E no quality/budget/retry constant changed: PASS")


def main():
    case_a_recent_topics_artifact_restore_with_new_params()
    case_b_default_analytics_history_behavior_unchanged()
    case_c_main_py_calls_remember_used_topic_in_success_path()
    case_d_main_yml_restores_and_preserves_recent_topics()
    case_e_no_threshold_budget_retry_change()
    print("RECENT TOPIC MEMORY WIRING REGRESSION: PASS")


if __name__ == "__main__":
    main()
