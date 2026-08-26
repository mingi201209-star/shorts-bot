from pathlib import Path

PATH = Path("main.py")
text = PATH.read_text(encoding="utf-8")

if "VISUAL_QUALITY_V1_PRODUCTION" not in text:
    import_anchor = '''from quality.final_visual_semantic_qa import (
    reset_final_visual_semantic_report,
    validate_final_visual_semantic_qa,
)
'''
    import_block = import_anchor + '''
from quality.final_visual_director import (
    director_qa,
    infer_scene_role,
    selective_repair_plan,
    MAX_DIRECTOR_RECOVERY_ROUNDS,
)
import json
from pathlib import Path as _VisualQualityPath
'''
    if import_anchor not in text:
        raise RuntimeError("Visual Quality V1 requires final visual semantic QA hotfix first")
    text = text.replace(import_anchor, import_block, 1)

    render_anchor = '''        validate_final_render_integrity(
            final_path,
            script_data,
            expected_content_topic,
            content_manifest,
            total_duration,
        )

        # ====================================================
        # Telegram
'''
    replacement = '''        validate_final_render_integrity(
            final_path,
            script_data,
            expected_content_topic,
            content_manifest,
            total_duration,
        )

        # VISUAL_QUALITY_V1_PRODUCTION
        # Director QA runs only after a real final MP4 exists and consumes exact
        # selection lineage. It adds no API call or generation budget itself.
        def _visual_quality_observations():
            report = json.loads(_VisualQualityPath("final_visual_semantic_qa.json").read_text(encoding="utf-8"))
            lineage = {int(x.get("scene_index", -1)): x for x in report.get("scenes", [])}
            observations = []
            elapsed = 0.0
            for scene_index, scene_item in enumerate(scenes):
                role = infer_scene_role(scene_item, scene_index, len(scenes))
                item = lineage.get(scene_index, {})
                duration = float(scene_item.get("duration", 0.0) or 0.0)
                total = int(item.get("anchor_total", 0) or 0)
                matched = int(item.get("anchor_matched", 0) or 0)
                mode = str(item.get("mode") or "")
                hook_verified = mode == "EXISTING_STRICT_HOOK_GATE"
                full_anchor = total > 0 and matched >= total
                explanatory = 8.5 if full_anchor else (5.0 if role in {"setup", "transition", "atmosphere"} else 3.0)
                if hook_verified:
                    explanatory = max(explanatory, 6.0)
                generic = "CONTEXTUAL" in mode.upper() or "UNKNOWN_SAFE" in mode.upper()
                if generic and role in {"cause", "mechanism", "solution"}:
                    explanatory = min(explanatory, 4.0)
                observations.append({
                    "scene_index": scene_index, "role": role,
                    "source_id": item.get("source_id", ""),
                    "start_sec": round(elapsed, 3), "end_sec": round(elapsed + duration, 3),
                    "scores": {
                        "semantic_match": 9.0 if item.get("accepted", hook_verified) else 0.0,
                        "explanatory_power": explanatory,
                        "subject_prominence": 8.0 if (full_anchor or hook_verified) else 6.0,
                        "mobile_clarity": 9.0 if hook_verified else 8.0,
                        "hook_visual_strength": 8.0 if hook_verified else 7.0,
                        "payoff_visual_strength": 7.0 if (full_anchor or item.get("accepted")) else 5.0,
                        "artifact_risk": 1.0 if str(item.get("visual_state", "TRUE")).upper() != "FALSE" else 9.0,
                        "obstruction_risk": 1.0,
                    },
                })
                elapsed += duration
            return observations

        director_round = 0
        while True:
            director_result = director_qa(_visual_quality_observations())
            if director_result.get("overall_pass"):
                print(f"[DirectorQA] recovery_round={director_round} PASS")
                break
            repair = selective_repair_plan(director_result, director_round)
            if repair.get("status") == "HOLD":
                raise RuntimeError("VISUAL_QUALITY_DIRECTOR_HOLD recovery limit reached")
            if repair.get("subtitle_only") and not repair.get("scene_indexes"):
                # Never throw away a good visual for a subtitle-only defect.
                raise RuntimeError("VISUAL_QUALITY_SUBTITLE_RELOCATION_REQUIRED")
            repair_indexes = list(repair.get("scene_indexes") or [])[:2]
            if not repair_indexes:
                raise RuntimeError("VISUAL_QUALITY_DIRECTOR_HOLD no concrete repairable scene")
            print(f"[DirectorQA] recovery_round={director_round + 1} selective_repair scenes={repair_indexes}")
            # Narration, FACT and timing remain locked. Only failed Scene clips
            # are recreated; all healthy clips remain byte-identical inputs.
            for repair_index in repair_indexes:
                scene_clips[repair_index] = create_scene(repair_index, scenes[repair_index], create_voice)
            # Worker/process scene records are consolidated again so Director
            # evaluates the replacement lineage rather than the stale first pass.
            validate_final_visual_semantic_qa(scenes)
            final_path = render_final_video(scene_clips, output_path=content_manifest["output_path"])
            validate_final_render_integrity(
                final_path, script_data, expected_content_topic,
                content_manifest, total_duration,
            )
            director_round += 1
            if director_round >= MAX_DIRECTOR_RECOVERY_ROUNDS:
                final_check = director_qa(_visual_quality_observations())
                if not final_check.get("overall_pass"):
                    raise RuntimeError("VISUAL_QUALITY_DIRECTOR_HOLD recovery limit reached")
                print(f"[DirectorQA] recovery_round={director_round} PASS")
                break

        # ====================================================
        # Telegram
'''
    if render_anchor not in text:
        raise RuntimeError("Visual Quality V1 final-render anchor not found")
    text = text.replace(render_anchor, replacement, 1)
    PATH.write_text(text, encoding="utf-8")

print("VISUAL_QUALITY_V1_PRODUCTION installed")
