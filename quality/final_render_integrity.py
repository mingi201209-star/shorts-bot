import hashlib
import json
import os
import re
import subprocess
import time

import numpy as np

from config import VIDEO_HEIGHT, VIDEO_WIDTH


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def assert_content_identity(expected_topic, script_data, stage="unknown"):
    expected = _clean(expected_topic)
    actual = _clean((script_data or {}).get("topic"))
    if not expected:
        raise RuntimeError(f"CONTENT_IDENTITY_INVALID_EXPECTED_TOPIC stage={stage}")
    if actual != expected:
        raise RuntimeError(
            "CONTENT_IDENTITY_DRIFT "
            f"stage={stage} expected={expected!r} actual={actual!r}"
        )
    return True


def _scene_contract(scene, index):
    if not isinstance(scene, dict):
        raise RuntimeError(f"FINAL_RENDER_SCENE_INVALID index={index}")
    text = _clean(scene.get("text"))
    keyword = _clean(scene.get("keyword"))
    visual_goal = _clean(scene.get("visual_goal"))
    if not text:
        raise RuntimeError(f"FINAL_RENDER_SCENE_TEXT_MISSING index={index}")
    if not keyword:
        raise RuntimeError(f"FINAL_RENDER_SCENE_KEYWORD_MISSING index={index}")
    if not visual_goal:
        raise RuntimeError(f"FINAL_RENDER_VISUAL_GOAL_MISSING index={index}")
    return {
        "index": index,
        "text": text,
        "keyword": keyword,
        "visual_goal": visual_goal,
    }


def build_content_manifest(script_data, expected_topic):
    assert_content_identity(expected_topic, script_data, stage="pre_production")
    scenes = list((script_data or {}).get("scenes") or [])
    if not scenes:
        raise RuntimeError("FINAL_RENDER_NO_SCENES")
    normalized_scenes = [_scene_contract(scene, idx) for idx, scene in enumerate(scenes)]
    payload = {
        "topic": _clean(expected_topic),
        "title": _clean((script_data or {}).get("title")),
        "scenes": normalized_scenes,
    }

    # Observability only: preserve the already-decided retention contract so a
    # production artifact can explain whether a short render was intentionally
    # routed to a thin bucket or lost duration downstream. These fields do not
    # affect routing, FACT gates, scene generation, or render timing.
    runtime_bucket = _clean((script_data or {}).get("runtime_bucket"))
    retention_structure = (script_data or {}).get("retention_structure")
    payload["scene_count"] = len(normalized_scenes)
    if runtime_bucket:
        payload["runtime_bucket"] = runtime_bucket
    if isinstance(retention_structure, dict):
        payload["retention_structure"] = retention_structure

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload["fingerprint"] = fingerprint
    return payload


def begin_final_render_integrity(script_data, expected_topic, manifest_path="final_content_manifest.json"):
    manifest = build_content_manifest(script_data, expected_topic)
    short_id = manifest["fingerprint"][:12]
    output_path = f"final_shorts_{short_id}.mp4"

    # A stale fixed-name output must never be mistaken for the current production.
    for stale_path in (output_path, "final_shorts.mp4"):
        if os.path.exists(stale_path):
            os.remove(stale_path)

    manifest["output_path"] = output_path
    manifest["started_at"] = time.time()
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"CONTENT_INTEGRITY manifest={manifest_path} fingerprint={manifest['fingerprint']}")
    print(f"CONTENT_INTEGRITY output={output_path}")
    return manifest


def _probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FINAL_RENDER_FFPROBE_FAILED {result.stderr[-500:]}")
    return float(result.stdout.strip())


def assess_opening_frame_visual_safety(frame, *, subtitle_visible=True, timestamp=0.0):
    frame = np.asarray(frame)
    if frame.ndim != 3 or frame.shape[2] < 3:
        return {
            "pass": False,
            "reason": "opening_frame_invalid",
            "timestamp": float(timestamp),
        }
    rgb = frame[:, :, :3].astype(np.float32)
    gray = (
        0.299 * rgb[:, :, 0]
        + 0.587 * rgb[:, :, 1]
        + 0.114 * rgb[:, :, 2]
    )
    mean = float(np.mean(gray))
    std = float(np.std(gray))
    edge = 0.0
    if gray.shape[0] > 1 and gray.shape[1] > 1:
        edge = float(
            np.mean(np.abs(np.diff(gray[::4, ::4], axis=0)))
            + np.mean(np.abs(np.diff(gray[::4, ::4], axis=1)))
        )
    black_or_empty = mean < 12.0 and std < 8.0 and edge < 3.0
    if subtitle_visible and black_or_empty:
        return {
            "pass": False,
            "reason": "subtitle_on_black_or_empty_frame",
            "timestamp": float(timestamp),
            "mean_luma": round(mean, 3),
            "std_luma": round(std, 3),
            "edge_signal": round(edge, 3),
        }
    return {
        "pass": True,
        "reason": "opening_frame_visual_ready",
        "timestamp": float(timestamp),
        "mean_luma": round(mean, 3),
        "std_luma": round(std, 3),
        "edge_signal": round(edge, 3),
    }


def _probe_opening_frame(path):
    result = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-ss", "0", "-i", path,
            "-frames:v", "1",
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FINAL_RENDER_OPENING_FRAME_PROBE_FAILED {result.stderr[-500:]!r}")
    expected = VIDEO_WIDTH * VIDEO_HEIGHT * 3
    if len(result.stdout) < expected:
        raise RuntimeError("FINAL_RENDER_OPENING_FRAME_MISSING")
    return np.frombuffer(result.stdout[:expected], dtype=np.uint8).reshape(
        (VIDEO_HEIGHT, VIDEO_WIDTH, 3)
    )


def validate_opening_frame_visual_safety(final_path):
    frame = _probe_opening_frame(final_path)
    result = assess_opening_frame_visual_safety(
        frame,
        subtitle_visible=True,
        timestamp=0.0,
    )
    if not result.get("pass"):
        raise RuntimeError(
            "FINAL_RENDER_OPENING_FRAME_VISUAL_UNSAFE "
            f"reason={result.get('reason')} mean={result.get('mean_luma')} "
            f"std={result.get('std_luma')}"
        )
    print(
        "FINAL_RENDER_OPENING_FRAME_VISUAL_READY "
        f"mean={result.get('mean_luma')} std={result.get('std_luma')}"
    )
    return result


def validate_final_render_integrity(final_path, script_data, expected_topic, manifest, expected_duration):
    assert_content_identity(expected_topic, script_data, stage="post_render")
    current = build_content_manifest(script_data, expected_topic)
    if current["fingerprint"] != manifest.get("fingerprint"):
        raise RuntimeError(
            "CONTENT_IDENTITY_FINGERPRINT_DRIFT "
            f"expected={manifest.get('fingerprint')} actual={current['fingerprint']}"
        )
    if final_path != manifest.get("output_path"):
        raise RuntimeError(
            "FINAL_RENDER_OUTPUT_PATH_MISMATCH "
            f"expected={manifest.get('output_path')} actual={final_path}"
        )
    if not os.path.exists(final_path) or os.path.getsize(final_path) <= 0:
        raise RuntimeError("FINAL_RENDER_OUTPUT_MISSING")
    if os.path.getmtime(final_path) + 1 < float(manifest.get("started_at", 0)):
        raise RuntimeError("FINAL_RENDER_STALE_OUTPUT")

    actual_duration = _probe_duration(final_path)
    tolerance = max(1.0, float(expected_duration) * 0.03)
    if abs(actual_duration - float(expected_duration)) > tolerance:
        raise RuntimeError(
            "FINAL_RENDER_DURATION_MISMATCH "
            f"expected={float(expected_duration):.3f} actual={actual_duration:.3f} tolerance={tolerance:.3f}"
        )

    validate_opening_frame_visual_safety(final_path)

    print(
        "FINAL_RENDER_CONTENT_INTEGRITY PASS "
        f"topic={expected_topic!r} fingerprint={manifest['fingerprint'][:12]} "
        f"duration={actual_duration:.2f}s"
    )
    return True
