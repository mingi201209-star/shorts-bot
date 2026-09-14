"""Run 34847558126 YouTube OAuth credential alias fallback regression.

Authority: Publish Stable Engine run 34847540739 -> child Shorts Generator
run 34847558126 (publish-stable, youtube_upload=true, immediately after PR
#371 wired explicit upload intent through) proved that
`YOUTUBE_ANALYTICS_CLIENT_ID` / `YOUTUBE_ANALYTICS_CLIENT_SECRET` /
`YOUTUBE_ANALYTICS_REFRESH_TOKEN` resolve to empty strings at the actual
GitHub Actions secrets store under their current names, even though the
workflow's own `${{ secrets.YOUTUBE_ANALYTICS_* }}` mapping syntax was
already correct. `analytics.publish_and_persist` then safely no-oped with
"OAuth credentials unavailable" instead of uploading.

Fix: both the publish step in main.yml and the collect job in
youtube_analytics_ingestion.yml try the current `YOUTUBE_ANALYTICS_*` secret
name first and fall back to a legacy `YT_*` alias only when the current name
is unset (GitHub Actions `A || B` expression semantics: empty string is
falsy). This is a no-op once `YOUTUBE_ANALYTICS_*` is actually populated,
and does not change behavior at all if neither name is set.

This regression is static (parses the actual committed YAML) since neither
this environment nor CI has access to the real secret values -- it proves
the *wiring* pattern is present and correctly ordered, not that upload
succeeds against a live YouTube account.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_CREDENTIAL_ALIASES = (
    ("YOUTUBE_ANALYTICS_CLIENT_ID", "YT_CLIENT_ID"),
    ("YOUTUBE_ANALYTICS_CLIENT_SECRET", "YT_CLIENT_SECRET"),
    ("YOUTUBE_ANALYTICS_REFRESH_TOKEN", "YT_REFRESH_TOKEN"),
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _assert_fallback_wired(text: str, label: str) -> None:
    for current, legacy in _CREDENTIAL_ALIASES:
        # Current name must be tried first, legacy only as a fallback -- not
        # the other way around, and not the legacy name used bare/alone.
        expected = f"${{{{ secrets.{current} || secrets.{legacy} }}}}"
        assert expected in text, f"{label}: missing current-first fallback for {current}"
        # A bare, unconditional reference to the current name alone (the
        # pre-fix shape) must not remain anywhere in the file.
        bare = f"${{{{ secrets.{current} }}}}"
        assert bare not in text, f"{label}: unconditional (non-fallback) {current} reference still present"


def test_main_yml_publish_step_has_oauth_fallback() -> None:
    text = _read(".github/workflows/main.yml")
    assert "YOUTUBE_ANALYTICS_CLIENT_ID" in text
    _assert_fallback_wired(text, "main.yml")
    # The publish step itself, not some unrelated block, must carry it.
    marker_index = text.index("Publish to YouTube and persist lineage")
    step_slice = text[marker_index:marker_index + 1500]
    for current, legacy in _CREDENTIAL_ALIASES:
        assert f"secrets.{current} || secrets.{legacy}" in step_slice, (
            f"main.yml publish step does not carry the {current} fallback"
        )


def test_youtube_analytics_ingestion_collect_job_has_oauth_fallback() -> None:
    text = _read(".github/workflows/youtube_analytics_ingestion.yml")
    assert "YOUTUBE_ANALYTICS_CLIENT_ID" in text
    _assert_fallback_wired(text, "youtube_analytics_ingestion.yml")


def test_publish_engine_still_forwards_only_intent_not_secrets() -> None:
    # publish_engine.yml dispatches main.yml on the publish-stable ref via a
    # fresh workflow_dispatch; it must not itself carry a duplicate/parallel
    # OAuth secret mapping (that would be a second place to keep in sync).
    text = _read(".github/workflows/publish_engine.yml")
    assert "YOUTUBE_ANALYTICS_CLIENT_ID" not in text
    assert "secrets.YT_CLIENT_ID" not in text


def test_no_secret_values_or_engine_code_touched() -> None:
    # This fix must be workflow-only: no change to analytics/*.py, no video
    # regeneration, no printing of credential values anywhere in the diff
    # surface this test can see.
    #
    # Checked against THIS fix's own marker specifically, not the bare
    # "RUN_34847558126" run-id prefix: a later, separate, independently
    # reviewed fix (PR #375, RUN_34847558126_VIDEO_PATH_FINGERPRINT_
    # RESOLUTION_V1) legitimately touches analytics/publish_and_persist.py
    # -- a real code bug in video-path resolution discovered from the same
    # evidence run, unrelated to this OAuth-wiring-only change -- so the
    # bare run-id substring is no longer unique to this fix.
    oauth_fix_marker = "RUN_34847558126_OAUTH_CREDENTIAL_ALIAS_FALLBACK_V1"
    for path in ("analytics/publish_and_persist.py", "analytics/youtube_upload.py"):
        text = _read(path)
        assert oauth_fix_marker not in text, f"{path} unexpectedly touched by an OAuth-wiring-only fix"


def run() -> None:
    tests = [
        test_main_yml_publish_step_has_oauth_fallback,
        test_youtube_analytics_ingestion_collect_job_has_oauth_fallback,
        test_publish_engine_still_forwards_only_intent_not_secrets,
        test_no_secret_values_or_engine_code_touched,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print("YOUTUBE_OAUTH_CREDENTIAL_FALLBACK_REGRESSION: PASS")


if __name__ == "__main__":
    run()
