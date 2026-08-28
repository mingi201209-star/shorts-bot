from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} marker mismatch count={count}")
    return text.replace(old, new, 1)


qa_path = Path("quality/final_visual_semantic_qa.py")
qa = qa_path.read_text(encoding="utf-8")
qa = replace_once(
    qa,
    '''            "provider": str(selection.get("provider") or ""),
            "source_id": str(selection.get("source_id") or ""),
            "metadata": str(selection.get("metadata") or "")[:500],
''',
    '''            "provider": str(selection.get("provider") or ""),
            "source_id": str(selection.get("source_id") or ""),
            "physical_signature": str(selection.get("physical_signature") or ""),
            "source_asset_id": str(selection.get("source_asset_id") or ""),
            "template_type": str(selection.get("template_type") or ""),
            "metadata": str(selection.get("metadata") or "")[:500],
''',
    "final visual physical lineage",
)
qa_path.write_text(qa, encoding="utf-8")

still_path = Path("video/still_image_fallback.py")
still = still_path.read_text(encoding="utf-8")
if "from quality.visual_diversity_context import is_physical_asset_excluded" not in still:
    still = replace_once(
        still,
        "from config import OPENAI_KEY\n",
        "from config import OPENAI_KEY\nfrom quality.visual_diversity_context import is_physical_asset_excluded\n",
        "still exclusion import",
    )
still = replace_once(
    still,
    '''        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        image_path = Path(str(cached.get("image_path") or ""))
''',
    '''        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        if is_physical_asset_excluded(cached.get("source_id")):
            print(
                f"[VISUAL_DIVERSITY_EXCLUDE] scene={_scene_id(scene)} "
                f"source_id={cached.get('source_id', '')}"
            )
            continue
        image_path = Path(str(cached.get("image_path") or ""))
''',
    "still repair exclusion",
)
still_path.write_text(still, encoding="utf-8")

engine_path = Path("video/video_engine.py")
engine = engine_path.read_text(encoding="utf-8")
engine = replace_once(
    engine,
    '''                    "source_id": still_result.get("source_id", "generated-still"),
                    "metadata": " | ".join(part for part in metadata_parts if part),
''',
    '''                    "source_id": still_result.get("source_id", "generated-still"),
                    "source_asset_id": still_result.get("source_asset_id", still_result.get("source_id", "generated-still")),
                    "template_type": still_result.get("template_type", ""),
                    "metadata": " | ".join(part for part in metadata_parts if part),
''',
    "visual explanation physical lineage",
)
engine_path.write_text(engine, encoding="utf-8")

director_path = Path("quality/final_visual_director.py")
director = director_path.read_text(encoding="utf-8")
if "FINAL_DIRECTOR_QA_REPORT_V1" not in director:
    director = replace_once(
        director,
        "from collections import Counter\n",
        "from collections import Counter\nimport json\nfrom pathlib import Path\n",
        "director report imports",
    )
    director = replace_once(
        director,
        '''    for issue in deduped:
        print(f"[DirectorQA] FAIL scene={issue['scene_index']} reason={issue['type']}")
    return payload
''',
        '''    for issue in deduped:
        print(f"[DirectorQA] FAIL scene={issue['scene_index']} reason={issue['type']}")
    # FINAL_DIRECTOR_QA_REPORT_V1
    Path("final_director_qa.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload
''',
        "director report persistence",
    )
director_path.write_text(director, encoding="utf-8")

main_path = Path("main.py")
main = main_path.read_text(encoding="utf-8")
if "VISUAL_DIVERSITY_PREFLIGHT_V1" not in main:
    anchor = '''        validate_final_visual_semantic_qa(scenes)

        # ====================================================
        # Duration
'''
    block = '''        validate_final_visual_semantic_qa(scenes)

        # VISUAL_DIVERSITY_PREFLIGHT_V1
        from quality.visual_diversity_preflight import (
            evaluate_visual_diversity,
            plan_bounded_diversity_repair,
            write_visual_diversity_report,
        )
        from quality.visual_diversity_context import excluded_physical_assets
        from pathlib import Path as _DiversityPath
        import json as _diversity_json

        def _run_diversity_preflight():
            semantic = _diversity_json.loads(
                _DiversityPath("final_visual_semantic_qa.json").read_text(encoding="utf-8")
            )
            result = evaluate_visual_diversity(scenes, semantic.get("scenes", []))
            write_visual_diversity_report(result)
            for group in result.get("repetition_groups", []):
                if group.get("severity") == "high":
                    print(
                        f"[VisualDiversity] FAIL asset={group.get('asset_id')} "
                        f"scenes={group.get('human_scene_numbers')} count={group.get('count')}"
                    )
            for info in result.get("information_beat_repetition", []):
                print(
                    f"[VisualDiversity] information_repeat "
                    f"scenes={info.get('human_scene_numbers')}"
                )
            return result

        diversity_result = _run_diversity_preflight()
        if not diversity_result.get("pass"):
            diversity_repairs = plan_bounded_diversity_repair(
                diversity_result, scenes, max_repairs=2
            )
            write_visual_diversity_report(diversity_result)
            if diversity_repairs:
                print(
                    f"[VisualDiversity] bounded_repair "
                    f"scenes={[x['human_scene_number'] for x in diversity_repairs]}"
                )
                for repair_spec in diversity_repairs:
                    repair_index = int(repair_spec["scene_index"])
                    with excluded_physical_assets({repair_spec["excluded_physical_asset_id"]}):
                        scene_clips[repair_index] = create_scene(
                            repair_index, scenes[repair_index], create_voice
                        )
                validate_final_visual_semantic_qa(scenes)
                diversity_result = _run_diversity_preflight()
            if not diversity_result.get("pass"):
                write_visual_diversity_report(diversity_result)
                reason = "capability exhausted" if diversity_result.get("capability_exhausted") else "repetition remains"
                raise RuntimeError(
                    "VISUAL_DIVERSITY_PREFLIGHT_HOLD " + reason
                )
        print("[VisualDiversity] PASS")

        # ====================================================
        # Duration
'''
    main = replace_once(main, anchor, block, "pre-render diversity boundary")
main_path.write_text(main, encoding="utf-8")

print("VISUAL_DIVERSITY_PREFLIGHT_V1 installed")
