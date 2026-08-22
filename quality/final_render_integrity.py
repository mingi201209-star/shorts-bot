import hashlib
import json
import os
import re
import subprocess
import time


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

    print(
        "FINAL_RENDER_CONTENT_INTEGRITY PASS "
        f"topic={expected_topic!r} fingerprint={manifest['fingerprint'][:12]} "
        f"duration={actual_duration:.2f}s"
    )
    return True
