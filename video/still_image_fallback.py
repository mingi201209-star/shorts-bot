import base64
import hashlib
import os
import subprocess
from pathlib import Path

import requests

from config import OPENAI_KEY

STILL_IMAGE_FALLBACK_ENABLED = os.environ.get("STILL_IMAGE_FALLBACK_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
STILL_IMAGE_MODEL = os.environ.get("STILL_IMAGE_MODEL", "gpt-image-1.5")
STILL_IMAGE_QUALITY = os.environ.get("STILL_IMAGE_QUALITY", "low")
STILL_IMAGE_SIZE = os.environ.get("STILL_IMAGE_SIZE", "1024x1536")
# Keep this budget independent from the disabled Sora video-generation budget.
# Production evidence can require two distinct verified stills when separate
# concrete aviation scenes both have no semantically safe stock candidate.
STILL_IMAGE_MAX_PER_VIDEO = int(os.environ.get("STILL_IMAGE_MAX_PER_VIDEO", "2"))

_GENERATION_COUNT = 0
_VERIFIED_STILL_CACHE = {}


def reset_still_image_budget():
    global _GENERATION_COUNT
    _GENERATION_COUNT = 0
    _VERIFIED_STILL_CACHE.clear()


def still_image_generation_count():
    return _GENERATION_COUNT


def _scene_id(scene):
    return str(scene.get("scene_id") or scene.get("index") or scene.get("id") or "unknown")


def _anchor_signature(scene):
    """Return a narrow physical-component signature for verified-still reuse.

    This deliberately does not import the production-hotfix-only
    ``extract_query_anchors`` symbol: focused regressions import this module
    before that installer runs. The signature is only a reuse prefilter; the
    reused clip must still pass the full production vision/anchor verifier.
    """
    query = str(scene.get("keyword", "") or "").strip().lower().replace("-", " ")
    words = set(query.split())
    signature = []
    if words & {"aircraft", "airplane", "aviation"}:
        signature.append("aircraft")
    if "winglet" in words:
        signature.append("winglet")
    elif "wingtip" in words or "wing" in words and "tip" in words:
        signature.append("wingtip")
    elif "wing" in words:
        signature.append("wing")
    if "window" in words:
        signature.append("window")
    if "landing gear" in query or ("landing" in words and "gear" in words):
        signature.append("landing_gear")
    if "wheel" in words or "wheels" in words:
        signature.append("wheel")
    if "tire" in words or "tires" in words or "tyre" in words or "tyres" in words:
        signature.append("tire")
    # No concrete component signature means no reuse. Broad aircraft-only
    # context is intentionally insufficient for this optimization.
    return tuple(signature) if len(signature) >= 2 else ()


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


def _verify_motion_clip(scene, output_path):
    # Reuse the already-bounded visual verifier used for generated Sora Hook
    # visuals. This adds no new verifier implementation and fails closed if the
    # generated still does not visibly contain the required query anchors.
    from video.hook_visual_dominance import evaluate_hook_subject_dominance
    from video.video_downloader import _anchor_aliases, extract_query_anchors

    candidate = {
        "id": f"still-verify-{_scene_id(scene)}",
        "source_id": f"still-verify-{_scene_id(scene)}",
        "provider": "openai_image",
        "source_type": "ai_generated_still_motion",
        "url": str(output_path),
        "page_url": None,
        "duration": 4.0,
        "width": 1080,
        "height": 1920,
        "search_position": 0,
    }
    result = evaluate_hook_subject_dominance(candidate, scene)
    if result.get("obvious_generation_artifact", False):
        return False, result
    if result.get("factual_visual_contradiction", False):
        return False, result
    if float(result.get("subject_visibility", 0) or 0) < 6.0:
        return False, result

    visible_words = set()
    for component in result.get("visible_components", []) or []:
        visible_words.update(str(component or "").strip().lower().replace("-", " ").split())
    anchors = extract_query_anchors(str(scene.get("keyword", "") or ""))
    for anchor in anchors:
        aliases = set(_anchor_aliases(anchor)) | {anchor}
        if not (visible_words & aliases):
            return False, result
    return True, result


def _reuse_verified_still(scene, *, output_path, duration, trigger_reason):
    signature = _anchor_signature(scene)
    cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
    image_path = Path(str(cached.get("image_path") or ""))
    if not signature or not image_path.is_file():
        return None

    try:
        _motion_clip(image_path, output_path, duration)
        verified, evidence = _verify_motion_clip(scene, output_path)
        if not verified:
            Path(output_path).unlink(missing_ok=True)
            return None
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=reused_verified "
            f"count={_GENERATION_COUNT} trigger={trigger_reason} anchors={'+'.join(signature)}"
        )
        return {
            "path": str(output_path),
            "provider": cached.get("provider", "openai_image"),
            "source_id": cached.get("source_id", "verified-still-reuse"),
            "mode": "REUSED_VERIFIED_STILL_MOTION",
            "tier": 2,
            "visual_state": "TRUE",
            "anchor_matched": len(signature),
            "anchor_total": len(signature),
            "visible_components": list(evidence.get("visible_components", []) or []),
        }
    except Exception as exc:
        Path(output_path).unlink(missing_ok=True)
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=reuse_failed "
            f"reason={type(exc).__name__}"
        )
        return None


def generate_still_motion_fallback(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    global _GENERATION_COUNT
    if not STILL_IMAGE_FALLBACK_ENABLED:
        return None

    # Prefer an already verified still for the exact same concrete component
    # signature before spending another image generation. The reused motion
    # clip is re-verified against the current scene, so this does not weaken the
    # visual quality floor. If reuse fails, normal bounded generation continues.
    reused = _reuse_verified_still(
        scene,
        output_path=output_path,
        duration=duration,
        trigger_reason=trigger_reason,
    )
    if reused:
        return reused

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
        verified, evidence = _verify_motion_clip(scene, output_path)
        if not verified:
            print(
                f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=rejected_by_vision "
                f"count={_GENERATION_COUNT}"
            )
            try:
                Path(output_path).unlink()
            except FileNotFoundError:
                pass
            return None
        source_id = f"still-{digest}"
        signature = _anchor_signature(scene)
        if signature:
            _VERIFIED_STILL_CACHE[signature] = {
                "image_path": str(image_path),
                "provider": "openai_image",
                "source_id": source_id,
            }
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=verified "
            f"count={_GENERATION_COUNT} model={STILL_IMAGE_MODEL} quality={STILL_IMAGE_QUALITY}"
        )
        return {
            "path": str(output_path),
            "provider": "openai_image",
            "source_id": source_id,
            "mode": "GENERATED_STILL_MOTION_VERIFIED",
            "tier": 2,
            "visual_state": "TRUE",
            "anchor_matched": len(signature),
            "anchor_total": len(signature),
            "visible_components": list(evidence.get("visible_components", []) or []),
        }
    except Exception as exc:
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=failed "
            f"reason={type(exc).__name__}"
        )
        return None
