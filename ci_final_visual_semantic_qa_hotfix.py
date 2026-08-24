from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


downloader = Path("video/video_downloader.py")
text = downloader.read_text(encoding="utf-8")
text = append_once(
    text,
    "FINAL_VISUAL_SELECTION_LINEAGE_V1",
    r'''
# FINAL_VISUAL_SELECTION_LINEAGE_V1
_LAST_FINAL_VISUAL_SELECTION = None
_final_visual_previous_choose_best_candidate = choose_best_candidate


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
            tier, mode = general_scene_unknown_safe_tier(selected, subject_filter_query)
            visual = candidate_visible_component_evidence(selected, subject_filter_query)
            compatibility = candidate_anchor_compatibility(selected, subject_filter_query)
            _LAST_FINAL_VISUAL_SELECTION = {
                "accepted": tier <= 4 and str(visual.get("state") or "UNKNOWN").upper() != "FALSE",
                "mode": mode,
                "tier": tier,
                "visual_state": str(visual.get("state") or "UNKNOWN").upper(),
                "anchor_matched": compatibility.get("matched", 0),
                "anchor_total": compatibility.get("total", 0),
                "provider": selected.get("provider", "pexels"),
                "source_id": selected.get("source_id", selected.get("id")),
                "metadata": _candidate_metadata(selected),
            }
    return selected


def get_last_final_visual_selection():
    return dict(_LAST_FINAL_VISUAL_SELECTION or {})
''',
)
downloader.write_text(text, encoding="utf-8")


engine = Path("video/video_engine.py")
text = engine.read_text(encoding="utf-8")
import_needle = "from video.subtitle_engine import (\n"
import_replacement = (
    "from video.video_downloader import get_last_final_visual_selection\n"
    "from quality.final_visual_semantic_qa import record_final_visual_scene\n\n"
    + import_needle
)
if "FINAL_VISUAL_SCENE_RECORD_V1" not in text:
    if import_needle not in text:
        raise RuntimeError("final visual QA video_engine import anchor not found")
    text = text.replace(import_needle, import_replacement, 1)
    selection_needle = '''        # ====================================================
        # 4. 영상 다운로드
        # ====================================================
'''
    selection_replacement = '''        # FINAL_VISUAL_SCENE_RECORD_V1
        record_final_visual_scene(
            idx,
            keyword,
            get_last_final_visual_selection(),
            hook_verified=hook_scene_enabled,
        )

''' + selection_needle
    if selection_needle not in text:
        raise RuntimeError("final visual QA selection anchor not found")
    text = text.replace(selection_needle, selection_replacement, 1)
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
    import_replacement = import_needle + '''
from quality.final_visual_semantic_qa import (
    reset_final_visual_semantic_report,
    validate_final_visual_semantic_qa,
)
'''
    if import_needle not in text:
        raise RuntimeError("final visual QA main import anchor not found")
    text = text.replace(import_needle, import_replacement, 1)
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

print("FINAL_VISUAL_SEMANTIC_QA_V1 installed")
