#!/usr/bin/env python3
"""Fail-closed validation for a verified Shorts Studio artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(artifact_dir: Path) -> dict:
    dist = artifact_dir / "dist"
    video = dist / "final.mp4"
    captions = dist / "captions.srt"
    description = dist / "upload-description.txt"
    report_path = dist / "qa_report.json"

    for path in (video, captions, description, report_path):
        _require(path.is_file() and path.stat().st_size > 0, f"missing or empty: {path.relative_to(artifact_dir)}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    _require(report.get("status") == "PASS", "qa_report.status must be PASS")
    _require(report.get("semantic_required") is True, "semantic_required must be true")
    _require((report.get("semantic_visual_qa") or {}).get("status") == "PASS", "semantic visual QA must PASS")
    semantic_results = (report.get("semantic_visual_qa") or {}).get("results")
    _require(isinstance(semantic_results, list) and bool(semantic_results), "semantic visual QA results are missing")
    _require(all(isinstance(item, dict) and item.get("status") == "PASS" for item in semantic_results),
             "every semantic visual result must PASS")
    _require((report.get("final_video_qa") or {}).get("status") == "PASS", "final video QA must PASS")
    _require((report.get("captions") or {}).get("status") == "PASS", "caption QA must PASS")
    subtitle_reports = report.get("subtitle_reports")
    _require(isinstance(subtitle_reports, list) and bool(subtitle_reports), "subtitle reports are missing")
    _require(all(isinstance(item, dict) and item.get("status") == "PASS" for item in subtitle_reports),
             "every subtitle report must PASS")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        check=True,
        capture_output=True,
        text=True,
    )
    media = json.loads(probe.stdout)
    streams = media.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    _require(bool(video_streams), "MP4 has no video stream")
    _require(bool(audio_streams), "MP4 has no audio stream")
    _require(video_streams[0].get("width") == 1080 and video_streams[0].get("height") == 1920,
             "MP4 must be 1080x1920 vertical video")
    duration = float((media.get("format") or {}).get("duration", 0))
    _require(duration > 0, "MP4 duration must be positive")
    _require(bool(description.read_text(encoding="utf-8").strip()), "upload description is empty")
    _require(bool(captions.read_text(encoding="utf-8").strip()), "caption file is empty")

    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    return {"video": str(video), "sha256": digest, "duration_seconds": duration,
            "width": 1080, "height": 1920, "semantic_scenes": len(semantic_results)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.artifact_dir)
        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"STUDIO_ARTIFACT_REJECTED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
