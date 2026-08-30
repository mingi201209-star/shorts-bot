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
STILL_IMAGE_MAX_PER_VIDEO = int(os.environ.get("STILL_IMAGE_MAX_PER_VIDEO", "2"))
MAX_INFORMATION_USES_PER_PHYSICAL_STILL = 2

_GENERATION_COUNT = 0
_VERIFIED_STILL_CACHE = {}
_VERIFIED_SOURCE_USE_COUNTS = {}


def reset_still_image_budget():
    global _GENERATION_COUNT
    _GENERATION_COUNT = 0
    _VERIFIED_STILL_CACHE.clear()
    _VERIFIED_SOURCE_USE_COUNTS.clear()


def still_image_generation_count():
    return _GENERATION_COUNT


def _scene_id(scene):
    return str(scene.get("scene_id") or scene.get("index") or scene.get("id") or "unknown")


def _is_information_scene(scene):
    role = str((scene or {}).get("role") or (scene or {}).get("scene_role") or "").strip().lower()
    return role not in {"transition", "atmosphere"}


def _source_reuse_allowed(source_id, scene):
    if not _is_information_scene(scene):
        return True
    return int(_VERIFIED_SOURCE_USE_COUNTS.get(str(source_id or ""), 0)) < MAX_INFORMATION_USES_PER_PHYSICAL_STILL


def _register_source_use(source_id, scene):
    if not source_id or not _is_information_scene(scene):
        return
    key = str(source_id)
    _VERIFIED_SOURCE_USE_COUNTS[key] = int(_VERIFIED_SOURCE_USE_COUNTS.get(key, 0)) + 1


def verified_source_use_count(source_id):
    return int(_VERIFIED_SOURCE_USE_COUNTS.get(str(source_id or ""), 0))


def _anchor_signature(scene):
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
    return tuple(signature) if len(signature) >= 2 else ()


def _reuse_signatures(scene):
    signature = _anchor_signature(scene)
    if not signature:
        return ()
    signatures = [signature]
    if signature == ("aircraft", "wing"):
        signatures.extend((("aircraft", "winglet"), ("aircraft", "wingtip")))
    return tuple(signatures)


def _clean_terms(values):
    terms = []
    for value in values or []:
        normalized = str(value or "").strip().lower().replace("-", " ")
        for token in normalized.split():
            if token and token not in terms:
                terms.append(token)
    return terms


def _canonical_still_contract(scene):
    """Build generation-only composition guidance from trusted canonical metadata."""
    profile = (scene or {}).get("_canonical_visual_supply")
    if not isinstance(profile, dict):
        return {
            "canonical_subject": "",
            "trusted_visual_discriminators": [],
            "required_viewpoint": "",
            "subject_proof_priority": [],
            "negative_composition_guards": [],
        }

    canonical_subject = str(profile.get("canonical_subject") or "").strip()
    discriminators = _clean_terms(profile.get("visual_discriminators") or [])
    canonical_terms = _clean_terms(profile.get("canonical_terms") or canonical_subject.split())
    trusted_terms = set(canonical_terms + discriminators)

    # Viewpoint is inferred only when trusted physical evidence identifies a
    # rear/trailing-edge feature. This remains empty for generic subjects.
    has_rear_feature = bool(
        trusted_terms & {"rear", "trailing", "nozzle"}
        and trusted_terms & {"chevron", "serrated", "sawtooth", "edge"}
    )
    required_viewpoint = "rear or rear-quarter close-up of the trailing edge" if has_rear_feature else ""

    priority = []
    for group in (
        ("nozzle", "nacelle", "trailing", "edge"),
        ("chevron", "serrated", "sawtooth"),
        tuple(canonical_terms),
    ):
        for term in group:
            if term in trusted_terms and term not in priority:
                priority.append(term)

    negative_guards = []
    if priority:
        negative_guards.extend([
            "aircraft-wide shot",
            "generic turbine close-up",
            "unrelated wing detail",
        ])
    if has_rear_feature:
        negative_guards.extend([
            "front fan intake dominant",
            "engine interior blades as primary subject",
        ])

    return {
        "canonical_subject": canonical_subject,
        "trusted_visual_discriminators": discriminators,
        "required_viewpoint": required_viewpoint,
        "subject_proof_priority": priority,
        "negative_composition_guards": negative_guards,
    }


def _prompt(scene):
    narration = str(scene.get("text", "") or "").strip()
    visual_goal = str(scene.get("visual_goal", "") or "").strip()
    keyword = str(scene.get("keyword", "") or "").strip()
    contract = _canonical_still_contract(scene)

    proof = ""
    canonical_subject = contract["canonical_subject"]
    priority = contract["subject_proof_priority"]
    viewpoint = contract["required_viewpoint"]
    negative_guards = contract["negative_composition_guards"]

    if canonical_subject and priority:
        proof = (
            f"Trusted canonical subject: {canonical_subject}. "
            f"Subject-proof priority, highest first: {', '.join(priority)}. "
            "The highest-priority externally visible component must occupy a large central portion of the portrait frame and be immediately identifiable on a phone screen. "
            "Aircraft context may remain visible but must be secondary to the proof component. "
        )
        if viewpoint:
            proof += f"Required viewpoint from trusted physical evidence: {viewpoint}. "
        if negative_guards:
            proof += f"Avoid these compositions: {', '.join(negative_guards)}. "

    return (
        "Create one accurate vertical educational still image for a Korean YouTube Short. "
        + proof
        + f"Narration meaning: {narration}. Visual goal: {visual_goal}. Search concept: {keyword}. "
        "Show the exact physical subject named in the narration clearly and prominently. "
        "No text, captions, logos, diagrams with invented labels, unrelated decorative objects, or cross-domain metaphors. "
        "Do not invent hidden technical structure, measurements, or unsupported mechanisms. "
        "If technical internals are uncertain, show only the externally visible real-world subject in a conservative photorealistic style. "
        "Portrait 9:16 composition, mobile readable, uncluttered."
    )


def _trace_canonical_still(scene, *, prompt=None, evidence=None, result="pending"):
    contract = _canonical_still_contract(scene)
    prompt_signature = (
        hashlib.sha256(str(prompt).encode("utf-8")).hexdigest()[:16]
        if prompt is not None
        else "none"
    )
    evidence = evidence if isinstance(evidence, dict) else {}
    visible_groups = evidence.get("visible_subject_groups") or {}
    print(
        "[CANONICAL_STILL_TRACE] "
        f"scene={_scene_id(scene)} "
        f"canonical_subject={contract['canonical_subject'] or 'none'} "
        f"trusted_visual_discriminators={'+'.join(contract['trusted_visual_discriminators']) or 'none'} "
        f"required_viewpoint={contract['required_viewpoint'] or 'none'} "
        f"subject_proof_priority={'+'.join(contract['subject_proof_priority']) or 'none'} "
        f"final_prompt_signature={prompt_signature} "
        f"vision_structured_groups={visible_groups or 'none'} "
        f"result={result}"
    )


def _generate_image(scene):
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_KEY is unavailable")
    prompt = _prompt(scene)
    _trace_canonical_still(scene, prompt=prompt, result="generation_requested")
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
    for signature in _reuse_signatures(scene):
        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        image_path = Path(str(cached.get("image_path") or ""))
        source_id = str(cached.get("source_id") or "verified-still-reuse")
        if not image_path.is_file():
            continue
        if not _source_reuse_allowed(source_id, scene):
            print(
                f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=diversity_skip "
                f"source_id={source_id} uses={verified_source_use_count(source_id)}"
            )
            continue
        try:
            _motion_clip(image_path, output_path, duration)
            verified, evidence = _verify_motion_clip(scene, output_path)
            if not verified:
                Path(output_path).unlink(missing_ok=True)
                continue
            _register_source_use(source_id, scene)
            print(
                f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=reused_verified "
                f"count={_GENERATION_COUNT} trigger={trigger_reason} anchors={'+'.join(signature)} "
                f"source_uses={verified_source_use_count(source_id)}"
            )
            return {
                "path": str(output_path),
                "provider": cached.get("provider", "openai_image"),
                "source_id": source_id,
                "mode": "REUSED_VERIFIED_STILL_MOTION",
                "tier": 2,
                "visual_state": "TRUE",
                "anchor_matched": len(_anchor_signature(scene)),
                "anchor_total": len(_anchor_signature(scene)),
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
        _trace_canonical_still(
            scene,
            prompt=prompt,
            evidence=evidence,
            result="verified" if verified else "rejected_by_vision",
        )
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
        _register_source_use(source_id, scene)
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=verified "
            f"count={_GENERATION_COUNT} model={STILL_IMAGE_MODEL} quality={STILL_IMAGE_QUALITY} "
            f"source_uses={verified_source_use_count(source_id)}"
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
