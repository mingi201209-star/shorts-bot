import base64
import hashlib
import os
import subprocess
from pathlib import Path

import requests

from config import OPENAI_KEY

STILL_IMAGE_FALLBACK_ENABLED = os.environ.get("STILL_IMAGE_FALLBACK_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
STILL_IMAGE_MODEL = os.environ.get("STILL_IMAGE_MODEL", "gpt-image-1.5")
STILL_IMAGE_QUALITY = os.environ.get("STILL_IMAGE_QUALITY", "low")
STILL_IMAGE_SIZE = os.environ.get("STILL_IMAGE_SIZE", "1024x1536")
STILL_IMAGE_MAX_PER_VIDEO = int(os.environ.get("STILL_IMAGE_MAX_PER_VIDEO", "1"))

_GENERATION_COUNT = 0


def reset_still_image_budget():
    global _GENERATION_COUNT
    _GENERATION_COUNT = 0


def still_image_generation_count():
    return _GENERATION_COUNT


def _scene_id(scene):
    return str(scene.get("scene_id") or scene.get("index") or scene.get("id") or "unknown")


def _prompt(scene):
    narration = str(scene.get("text", "") or "").strip()
    visual_goal = str(scene.get("visual_goal", "") or "").strip()
    keyword = str(scene.get("keyword", "") or "").strip()
    return (
        "Create one accurate vertical educational still image for a Korean YouTube Short. "
        f"Narration meaning: {narration}. Visual goal: {visual_goal}. Search concept: {keyword}. "
        "Show the exact physical subject named in the narration clearly and prominently. "
        "No text, captions, logos, diagrams with invented labels, unrelated decorative objects, or cross-domain metaphors. "
        "Do not invent hidden technical structure, measurements, or unsupported mechanisms. "
        "If technical internals are uncertain, show only the externally visible real-world subject in a conservative photorealistic style. "
        "Portrait 9:16 composition, mobile readable, uncluttered."
    )


def _generate_image(scene):
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_KEY is unavailable")
    prompt = _prompt(scene)
    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={
            "model": STILL_IMAGE_MODEL,
            "prompt": prompt,
            "size": STILL_IMAGE_SIZE,
            "quality": STILL_IMAGE_QUALITY,
            "n": 1,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or []
    if not data:
        raise RuntimeError("image generation response missing data")
    item = data[0] or {}
    raw = item.get("b64_json")
    if raw:
        return base64.b64decode(raw), prompt
    url = item.get("url")
    if url:
        download = requests.get(url, timeout=120)
        download.raise_for_status()
        return download.content, prompt
    raise RuntimeError("image generation response missing b64_json/url")


def _motion_clip(image_path, output_path, duration):
    duration = max(1.0, float(duration))
    fade = min(0.35, duration / 4.0)
    fade_out_start = max(0.0, duration - fade)
    vf = (
        "scale=1280:1920:force_original_aspect_ratio=increase,"
        "crop=1280:1920,"
        "zoompan=z='min(zoom+0.0007,1.08)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade:.3f},"
        "format=yuv420p"
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
            "-t", f"{duration:.3f}", "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("still-image motion ffmpeg failed: " + result.stderr[-1200:])
    if not Path(output_path).exists():
        raise RuntimeError("still-image motion output missing")


def generate_still_motion_fallback(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    global _GENERATION_COUNT
    if not STILL_IMAGE_FALLBACK_ENABLED:
        return None
    if _GENERATION_COUNT >= STILL_IMAGE_MAX_PER_VIDEO:
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=budget_exhausted "
            f"count={_GENERATION_COUNT} trigger={trigger_reason}"
        )
        return None

    _GENERATION_COUNT += 1
    try:
        image_bytes, prompt = _generate_image(scene)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        temp_dir = Path("workspace/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        image_path = temp_dir / f"still_fallback_{digest}.png"
        image_path.write_bytes(image_bytes)
        _motion_clip(image_path, output_path, duration)
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=completed "
            f"count={_GENERATION_COUNT} model={STILL_IMAGE_MODEL} quality={STILL_IMAGE_QUALITY}"
        )
        return {
            "path": str(output_path),
            "provider": "openai_image",
            "source_id": f"still-{digest}",
            "mode": "GENERATED_STILL_MOTION",
            "tier": 3,
            "visual_state": "GENERATED",
        }
    except Exception as exc:
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=failed "
            f"reason={type(exc).__name__}"
        )
        return None
