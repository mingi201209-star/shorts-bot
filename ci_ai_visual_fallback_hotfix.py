from pathlib import Path

# 1) Extend the existing Hook vision response with generation-specific safety fields.
# This reuses the same vision call; it does not add a second verifier call.
path = Path("video/hook_visual_dominance.py")
text = path.read_text(encoding="utf-8")
if '"obvious_generation_artifact"' not in text:
    text = text.replace(
        '        "visible_components": [str(item).strip().lower() for item in payload.get("visible_components", []) if str(item).strip()],\n',
        '        "visible_components": [str(item).strip().lower() for item in payload.get("visible_components", []) if str(item).strip()],\n'
        '        "obvious_generation_artifact": bool(payload.get("obvious_generation_artifact", False)),\n'
        '        "factual_visual_contradiction": bool(payload.get("factual_visual_contradiction", False)),\n',
        1,
    )
    text = text.replace(
        '- visible_components: list ONLY concrete components actually visible in the supplied frames. Never infer a component from Hook text, query, title, tags, or metadata. Example: wing/cloud view from a window may have aircraft visible but window absent.\n',
        '- visible_components: list ONLY concrete components actually visible in the supplied frames. Never infer a component from Hook text, query, title, tags, or metadata. Example: wing/cloud view from a window may have aircraft visible but window absent.\n'
        '- obvious_generation_artifact: true only for clearly malformed geometry, impossible object continuity, severe visual corruption, or obvious synthetic failure.\n'
        '- factual_visual_contradiction: true only if the visible generated depiction clearly contradicts the narration/visual goal; do not invent hidden technical facts.\n',
        1,
    )
    text = text.replace(
        '  "visible_components": ["aircraft", "window"],\n  "reason": "short concrete explanation"\n',
        '  "visible_components": ["aircraft", "window"],\n  "obvious_generation_artifact": false,\n  "factual_visual_contradiction": false,\n  "reason": "short concrete explanation"\n',
        1,
    )
path.write_text(text, encoding="utf-8")

# 2) Allow only already-created local AI MP4s through the normal renderer handoff.
# Stock URLs retain the exact HTTP path. No arbitrary file URI support is added.
path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
if "AI_GENERATED_LOCAL_HANDOFF" not in text:
    old = '''def download_video(\n    video_url,\n    output_path,\n    requests_module=requests,\n):\n    \"\"\"영상 URL을 로컬 MP4로 저장한다.\"\"\"\n    if not video_url:\n        raise ValueError(\"다운로드할 영상 URL이 없습니다.\")\n\n    response = requests_module.get(\n'''
    new = '''def download_video(\n    video_url,\n    output_path,\n    requests_module=requests,\n):\n    \"\"\"영상 URL 또는 검증된 generated local MP4를 scene 파일로 저장한다.\"\"\"\n    if not video_url:\n        raise ValueError(\"다운로드할 영상 URL이 없습니다.\")\n\n    # AI_GENERATED_LOCAL_HANDOFF\n    local_path = Path(str(video_url))\n    if local_path.is_file():\n        if local_path.suffix.lower() != \".mp4\":\n            raise RuntimeError(\"generated local visual must be an MP4\")\n        target = Path(output_path)\n        target.write_bytes(local_path.read_bytes())\n        if not target.exists() or target.stat().st_size <= 0:\n            raise RuntimeError(f\"generated visual handoff failed: {output_path}\")\n        return output_path\n\n    response = requests_module.get(\n'''
    if old not in text:
        raise RuntimeError("download_video HTTP marker missing")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

# 3) Add the Sora fallback between component-relevant stock and same-domain contextual.
path = Path("video/hook_visual.py")
text = path.read_text(encoding="utf-8")
marker = "# HOOK_FALLBACK_QUALITY_FLOOR\n"
helper = r'''
# AI_VISUAL_SORA_FALLBACK

def _try_ai_generated_hook_visual(scene, scene_query, trigger_reason):
    from video.ai_visual_provider import generate_ai_visual

    semantic = concrete_visual_evidence(
        {"provider": "synthetic_context", "source_id": "required", "url": ""},
        scene_query,
    )
    required = list(semantic.get("required") or [])
    candidate = generate_ai_visual(
        scene,
        required_components=required,
        hook=True,
        trigger_reason=trigger_reason,
    )
    if candidate is None:
        return None

    try:
        dominance = evaluate_hook_subject_dominance(candidate, scene)
        register_visual_evidence(
            candidate,
            visible_components=dominance.get("visible_components", []),
            source="hook_dominance_vision_ai_generated",
            definitive=True,
        )
        visual = candidate_visible_component_evidence(candidate, scene_query)
        verified = bool(
            dominance.get("pass")
            and visual.get("state") == "TRUE"
            and not dominance.get("obvious_generation_artifact", False)
            and not dominance.get("factual_visual_contradiction", False)
        )
        print(
            "[AI_VISUAL] "
            f"generation_count=verified trigger_reason={trigger_reason} "
            f"scene_id={candidate.get('scene_id')} generation_status={'verified' if verified else 'rejected'}"
        )
        if not verified:
            return None
        candidate["_ai_visual_dominance"] = dominance
        candidate["_ai_visual_evidence"] = visual
        return candidate
    except Exception as exc:
        print(
            "[AI_VISUAL] "
            f"generation_count=verification trigger_reason={trigger_reason} "
            f"scene_id={candidate.get('scene_id')} generation_status=verification_failed "
            f"reason={type(exc).__name__}"
        )
        return None
'''
if "AI_VISUAL_SORA_FALLBACK" not in text:
    if marker not in text:
        raise RuntimeError("#28 Hook fallback marker missing")
    text = text.replace(marker, helper + "\n" + marker, 1)
if "evaluate_hook_subject_dominance" not in text:
    raise RuntimeError("existing Hook dominance verifier unavailable")

old = '''        candidate, quality, fallback_item = _choose_hook_fallback(fallback_scored, fallback_query)
        if candidate is not None:
            _mark_candidate_used(candidate)
            visual = quality.get('visual') or candidate_visible_component_evidence(candidate, fallback_query)
            mode = quality.get('label') or 'LAST_RESORT'
'''
new = '''        candidate, quality, fallback_item = _choose_hook_fallback(fallback_scored, fallback_query)
        if candidate is not None:
            if int((quality or {}).get('tier', 0)) <= 2:
                ai_candidate = _try_ai_generated_hook_visual(
                    scene,
                    fallback_query,
                    trigger_reason=f"stock_quality_floor_tier_{int((quality or {}).get('tier', 0))}",
                )
                if ai_candidate is not None:
                    candidate = ai_candidate
                    quality = {
                        'tier': 2.5,
                        'label': 'AI_GENERATED_VERIFIED',
                        'visual': ai_candidate.get('_ai_visual_evidence') or candidate_visible_component_evidence(ai_candidate, fallback_query),
                        'semantic': concrete_visual_evidence(ai_candidate, fallback_query),
                        'reuse': False,
                    }
                    fallback_item = {
                        'candidate': ai_candidate,
                        'scores': None,
                        'total_score': None,
                        'dominance': ai_candidate.get('_ai_visual_dominance'),
                    }
            _mark_candidate_used(candidate)
            visual = quality.get('visual') or candidate_visible_component_evidence(candidate, fallback_query)
            mode = quality.get('label') or 'LAST_RESORT'
'''
if old not in text:
    raise RuntimeError("#28 fallback selection block missing")
text = text.replace(old, new, 1)
text = text.replace(
    "                'reuse': bool(candidate.get('_safe_reuse')),\n",
    "                'reuse': bool(candidate.get('_safe_reuse')),\n"
    "                'source_type': candidate.get('source_type', 'stock'),\n"
    "                'generation_id': candidate.get('generation_id'),\n"
    "                'prompt_hash': candidate.get('prompt_hash'),\n",
    1,
)
path.write_text(text, encoding="utf-8")

print("✅ Bounded Sora AI visual fallback applied")
