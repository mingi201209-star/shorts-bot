import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.visual_diversity_preflight import (
    evaluate_visual_diversity,
    plan_bounded_diversity_repair,
)
from quality.visual_diversity_context import (
    excluded_physical_assets,
    is_physical_asset_excluded,
)


def _scene(text, role="mechanism", keyword="aircraft wing winglet"):
    return {"text": text, "role": role, "keyword": keyword, "visual_goal": text}


def _lineage(index, source="still-winglet-a", *, template="", mode="REUSED_VERIFIED_STILL_MOTION", source_asset_id=""):
    return {
        "scene_index": index,
        "accepted": True,
        "provider": "openai_image",
        "source_id": source,
        "source_asset_id": source_asset_id,
        "mode": mode,
        "template_type": template,
        "visual_state": "TRUE",
    }


def main():
    scenes = [_scene(f"scene {i}") for i in range(12)]
    lineage = [_lineage(i, source=f"unique-{i}") for i in range(12)]
    for idx in (5, 7, 9, 10, 11):
        lineage[idx] = _lineage(idx)
    result = evaluate_visual_diversity(scenes, lineage)
    assert result["pass"] is False, result
    group = result["repetition_groups"][0]
    assert group["scene_indices"] == [5, 7, 9, 10, 11], group
    assert group["human_scene_numbers"] == [6, 8, 10, 11, 12], group
    assert group["count"] == 5 and group["severity"] == "high", group

    two = evaluate_visual_diversity(scenes[:2], [_lineage(0), _lineage(1)])
    assert two["pass"] is True, two

    same_template = evaluate_visual_diversity(
        scenes[:3],
        [_lineage(i, source_asset_id="still-winglet-a", template="WINGLET_FLOW", mode="ANNOTATED_VERIFIED_STILL") for i in range(3)],
    )
    assert same_template["pass"] is False, same_template

    transformed = evaluate_visual_diversity(
        [_scene("공기 흐름"), _scene("날개 끝 소용돌이"), _scene("효율 개선 결과", "result")],
        [
            _lineage(0, source="vx-flow", source_asset_id="still-winglet-a", template="WINGLET_FLOW", mode="ANNOTATED_VERIFIED_STILL"),
            _lineage(1, source="vx-vortex", source_asset_id="still-winglet-a", template="WINGLET_VORTEX", mode="ANNOTATED_VERIFIED_STILL"),
            _lineage(2, source="vx-result", source_asset_id="still-winglet-a", template="WINGLET_RESULT", mode="ANNOTATED_VERIFIED_STILL"),
        ],
    )
    assert transformed["pass"] is True, transformed

    zoom = evaluate_visual_diversity(
        scenes[:3],
        [
            _lineage(0, mode="REUSED_VERIFIED_STILL_MOTION"),
            _lineage(1, mode="REUSED_VERIFIED_STILL_MOTION_ZOOM"),
            _lineage(2, mode="REUSED_VERIFIED_STILL_MOTION_CROP"),
        ],
    )
    assert zoom["pass"] is False, zoom

    different = evaluate_visual_diversity(scenes[:3], [_lineage(i, source=f"still-{i}") for i in range(3)])
    assert different["pass"] is True, different

    transition = evaluate_visual_diversity(
        [_scene("핵심 설명"), _scene("전환", "transition"), _scene("분위기", "atmosphere")],
        [_lineage(i) for i in range(3)],
    )
    assert transition["pass"] is True, transition

    repairs = plan_bounded_diversity_repair(result, scenes, max_repairs=2)
    assert repairs == [], repairs
    assert result["capability_exhausted"] is True, result

    assert not is_physical_asset_excluded("still-winglet-a")
    with excluded_physical_assets({"still-winglet-a"}):
        assert is_physical_asset_excluded("still-winglet-a")
        assert not is_physical_asset_excluded("still-other")
    assert not is_physical_asset_excluded("still-winglet-a")

    repeated_text = [_scene("동일 문장"), _scene("동일 문장")]
    info = evaluate_visual_diversity(repeated_text, [_lineage(0, source="a"), _lineage(1, source="b")])
    assert info["pass"] is True, info
    assert info["information_beat_repetition"][0]["scene_indices"] == [0, 1], info

    print("VISUAL DIVERSITY PREFLIGHT V1 REGRESSION: PASS")


if __name__ == "__main__":
    main()
