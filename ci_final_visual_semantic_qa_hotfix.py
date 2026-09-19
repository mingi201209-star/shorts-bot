from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


def replace_between(text, start_marker, end_marker, replacement, error_label):
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{error_label} start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{error_label} end marker not found")
    return text[:start] + replacement + text[end:]


downloader = Path("video/video_downloader.py")
text = downloader.read_text(encoding="utf-8")
text = append_once(
    text,
    "FINAL_VISUAL_SELECTION_LINEAGE_V1",
    r'''
# FINAL_VISUAL_SELECTION_LINEAGE_V1
_LAST_FINAL_VISUAL_SELECTION = None
_final_visual_previous_choose_best_candidate = choose_best_candidate


def _final_visual_candidate_metadata(candidate):
    if "_candidate_metadata" in globals():
        return _candidate_metadata(candidate)
    candidate = dict(candidate or {})
    return " ".join(
        str(candidate.get(key) or "")
        for key in (
            "metadata", "title", "tags", "description", "page_url",
            "source_id", "id", "provider",
        )
    )


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    global _LAST_FINAL_VISUAL_SELECTION
    selected = _final_visual_previous_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
    if subject_filter_query and not historical:
        if selected is None:
            _LAST_FINAL_VISUAL_SELECTION = {
                "accepted": False,
                "mode": "NO_SEMANTICALLY_SAFE_CANDIDATE",
                "tier": 99,
            }
        else:
            if all(
                name in globals()
                for name in (
                    "general_scene_unknown_safe_tier",
                    "candidate_visible_component_evidence",
                    "candidate_anchor_compatibility",
                )
            ):
                tier, mode = general_scene_unknown_safe_tier(selected, subject_filter_query)
                visual = candidate_visible_component_evidence(selected, subject_filter_query)
                compatibility = candidate_anchor_compatibility(selected, subject_filter_query)
            else:
                tier, mode = 3, "LEGACY_SELECTION_LINEAGE"
                visual = {"state": "UNKNOWN"}
                compatibility = {"matched": 0, "total": 0}
            _LAST_FINAL_VISUAL_SELECTION = {
                "accepted": tier <= 4 and str(visual.get("state") or "UNKNOWN").upper() != "FALSE",
                "mode": mode,
                "tier": tier,
                "visual_state": str(visual.get("state") or "UNKNOWN").upper(),
                "anchor_matched": compatibility.get("matched", 0),
                "anchor_total": compatibility.get("total", 0),
                "provider": selected.get("provider", "pexels"),
                "source_id": selected.get("source_id", selected.get("id")),
                "metadata": _final_visual_candidate_metadata(selected),
            }
    return selected


def get_last_final_visual_selection():
    return dict(_LAST_FINAL_VISUAL_SELECTION or {})
''',
)
text = append_once(
    text,
    "FINAL_VISUAL_GENERATED_LINEAGE_SETTER_V1",
    r'''
# FINAL_VISUAL_GENERATED_LINEAGE_SETTER_V1
def set_last_final_visual_selection(selection):
    global _LAST_FINAL_VISUAL_SELECTION
    _LAST_FINAL_VISUAL_SELECTION = dict(selection or {})
    return dict(_LAST_FINAL_VISUAL_SELECTION)
''',
)
downloader.write_text(text, encoding="utf-8")


engine = Path("video/video_engine.py")
text = engine.read_text(encoding="utf-8")
import_needle = "from video.subtitle_engine import (\n"
import_replacement = (
    "from video.video_downloader import get_last_final_visual_selection\n"
    "from quality.final_visual_semantic_qa import record_final_visual_scene\n\n"
    "from quality.visual_semantic_contract import phenomenon_preserving_query\n\n"
    + import_needle
)
if "FINAL_VISUAL_SCENE_RECORD_V1" not in text:
    if import_needle not in text:
        raise RuntimeError("final visual QA video_engine import anchor not found")
    text = text.replace(import_needle, import_replacement, 1)
    search_needle = '''        if hook_scene_enabled:
'''
    search_replacement = '''        # PHENOMENON_PRESERVING_RETRIEVAL_QUERY_V1
        search_keyword = phenomenon_preserving_query(
            item,
            base_query=keyword,
        )
        if search_keyword != keyword.lower():
            print(
                "🧭 Phenomenon-preserving search: "
                f"{keyword} -> {search_keyword}"
            )

        if hook_scene_enabled:
'''
    if search_needle not in text:
        raise RuntimeError("phenomenon-preserving query anchor not found")
    text = text.replace(search_needle, search_replacement, 1)
    text = text.replace(
        "fetch_pexels_video(\n                        keyword",
        "fetch_pexels_video(\n                        search_keyword",
    )
    text = text.replace(
        "fetch_pexels_video(\n                    keyword",
        "fetch_pexels_video(\n                    search_keyword",
    )
    selection_needle = '''        # ====================================================
        # 4. 영상 다운로드
        # ====================================================
'''
    selection_replacement = '''        # FINAL_VISUAL_SCENE_RECORD_V1
        record_final_visual_scene(
            idx,
            search_keyword,
            get_last_final_visual_selection(),
            hook_verified=hook_scene_enabled,
            duration=duration,
        )

''' + selection_needle
    if selection_needle not in text:
        raise RuntimeError("final visual QA selection anchor not found")
    text = text.replace(selection_needle, selection_replacement, 1)

if "STILL_IMAGE_MOTION_FALLBACK_V1" not in text:
    import_anchor = "from video.video_downloader import get_last_final_visual_selection\n"
    import_block = (
        "from video.video_downloader import get_last_final_visual_selection, set_last_final_visual_selection\n"
        "from video.still_image_fallback import generate_still_motion_fallback\n"
    )
    if import_anchor not in text:
        raise RuntimeError("still fallback final visual import anchor not found")
    text = text.replace(import_anchor, import_block, 1)

    # Later production hotfixes can change the exact wording/spacing of the
    # no-video RuntimeError. Anchor only on the stable control-flow line and
    # the next numbered section so installer ordering cannot break startup.
    no_video_replacement = '''        # STILL_IMAGE_MOTION_FALLBACK_V1
        if not video_url:
            still_result = generate_still_motion_fallback(
                item,
                output_path=vertical_video_path,
                duration=duration,
                trigger_reason="no_semantically_safe_stock",
            )
            if still_result:
                # Reuse the existing generated-local-MP4 handoff installed by
                # the bounded AI visual hotfix. Normal download/vertical paths
                # remain untouched for all stock candidates.
                video_url = vertical_video_path
                set_last_final_visual_selection({
                    "accepted": True,
                    "mode": still_result.get("mode", "GENERATED_STILL_MOTION_VERIFIED"),
                    "tier": int(still_result.get("tier", 3)),
                    "visual_state": still_result.get("visual_state", "TRUE"),
                    "anchor_matched": int(still_result.get("anchor_matched", 1)),
                    "anchor_total": int(still_result.get("anchor_total", 1)),
                    "provider": still_result.get("provider", "openai_image"),
                    "source_id": still_result.get("source_id", "generated-still"),
                    "source_asset_id": still_result.get("source_asset_id", still_result.get("source_id", "generated-still")),
                    "template_type": still_result.get("template_type", ""),
                    "presentation_variant": still_result.get("presentation_variant", ""),
                    "motion_profile": still_result.get("motion_profile", ""),
                    "visible_components": still_result.get("visible_components", []),
                    "visible_subject_groups": still_result.get("visible_subject_groups", {}),
                    "verification_evidence": still_result.get("verification_evidence", {}),
                    "current_scene_verification": still_result.get("current_scene_verification", {}),
                    "metadata": (
                        "verified generated still animated with slow zoom/pan and fade "
                        f"visible_components={still_result.get('visible_components', [])} "
                        f"verification={still_result.get('current_scene_verification', {})}"
                    ),
                })
                print(f"🖼️ STILL IMAGE MOTION FALLBACK scene={idx + 1}: {vertical_video_path}")
            else:
                raise RuntimeError(
                    "영상 후보가 없고 검증된 정지 이미지 fallback도 실패했습니다: "
                    f"{search_keyword}"
                )

'''
    text = replace_between(
        text,
        "        if not video_url:",
        "        # ====================================================\n        # 4. 영상 다운로드",
        no_video_replacement,
        "still fallback no-video block",
    )

# The still-image fallback replaces the whole no-video-to-download interval.
# Reinstall Scene lineage after that replacement so it cannot delete the call.
if "FINAL_VISUAL_SCENE_RECORD_V1" not in text:
    record_needle = '''        # ====================================================
        # 4. 영상 다운로드
        # ====================================================
'''
    record_block = '''        # FINAL_VISUAL_SCENE_RECORD_V1
        record_final_visual_scene(
            idx,
            search_keyword,
            get_last_final_visual_selection(),
            hook_verified=hook_scene_enabled,
        )

''' + record_needle
    if text.count(record_needle) != 1:
        raise RuntimeError("final visual QA post-fallback record anchor not unique")
    text = text.replace(record_needle, record_block, 1)

if text.count("FINAL_VISUAL_SCENE_RECORD_V1") != 1:
    raise RuntimeError("final visual QA Scene record was not installed exactly once")
engine.write_text(text, encoding="utf-8")


main = Path("main.py")
text = main.read_text(encoding="utf-8")
if "FINAL_VISUAL_SEMANTIC_QA_V1" not in text:
    import_needle = '''from quality.final_render_integrity import (
    assert_content_identity,
    begin_final_render_integrity,
    validate_final_render_integrity,
)
'''
    import_block = '''
from quality.final_visual_semantic_qa import (
    reset_final_visual_semantic_report,
    validate_final_visual_semantic_qa,
)
'''
    import_replacement = import_needle + import_block
    if "from quality.final_visual_semantic_qa import" not in text:
        if import_needle in text:
            text = text.replace(import_needle, import_replacement, 1)
        else:
            fallback_import_needle = '''from quality.budget_guard import (
    reset_budget,
    print_budget_status,
)
'''
            if fallback_import_needle not in text:
                raise RuntimeError("final visual QA main import anchor not found")
            text = text.replace(
                fallback_import_needle,
                fallback_import_needle + "\n" + import_block,
                1,
            )
    production_needle = '''        scene_clips = (
            generate_scenes(
                scenes
            )
        )
'''
    production_replacement = '''        # FINAL_VISUAL_SEMANTIC_QA_V1
        reset_final_visual_semantic_report()

''' + production_needle + '''
        # The exact clips selected for every rendered scene must pass before
        # the MP4 can be treated as a successful daily production.
        validate_final_visual_semantic_qa(scenes)
'''
    if production_needle not in text:
        raise RuntimeError("final visual QA production anchor not found")
    text = text.replace(production_needle, production_replacement, 1)
main.write_text(text, encoding="utf-8")

# Keep generated-still verification aligned with the actual dominance verifier
# contract after every other visual hotfix has finished mutating its modules.
from ci_still_image_verifier_contract_hotfix import main as _patch_still_image_verifier_contract
_patch_still_image_verifier_contract()

# Root Cause #3 (Run 34847558126): must run after ci_still_image_verifier_
# contract_hotfix.py above, which already rewrites _verify_motion_clip's full
# body. Running any earlier would have this installer's own text anchor win
# the race and break that later, more comprehensive rewrite's anchor match.
from ci_still_action_gate_hotfix import main as _patch_still_action_gate
_patch_still_action_gate()

from ci_still_vision_evidence_groups_hotfix import main as _patch_still_vision_evidence_groups
_patch_still_vision_evidence_groups()

from ci_still_vision_evidence_trace_hotfix import main as _patch_still_vision_evidence_trace
_patch_still_vision_evidence_trace()

print("FINAL_VISUAL_SEMANTIC_QA_V1 installed")
print("STILL_IMAGE_MOTION_FALLBACK_V1 installed")
