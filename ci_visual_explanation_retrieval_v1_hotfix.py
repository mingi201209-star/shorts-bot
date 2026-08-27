from pathlib import Path


engine = Path("video/video_engine.py")
text = engine.read_text(encoding="utf-8")
marker = "VISUAL_EXPLANATION_RETRIEVAL_V1"

if marker not in text:
    import_anchor = "from video.still_image_fallback import generate_still_motion_fallback\n"
    import_replacement = (
        import_anchor
        + "from video.visual_explanation import generate_visual_explanation_fallback\n"
    )
    if import_anchor not in text:
        raise RuntimeError("Visual Explanation import anchor not found")
    text = text.replace(import_anchor, import_replacement, 1)

    start_marker = "        # STILL_IMAGE_MOTION_FALLBACK_V1\n"
    end_marker = "        # FINAL_VISUAL_SCENE_RECORD_V1\n"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("Visual Explanation no-video block anchor not found")

    replacement = '''        # STILL_IMAGE_MOTION_FALLBACK_V1
        # VISUAL_EXPLANATION_RETRIEVAL_V1
        if not video_url:
            still_result = generate_still_motion_fallback(
                item,
                output_path=vertical_video_path,
                duration=duration,
                trigger_reason="no_semantically_safe_stock",
            )
            if not still_result:
                # Do not increase the raw still-generation budget. Once the
                # existing bounded still path is unavailable, try a zero-API
                # explanation transform using a verified cached asset or one
                # narrowly supported deterministic 2D template.
                still_result = generate_visual_explanation_fallback(
                    item,
                    output_path=vertical_video_path,
                    duration=duration,
                    trigger_reason="raw_still_unavailable",
                )

            if still_result:
                video_url = vertical_video_path
                metadata_parts = [
                    str(still_result.get("source_type", "verified_still_motion")),
                    str(still_result.get("template_type", "")),
                    str(still_result.get("annotation_type", "")),
                    str(still_result.get("protected_region", "")),
                    "llm_calls=0" if still_result.get("additional_llm_calls") == 0 else "",
                    "vision_calls=0" if still_result.get("additional_vision_calls") == 0 else "",
                ]
                set_last_final_visual_selection({
                    "accepted": True,
                    "mode": still_result.get("mode", "GENERATED_STILL_MOTION_VERIFIED"),
                    "tier": int(still_result.get("tier", 3)),
                    "visual_state": still_result.get("visual_state", "TRUE"),
                    "anchor_matched": int(still_result.get("anchor_matched", 1)),
                    "anchor_total": int(still_result.get("anchor_total", 1)),
                    "provider": still_result.get("provider", "openai_image"),
                    "source_id": still_result.get("source_id", "generated-still"),
                    "metadata": " | ".join(part for part in metadata_parts if part),
                })
                print(
                    f"[VisualExplanation] scene={idx + 1} source={still_result.get('source_type', 'verified_still_motion')} "
                    f"mode={still_result.get('mode', 'GENERATED_STILL_MOTION_VERIFIED')}"
                )
            else:
                raise RuntimeError(
                    "영상 후보가 없고 검증된 정지 이미지/설명 visual fallback도 실패했습니다: "
                    f"{keyword}"
                )

'''
    text = text[:start] + replacement + text[end:]

if text.count(marker) != 1:
    raise RuntimeError("Visual Explanation production marker must be installed exactly once")

engine.write_text(text, encoding="utf-8")
print("VISUAL_EXPLANATION_RETRIEVAL_V1 installed")
