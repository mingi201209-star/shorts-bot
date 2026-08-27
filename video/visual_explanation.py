"""Visual Explanation / Retrieval V1.

A zero-LLM/zero-Vision transformation layer for explanation-heavy scenes.
It never weakens stock/reuse eligibility. It is only consulted after the
existing semantically-safe stock and verified-still paths fail.
"""

from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip

from config import VIDEO_HEIGHT, VIDEO_WIDTH

MAX_EXPLANATION_TRANSFORMS_PER_VIDEO = int(
    os.environ.get("MAX_EXPLANATION_TRANSFORMS_PER_VIDEO", "3")
)

_TRANSFORM_COUNT = 0
_INFORMATION_SIGNATURES: set[tuple[str, str]] = set()


def reset_visual_explanation_budget():
    global _TRANSFORM_COUNT
    _TRANSFORM_COUNT = 0
    _INFORMATION_SIGNATURES.clear()


def visual_explanation_transform_count():
    return _TRANSFORM_COUNT


def _text(scene):
    return " ".join(
        str(scene.get(key, "") or "").strip().lower()
        for key in ("text", "visual_goal", "keyword")
    )


def _winglet_subject(scene):
    value = _text(scene)
    return any(token in value for token in ("winglet", "wingtip", "윙렛", "날개 끝", "aircraft wing"))


def plan_explanation(scene):
    """Return a deterministic, evidence-bounded plan or None.

    V1 intentionally supports only the production-proven wing/winglet family.
    Unsupported mechanisms fail closed rather than receiving a plausible-looking
    but ungrounded diagram.
    """
    value = _text(scene)
    if not _winglet_subject(scene):
        return None

    if "vortex" in value or "소용돌이" in value:
        return {
            "scene_role": "mechanism",
            "subject": "winglet",
            "action": "vortex_reduction",
            "template": "WINGLET_VORTEX",
            "label": "날개 끝 소용돌이",
            "source_priority": ("annotated_verified_still", "explanatory_2d"),
        }
    if any(token in value for token in ("airflow", "공기", "흐름")):
        return {
            "scene_role": "mechanism",
            "subject": "winglet",
            "action": "airflow_direction",
            "template": "WINGLET_FLOW",
            "label": "공기 흐름",
            "source_priority": ("annotated_verified_still", "explanatory_2d"),
        }
    if any(token in value for token in ("fuel", "efficiency", "efficient", "longer flight", "멀리", "연료", "효율", "항속")):
        return {
            "scene_role": "result",
            "subject": "winglet",
            "action": "efficiency_result",
            "template": "WINGLET_RESULT",
            "label": "효율 개선의 결과",
            "source_priority": ("annotated_verified_still", "explanatory_2d"),
        }
    return None


def annotation_fact_safe(scene, plan):
    if not plan or not _winglet_subject(scene):
        return False
    value = _text(scene)
    template = plan.get("template")
    if template == "WINGLET_VORTEX":
        return "vortex" in value or "소용돌이" in value
    if template == "WINGLET_FLOW":
        return any(token in value for token in ("airflow", "공기", "흐름"))
    if template == "WINGLET_RESULT":
        return any(token in value for token in ("fuel", "efficiency", "efficient", "longer flight", "멀리", "연료", "효율", "항속"))
    return False


def _font(size):
    candidates = (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    )
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _arrow(draw, start, end, width=14):
    draw.line((start, end), fill=(255, 255, 255, 235), width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 28
    for offset in (2.55, -2.55):
        point = (
            end[0] + head * math.cos(angle + offset),
            end[1] + head * math.sin(angle + offset),
        )
        draw.line((end, point), fill=(255, 255, 255, 235), width=width)


def _fit_cover(image):
    image = image.convert("RGB")
    scale = max(VIDEO_WIDTH / image.width, VIDEO_HEIGHT / image.height)
    size = (max(VIDEO_WIDTH, int(image.width * scale)), max(VIDEO_HEIGHT, int(image.height * scale)))
    image = image.resize(size, Image.Resampling.LANCZOS)
    left = max(0, (image.width - VIDEO_WIDTH) // 2)
    top = max(0, (image.height - VIDEO_HEIGHT) // 2)
    return image.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))


def _draw_concept_panel(frame, plan, progress):
    draw = ImageDraw.Draw(frame, "RGBA")
    # Keep explanation graphics in the upper third; the existing subtitle
    # safety selector can therefore prefer middle/bottom without overlap.
    panel = (72, 110, VIDEO_WIDTH - 72, 650)
    draw.rounded_rectangle(panel, radius=34, fill=(0, 0, 0, 145), outline=(255, 255, 255, 175), width=3)
    font = _font(54)
    small = _font(42)
    draw.text((112, 145), plan["label"], font=font, fill=(255, 255, 255, 245))

    y = 390
    # simple wing + upturned winglet silhouette
    draw.line((165, y, 730, y), fill=(235, 235, 235, 245), width=32)
    draw.line((730, y, 790, y - 150), fill=(235, 235, 235, 245), width=32)
    template = plan["template"]
    if template == "WINGLET_VORTEX":
        cx, cy = 855, y - 55
        radius = 105
        start = -0.8 + progress * 1.3
        points = []
        for i in range(32):
            a = start + i * 0.15
            r = radius * (0.45 + 0.55 * i / 31)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        draw.line(points, fill=(255, 255, 255, 225), width=12)
        _arrow(draw, points[-5], points[-1], width=10)
    elif template == "WINGLET_FLOW":
        for offset in (-95, -25, 45):
            _arrow(draw, (150, y + offset), (690, y + offset - 35), width=11)
    else:
        _arrow(draw, (170, 520), (900, 520), width=14)
        draw.text((300, 548), "원리 → 비행 효율의 결과", font=small, fill=(255, 255, 255, 235))
    return frame


def _render_clip(base_image, output_path, duration, plan):
    duration = max(1.0, float(duration))
    base = _fit_cover(base_image) if base_image is not None else Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (28, 31, 38))

    def make_frame(t):
        p = min(1.0, max(0.0, t / duration))
        # Distinct information transform: a small deterministic push-in plus
        # a different fact-bounded panel per information beat.
        zoom = 1.0 + 0.035 * p
        w = int(VIDEO_WIDTH / zoom)
        h = int(VIDEO_HEIGHT / zoom)
        left = max(0, (VIDEO_WIDTH - w) // 2)
        top = max(0, (VIDEO_HEIGHT - h) // 2)
        frame = base.crop((left, top, left + w, top + h)).resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        frame = _draw_concept_panel(frame, plan, p)
        return np.array(frame.convert("RGB"))

    clip = VideoClip(make_frame=make_frame, duration=duration)
    try:
        clip.write_videofile(
            str(output_path), fps=30, codec="libx264", audio=False,
            preset="veryfast", ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            logger=None,
        )
    finally:
        clip.close()


def _cached_verified_asset(scene):
    try:
        from video import still_image_fallback as still
        signatures = still._reuse_signatures(scene)
        for signature in signatures:
            cached = dict(still._VERIFIED_STILL_CACHE.get(signature) or {})
            path = Path(str(cached.get("image_path") or ""))
            if path.is_file():
                return path, str(cached.get("source_id") or "verified-still")
    except Exception:
        pass
    return None, None


def generate_visual_explanation_fallback(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    global _TRANSFORM_COUNT
    plan = plan_explanation(scene)
    if not annotation_fact_safe(scene, plan):
        print("[VisualExplanation] status=unsupported_or_fact_unsafe")
        return None
    if _TRANSFORM_COUNT >= MAX_EXPLANATION_TRANSFORMS_PER_VIDEO:
        print(f"[VisualExplanation] status=budget_exhausted count={_TRANSFORM_COUNT}")
        return None

    image_path, source_id = _cached_verified_asset(scene)
    source_type = "annotated_verified_still" if image_path else "explanatory_2d"
    asset_id = source_id or "deterministic-winglet-template-v1"
    information_signature = (asset_id, str(plan["template"]))
    if information_signature in _INFORMATION_SIGNATURES:
        print(f"[VisualExplanation] status=information_repeat_rejected source={asset_id} template={plan['template']}")
        return None

    _TRANSFORM_COUNT += 1
    base_image = Image.open(image_path).convert("RGB") if image_path else None
    _render_clip(base_image, output_path, duration, plan)
    digest = hashlib.sha256((asset_id + plan["template"]).encode("utf-8")).hexdigest()[:12]
    _INFORMATION_SIGNATURES.add(information_signature)
    print(
        f"[VisualExplanation] status=generated mode={source_type} template={plan['template']} "
        f"scene_role={plan['scene_role']} count={_TRANSFORM_COUNT} trigger={trigger_reason}"
    )
    return {
        "path": str(output_path),
        "provider": "visual_explanation",
        "source_type": source_type,
        "source_id": f"vx-{digest}",
        "source_asset_id": asset_id,
        "mode": "ANNOTATED_VERIFIED_STILL" if image_path else "EXPLANATORY_2D",
        "tier": 2,
        "visual_state": "TRUE",
        "anchor_matched": 2,
        "anchor_total": 2,
        "template_type": plan["template"],
        "scene_role": plan["scene_role"],
        "fact_evidence_reference": "scene_narration_and_existing_fact_gate",
        "protected_region": "upper_third",
        "annotation_type": "concept_panel",
        "additional_llm_calls": 0,
        "additional_vision_calls": 0,
    }
