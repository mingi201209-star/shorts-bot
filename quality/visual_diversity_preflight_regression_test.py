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


def _lineage(
    index,
    source="still-winglet-a",
    *,
    template="",
    mode="REUSED_VERIFIED_STILL_MOTION",
    source_asset_id="",
    presentation_variant="",
    motion_profile="",
):
    return {
        "scene_index": index,
        "accepted": True,
        "provider": "openai_image",
        "source_id": source,
        "source_asset_id": source_asset_id,
        "mode": mode,
        "template_type": template,
        "presentation_variant": presentation_variant,
        "motion_profile": motion_profile,
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

    # Run 34616204901 counterexample: claim-specific deterministic asset ids
    # must not hide three effectively identical uses of one explanation family.
    window_scenes = [
        _scene("각진 모서리 응력", keyword="aircraft window corner stress"),
        _scene("둥근 모서리 분산", keyword="aircraft window rounded stress"),
        _scene("응력 집중과 재료 피로", "result", keyword="aircraft window fatigue"),
    ]
    window_same_presentation = evaluate_visual_diversity(
        window_scenes,
        [
            _lineage(
                i,
                source=f"vx-window-{i}",
                source_asset_id=f"deterministic-window-claim-{i}",
                template="AIRCRAFT_WINDOW_STRESS_V1",
                mode="EXPLANATORY_2D",
            )
            for i in range(3)
        ],
    )
    assert window_same_presentation["pass"] is False, window_same_presentation
    presentation_failures = [
        group for group in window_same_presentation["repetition_groups"]
        if group.get("group_type") == "presentation_family"
        and group.get("severity") == "high"
    ]
    assert len(presentation_failures) == 1, window_same_presentation
    assert presentation_failures[0]["hard_repeat_count"] == 3

    # A real claim-aware treatment is allowed: same comparison template, but
    # three stable presentation identities and the same deterministic motion
    # profile. This is visual differentiation, not asset-id laundering.
    window_distinct_presentation = evaluate_visual_diversity(
        window_scenes,
        [
            _lineage(
                0,
                source="vx-window-left",
                source_asset_id="deterministic-window-claim-left",
                template="AIRCRAFT_WINDOW_STRESS_V1",
                mode="EXPLANATORY_2D",
                presentation_variant="LEFT_STRESS_INSPECTION",
                motion_profile="SUBTLE_INSPECTION",
            ),
            _lineage(
                1,
                source="vx-window-right",
                source_asset_id="deterministic-window-claim-right",
                template="AIRCRAFT_WINDOW_STRESS_V1",
                mode="EXPLANATORY_2D",
                presentation_variant="RIGHT_FLOW_INSPECTION",
                motion_profile="SUBTLE_INSPECTION",
            ),
            _lineage(
                2,
                source="vx-window-fatigue",
                source_asset_id="deterministic-window-claim-fatigue",
                template="AIRCRAFT_WINDOW_STRESS_V1",
                mode="EXPLANATORY_2D",
                presentation_variant="LEFT_FATIGUE_PAYOFF",
                motion_profile="SUBTLE_INSPECTION",
            ),
        ],
    )
    assert window_distinct_presentation["pass"] is True, window_distinct_presentation

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
