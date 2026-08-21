import hashlib
import os
import time
from pathlib import Path

import requests

from config import OPENAI_KEY

AI_VISUAL_FALLBACK_ENABLED = os.environ.get("AI_VISUAL_FALLBACK_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
AI_MAX_GENERATIONS_PER_VIDEO = int(os.environ.get("AI_MAX_GENERATIONS_PER_VIDEO", "1"))
AI_VISUAL_MODEL = os.environ.get("AI_VISUAL_MODEL", "sora-2")
AI_VISUAL_SECONDS = int(os.environ.get("AI_VISUAL_SECONDS", "4"))
AI_VISUAL_SIZE = os.environ.get("AI_VISUAL_SIZE", "720x1280")
AI_VISUAL_POLL_SECONDS = float(os.environ.get("AI_VISUAL_POLL_SECONDS", "5"))
AI_VISUAL_MAX_POLLS = int(os.environ.get("AI_VISUAL_MAX_POLLS", "36"))

_GENERATION_COUNT = 0


def reset_generation_budget():
    global _GENERATION_COUNT
    _GENERATION_COUNT = 0


def generation_count():
    return _GENERATION_COUNT


def _scene_id(scene):
    return str(scene.get("scene_id") or scene.get("index") or scene.get("id") or "unknown")


def ai_visual_eligible(scene, *, hook=False):
    if hook:
        return True
    combined = " ".join(str(scene.get(k, "") or "") for k in ("text", "visual_goal", "keyword", "visual_type")).lower()
    mechanism_terms = (
        "mechanism", "structure", "layer", "cross-section", "pressure", "stress",
        "작동", "구조", "단면", "압력", "응력", "원리", "메커니즘",
    )
    ambience_terms = ("ambient", "mood", "atmosphere", "분위기", "배경")
    return any(term in combined for term in mechanism_terms) and not any(term in combined for term in ambience_terms)


def build_visual_prompt(scene, *, required_components, hook=False):
    narration = str(scene.get("text", "") or "").strip()
    visual_goal = str(scene.get("visual_goal", "") or "").strip()
    components = ", ".join(required_components or []) or "the concrete subject named in the narration"
    emphasis = (
        "The required subject must be large, clear, and immediately identifiable from the first frame on a phone."
        if hook else
        "Clearly show the required subject and the mechanism being explained."
    )
    return (
        "Create a short vertical educational visual for a Korean YouTube Short. "
        f"Narration meaning: {narration}. Visual goal: {visual_goal}. "
        f"Required visible components: {components}. {emphasis} "
        "9:16 portrait composition, uncluttered, no on-screen text, no logos, no decorative unrelated objects. "
        "Do not invent hidden technical structure, design intent, historical cause, measurements, labels, or mechanisms beyond what is explicitly stated above. "
        "If a photorealistic technical depiction would require unsupported detail, use a simple physically conservative educational visualization instead."
    )


def _headers():
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_KEY is unavailable")
    return {"Authorization": f"Bearer {OPENAI_KEY}"}


def _create_job(prompt):
    response = requests.post(
        "https://api.openai.com/v1/videos",
        headers=_headers(),
        data={
            "model": AI_VISUAL_MODEL,
            "prompt": prompt,
            "seconds": str(AI_VISUAL_SECONDS),
            "size": AI_VISUAL_SIZE,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _wait_for_job(video_id):
    for _ in range(max(1, AI_VISUAL_MAX_POLLS)):
        response = requests.get(
            f"https://api.openai.com/v1/videos/{video_id}",
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        status = str(payload.get("status", ""))
        if status == "completed":
            return payload
        if status == "failed":
            error = payload.get("error") or {}
            raise RuntimeError(f"Sora generation failed: {error.get('code', 'unknown')}")
        time.sleep(max(0.25, AI_VISUAL_POLL_SECONDS))
    raise TimeoutError("Sora generation did not complete within bounded polling budget")


def _download_content(video_id, prompt_hash):
    response = requests.get(
        f"https://api.openai.com/v1/videos/{video_id}/content",
        headers=_headers(),
        timeout=120,
    )
    response.raise_for_status()
    output_dir = Path("workspace/temp")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"ai_visual_{prompt_hash}.mp4"
    path.write_bytes(response.content)
    return str(path)


def generate_ai_visual(scene, *, required_components, hook=False, trigger_reason="scarcity"):
    global _GENERATION_COUNT
    if not AI_VISUAL_FALLBACK_ENABLED:
        return None
    if not ai_visual_eligible(scene, hook=hook):
        return None
    if _GENERATION_COUNT >= AI_MAX_GENERATIONS_PER_VIDEO:
        print(f"[AI_VISUAL] generation_count={_GENERATION_COUNT} trigger_reason={trigger_reason} scene_id={_scene_id(scene)} generation_status=budget_exhausted")
        return None

    _GENERATION_COUNT += 1
    prompt = build_visual_prompt(scene, required_components=required_components, hook=hook)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    print(f"[AI_VISUAL] generation_count={_GENERATION_COUNT} trigger_reason={trigger_reason} scene_id={_scene_id(scene)} generation_status=started")
    try:
        created = _create_job(prompt)
        video_id = str(created.get("id") or "")
        if not video_id:
            raise RuntimeError("Sora create response missing video id")
        completed = _wait_for_job(video_id)
        path = _download_content(video_id, prompt_hash)
        print(f"[AI_VISUAL] generation_count={_GENERATION_COUNT} trigger_reason={trigger_reason} scene_id={_scene_id(scene)} generation_status=completed")
        return {
            "id": video_id,
            "source_id": video_id,
            "provider": "openai_sora",
            "source_type": "ai_generated",
            "generation_id": video_id,
            "scene_id": _scene_id(scene),
            "prompt_hash": prompt_hash,
            "url": path,
            "page_url": None,
            "duration": float(completed.get("seconds") or AI_VISUAL_SECONDS),
            "width": 720,
            "height": 1280,
            "search_position": 0,
        }
    except Exception as exc:
        print(f"[AI_VISUAL] generation_count={_GENERATION_COUNT} trigger_reason={trigger_reason} scene_id={_scene_id(scene)} generation_status=failed reason={type(exc).__name__}")
        return None
