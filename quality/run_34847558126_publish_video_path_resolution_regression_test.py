"""OAuth Publish Closure -- video path resolution regression.

Authority: with PR #372's OAuth credential fallback merged, the "Publish to
YouTube" step's OAuth-credential-presence check finally passes for the first
time in this repo's history, and the very next line executed is
`analytics.publish_and_persist._resolve_video_path()` (formerly a bare
`os.environ.get("SHORTS_VIDEO_PATH", "final_shorts.mp4")`). The production
renderer (`quality/final_render_integrity.begin_final_render_integrity`)
always writes the final video as `final_shorts_<fingerprint>.mp4` -- never
the literal `final_shorts.mp4` this module previously defaulted to -- and
`main.yml`'s "Publish to YouTube" step never sets `SHORTS_VIDEO_PATH`. Every
historical run masked this because every one of them failed earlier, at the
OAuth-credential check itself (`YOUTUBE_ANALYTICS_*` resolving empty). This
regression proves the fix closes that second, previously-unreachable gap.
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeResponse:
    def __init__(self, payload=None, headers=None):
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeTransport:
    def __init__(self):
        self.posts = []
        self.puts = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if "oauth2.googleapis.com" in url:
            return FakeResponse({"access_token": "test-token"})
        return FakeResponse({}, {"Location": "https://upload.example/session"})

    def put(self, url, **kwargs):
        self.puts.append((url, kwargs))
        return FakeResponse({"id": "video-oauth-verify-1"})


def _run_in_tempdir(fn):
    original_cwd = os.getcwd()
    scratch = tempfile.mkdtemp(prefix="oauth_video_path_")
    os.chdir(scratch)
    try:
        return fn(scratch)
    finally:
        os.chdir(original_cwd)


def main():
    from analytics import publish_and_persist as pap

    # CASE A: no SHORTS_VIDEO_PATH, no rendered file at all -- must fall back
    # to the original literal default, an explicit (not silently guessed)
    # FileNotFoundError target.
    def case_a(_scratch):
        os.environ.pop("SHORTS_VIDEO_PATH", None)
        return pap._resolve_video_path()
    assert _run_in_tempdir(case_a) == "final_shorts.mp4"
    print("CASE A no candidates -> literal default preserved: PASS")

    # CASE B: exactly one fingerprinted file present, no SHORTS_VIDEO_PATH --
    # this is the real production shape this fix targets.
    def case_b(_scratch):
        os.environ.pop("SHORTS_VIDEO_PATH", None)
        Path("final_shorts_965020e02930.mp4").write_bytes(b"fixture")
        return pap._resolve_video_path()
    assert _run_in_tempdir(case_b) == "final_shorts_965020e02930.mp4"
    print("CASE B single fingerprinted file resolved automatically: PASS")

    # CASE C: SHORTS_VIDEO_PATH explicitly set still wins unconditionally --
    # no behavior change for any existing caller (including this module's
    # own regression tests) that already sets it.
    def case_c(_scratch):
        os.environ["SHORTS_VIDEO_PATH"] = "explicit_override.mp4"
        Path("final_shorts_abcdef123456.mp4").write_bytes(b"fixture")
        try:
            return pap._resolve_video_path()
        finally:
            os.environ.pop("SHORTS_VIDEO_PATH", None)
    assert _run_in_tempdir(case_c) == "explicit_override.mp4"
    print("CASE C explicit SHORTS_VIDEO_PATH still wins: PASS")

    # CASE D: ambiguous (>1) fingerprinted files -- must NOT silently guess;
    # falls back to the explicit literal default (safe, clear failure).
    def case_d(_scratch):
        os.environ.pop("SHORTS_VIDEO_PATH", None)
        Path("final_shorts_aaaaaaaaaaaa.mp4").write_bytes(b"fixture")
        Path("final_shorts_bbbbbbbbbbbb.mp4").write_bytes(b"fixture")
        return pap._resolve_video_path()
    assert _run_in_tempdir(case_d) == "final_shorts.mp4"
    print("CASE D ambiguous multiple candidates -> safe explicit default, no guess: PASS")

    # CASE E: full main() end-to-end with a fake transport (no real network
    # calls) -- proves the whole publish path now actually succeeds given
    # real OAuth credentials, exactly the scenario PR #372 unblocked and this
    # fix completes. Previously this would have raised FileNotFoundError
    # immediately after the credential check passed.
    def case_e(_scratch):
        os.environ["ENABLE_YOUTUBE_UPLOAD"] = "1"
        os.environ["YOUTUBE_ANALYTICS_CLIENT_ID"] = "fixture-id"
        os.environ["YOUTUBE_ANALYTICS_CLIENT_SECRET"] = "fixture-secret"
        os.environ["YOUTUBE_ANALYTICS_REFRESH_TOKEN"] = "fixture-refresh"
        os.environ["SHORTS_YOUTUBE_TITLE"] = "OAuth verification fixture"
        os.environ["SHORTS_YOUTUBE_PRIVACY"] = "private"
        os.environ.pop("SHORTS_VIDEO_PATH", None)
        os.environ["SHORTS_ANALYTICS_HISTORY_PATH"] = "analytics_history_fixture.json"
        Path("final_shorts_e2e0e2e0e2e0.mp4").write_bytes(b"fixture-video-bytes")

        from analytics import youtube_upload as yu
        fake_transport = FakeTransport()
        original_requests = yu.requests
        original_upload_video = yu.upload_video

        def patched_upload_video(video_path, **kwargs):
            kwargs["transport"] = fake_transport
            return original_upload_video(video_path, **kwargs)

        pap.upload_video = patched_upload_video
        try:
            exit_code = pap.main()
        finally:
            pap.upload_video = original_upload_video
            for key in (
                "ENABLE_YOUTUBE_UPLOAD", "YOUTUBE_ANALYTICS_CLIENT_ID",
                "YOUTUBE_ANALYTICS_CLIENT_SECRET", "YOUTUBE_ANALYTICS_REFRESH_TOKEN",
                "SHORTS_YOUTUBE_TITLE", "SHORTS_YOUTUBE_PRIVACY",
                "SHORTS_ANALYTICS_HISTORY_PATH",
            ):
                os.environ.pop(key, None)
        return exit_code, fake_transport
    exit_code, fake_transport = _run_in_tempdir(case_e)
    assert exit_code == 0, exit_code
    assert len(fake_transport.puts) == 1, "expected exactly one upload PUT"
    print("CASE E full main() succeeds end-to-end via glob-resolved video path: PASS")

    print("RUN 34847558126 PUBLISH VIDEO PATH RESOLUTION REGRESSION: PASS")


if __name__ == "__main__":
    main()
