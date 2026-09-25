import os
import sys
import tempfile
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _ImageClip:
    def __init__(self, image):
        self.image = image

    def set_start(self, value):
        self.start = value
        return self

    def set_duration(self, value):
        self.duration = value
        return self

    def set_position(self, value):
        self.position = value
        return self


moviepy = types.ModuleType("moviepy")
moviepy_editor = types.ModuleType("moviepy.editor")
moviepy_editor.ImageClip = _ImageClip
moviepy.editor = moviepy_editor
sys.modules.setdefault("moviepy", moviepy)
sys.modules.setdefault("moviepy.editor", moviepy_editor)

from PIL import Image

from quality.final_visual_semantic_qa import (
    record_final_visual_scene,
    reset_final_visual_semantic_report,
    validate_final_visual_semantic_qa,
)
from quality.visual_diversity_preflight import evaluate_visual_diversity


def _alpha_bbox(image):
    arr = np.asarray(image)
    alpha = arr[:, :, 3] if arr.ndim == 3 and arr.shape[2] >= 4 else None
    if alpha is None:
        return None
    ys, xs = np.where(alpha > 0)
    if not len(xs):
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _expect_final_qa_failure(scenes, expected_reason):
    try:
        validate_final_visual_semantic_qa(scenes)
    except RuntimeError:
        report = Path("final_visual_semantic_qa.json").read_text(encoding="utf-8")
        assert expected_reason in report, report
        return
    raise AssertionError("final visual QA should fail closed")


def _scene(text, keyword, visual_goal=None, role="mechanism"):
    return {
        "text": text,
        "keyword": keyword,
        "visual_goal": visual_goal or text,
        "role": role,
    }


def _lineage(
    idx,
    source,
    *,
    duration=2.0,
    mode="PEXELS_STOCK",
    motion_profile="",
    template_type="",
):
    return {
        "scene_index": idx,
        "accepted": True,
        "provider": "pexels",
        "source_id": source,
        "source_asset_id": source,
        "mode": mode,
        "template_type": template_type,
        "motion_profile": motion_profile,
        "visual_state": "TRUE",
        "duration": duration,
    }


def test_same_domain_wrong_phenomenon_fails_final_qa():
    with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        os.chdir(tmp)
        try:
            scenes = [
                _scene(
                    "비행기 날개는 하중을 받으면 실제로 휘어집니다.",
                    "aircraft wing bending load",
                    "날개가 하중 때문에 휘어지는 모습",
                )
            ]
            reset_final_visual_semantic_report()
            record_final_visual_scene(0, scenes[0]["keyword"], {
                "accepted": True,
                "mode": "SAME_DOMAIN_CONTEXTUAL_UNKNOWN",
                "tier": 4,
                "visual_state": "UNKNOWN",
                "anchor_matched": 2,
                "anchor_total": 2,
                "provider": "pexels",
                "source_id": "generic-airplane-cruise",
                "metadata": "airplane aircraft wing cruising clouds beauty shot",
            })
            _expect_final_qa_failure(scenes, "missing_required_visual_evidence")

            reset_final_visual_semantic_report()
            record_final_visual_scene(0, scenes[0]["keyword"], {
                "accepted": True,
                "mode": "SEMANTIC_COMPLETE_TRUE",
                "tier": 2,
                "visual_state": "TRUE",
                "anchor_matched": 2,
                "anchor_total": 2,
                "provider": "pexels",
                "source_id": "wing-flex-visible",
                "metadata": "aircraft wing flex bending deformation turbulence",
            })
            assert validate_final_visual_semantic_qa(scenes)["status"] == "PASS"
        finally:
            os.chdir(old)


def test_static_wing_and_cross_domain_related_keyword_fail():
    with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        os.chdir(tmp)
        try:
            twisting = [
                _scene(
                    "날개 끝은 공기력 때문에 살짝 비틀립니다.",
                    "aircraft wing twisting aerodynamic load",
                    "날개가 비틀리는 변형이 보이는 장면",
                )
            ]
            reset_final_visual_semantic_report()
            record_final_visual_scene(0, twisting[0]["keyword"], {
                "accepted": True,
                "mode": "SAME_DOMAIN_CONTEXTUAL_UNKNOWN",
                "tier": 4,
                "visual_state": "UNKNOWN",
                "anchor_matched": 2,
                "anchor_total": 2,
                "provider": "pexels",
                "source_id": "static-wing",
                "metadata": "aircraft wing static flight close up",
            })
            _expect_final_qa_failure(twisting, "missing_required_visual_evidence")

            bridge = [
                _scene(
                    "다리는 바람을 받으면 진동할 수 있습니다.",
                    "bridge oscillation wind motion",
                    "다리가 흔들리거나 진동하는 모습",
                )
            ]
            reset_final_visual_semantic_report()
            record_final_visual_scene(0, bridge[0]["keyword"], {
                "accepted": True,
                "mode": "RELATED_KEYWORD_CONTEXTUAL_UNKNOWN",
                "tier": 4,
                "visual_state": "UNKNOWN",
                "anchor_matched": 1,
                "anchor_total": 2,
                "provider": "pexels",
                "source_id": "heart-valve-motion",
                "metadata": "heart valve motion medical animation",
            })
            _expect_final_qa_failure(bridge, "missing_required_subject_anchor")
        finally:
            os.chdir(old)


def test_visual_beats_and_staleness_fail_closed():
    scenes = [
        _scene("훅: 날개가 휘어집니다.", "aircraft wing bending", role="hook"),
        _scene("그런데 왜 부러지지 않을까요?", "aircraft wing load", role="cause"),
        _scene("하중은 날개 전체에 분산됩니다.", "aircraft wing load distribution"),
    ]

    long_same_source = evaluate_visual_diversity(
        scenes,
        [
            _lineage(0, "aircraft-wing-generic", duration=3.5),
            _lineage(1, "aircraft-wing-generic", duration=3.2),
            _lineage(2, "different-evidence", duration=2.0),
        ],
    )
    assert long_same_source["pass"] is False, long_same_source
    assert any(
        group.get("group_type") == "continuous_source_duration"
        for group in long_same_source["repetition_groups"]
    ), long_same_source

    zoom_only_first5 = evaluate_visual_diversity(
        scenes,
        [
            _lineage(0, "aircraft-wing-generic", duration=1.8, motion_profile="zoom"),
            _lineage(1, "aircraft-wing-generic", duration=1.8, motion_profile="crop"),
            _lineage(2, "aircraft-wing-generic", duration=1.8, motion_profile="small_pan"),
        ],
    )
    assert zoom_only_first5["pass"] is False, zoom_only_first5
    assert zoom_only_first5["first5_meaningful_visual_beats"] < 2


def test_subtitle_safe_width_and_opening_frame_gate():
    from quality.final_render_integrity import assess_opening_frame_visual_safety
    from PIL import ImageFont
    from video import subtitle_engine as se

    original_font = se.get_korean_font
    se.get_korean_font = lambda size: ImageFont.load_default()
    try:
        image = se.render_subtitle_image(
            "The wing is not rigid because it is designed to flex under load"
        )
    finally:
        se.get_korean_font = original_font
    bbox = _alpha_bbox(image)
    assert bbox is not None
    assert bbox[2] - bbox[0] <= int(se.VIDEO_WIDTH * se.SUBTITLE_SAFE_WIDTH_RATIO), bbox
    assert bbox[0] >= int(se.VIDEO_WIDTH * 0.07), bbox
    assert bbox[2] <= int(se.VIDEO_WIDTH * 0.93), bbox

    black = np.zeros((1920, 1080, 3), dtype=np.uint8)
    unsafe = assess_opening_frame_visual_safety(
        black,
        subtitle_visible=True,
        timestamp=0.0,
    )
    assert unsafe["pass"] is False, unsafe
    assert unsafe["reason"] == "subtitle_on_black_or_empty_frame", unsafe

    visible = np.array(Image.new("RGB", (1080, 1920), (130, 140, 150)))
    visible[500:900, 260:820] = (230, 230, 230)
    safe = assess_opening_frame_visual_safety(
        visible,
        subtitle_visible=True,
        timestamp=0.0,
    )
    assert safe["pass"] is True, safe


def main():
    test_same_domain_wrong_phenomenon_fails_final_qa()
    print("CASE A/C same-domain phenomenon final QA: PASS")
    test_static_wing_and_cross_domain_related_keyword_fail()
    print("CASE B/H static action and related cross-domain final QA: PASS")
    test_visual_beats_and_staleness_fail_closed()
    print("CASE D/E first5 beats and continuous source staleness: PASS")
    test_subtitle_safe_width_and_opening_frame_gate()
    print("CASE F/G subtitle bbox and opening frame gate: PASS")
    print("VISUAL QUALITY PRODUCTION GATE REGRESSION: PASS")


if __name__ == "__main__":
    main()
