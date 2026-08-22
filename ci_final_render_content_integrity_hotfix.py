from pathlib import Path

PATH = Path("main.py")
text = PATH.read_text(encoding="utf-8")

IMPORT_NEEDLE = '''from video.renderer import (\n    render_final_video,\n    validate_total_duration,\n)\n'''
IMPORT_REPLACEMENT = IMPORT_NEEDLE + '''\nfrom quality.final_render_integrity import (\n    assert_content_identity,\n    begin_final_render_integrity,\n    validate_final_render_integrity,\n)\n'''

if "FINAL_RENDER_CONTENT_INTEGRITY_V1" not in text:
    if IMPORT_NEEDLE not in text:
        raise RuntimeError("renderer import anchor not found")
    text = text.replace(IMPORT_NEEDLE, IMPORT_REPLACEMENT, 1)

    PASS_NEEDLE = '''            if status == "PASS":\n\n                final_script = (\n                    quality_result[\n                        "script_data"\n                    ]\n                )\n'''
    PASS_REPLACEMENT = '''            if status == "PASS":\n\n                # FINAL_RENDER_CONTENT_INTEGRITY_V1\n                # Quality rewrite/review must never silently change the selected topic.\n                expected_final_topic = (\n                    quality_result.get("fallback_to_topic")\n                    if quality_result.get("fallback_used", False)\n                    else current_topic\n                )\n                assert_content_identity(\n                    expected_final_topic,\n                    quality_result["script_data"],\n                    stage="quality_pass",\n                )\n\n                final_script = (\n                    quality_result[\n                        "script_data"\n                    ]\n                )\n                final_script["_content_identity_topic"] = expected_final_topic\n'''
    if PASS_NEEDLE not in text:
        raise RuntimeError("quality PASS anchor not found")
    text = text.replace(PASS_NEEDLE, PASS_REPLACEMENT, 1)

    PROD_NEEDLE = '''        # ====================================================\n        # Production\n        # ====================================================\n\n        scene_clips = (\n            generate_scenes(\n                scenes\n            )\n        )\n'''
    PROD_REPLACEMENT = '''        # ====================================================\n        # Production\n        # ====================================================\n\n        expected_content_topic = str(\n            script_data.get("_content_identity_topic", script_data.get("topic", ""))\n        ).strip()\n        assert_content_identity(\n            expected_content_topic,\n            script_data,\n            stage="pre_scene_production",\n        )\n        content_manifest = begin_final_render_integrity(\n            script_data,\n            expected_content_topic,\n        )\n\n        scene_clips = (\n            generate_scenes(\n                scenes\n            )\n        )\n'''
    if PROD_NEEDLE not in text:
        raise RuntimeError("production anchor not found")
    text = text.replace(PROD_NEEDLE, PROD_REPLACEMENT, 1)

    RENDER_NEEDLE = '''        final_path = (\n            render_final_video(\n                scene_clips\n            )\n        )\n\n        # ====================================================\n        # Telegram\n'''
    RENDER_REPLACEMENT = '''        final_path = (\n            render_final_video(\n                scene_clips,\n                output_path=content_manifest["output_path"],\n            )\n        )\n\n        validate_final_render_integrity(\n            final_path,\n            script_data,\n            expected_content_topic,\n            content_manifest,\n            total_duration,\n        )\n\n        # ====================================================\n        # Telegram\n'''
    if RENDER_NEEDLE not in text:
        raise RuntimeError("render anchor not found")
    text = text.replace(RENDER_NEEDLE, RENDER_REPLACEMENT, 1)

    PATH.write_text(text, encoding="utf-8")

print("FINAL_RENDER_CONTENT_INTEGRITY_V1 installed")
