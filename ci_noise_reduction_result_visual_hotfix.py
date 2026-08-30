from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "# NOISE_REDUCTION_RESULT_VISUAL_V1"


def main():
    # Reuse the established #257/#258 architecture and install it first when
    # this focused hotfix is exercised in isolation. No new subsystem/calls.
    from ci_grounded_explanatory_visual_supply_hotfix import main as install_grounded_explanation

    install_grounded_explanation()

    path = ROOT / "video/visual_explanation.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1" not in text:
        raise RuntimeError("noise-reduction result requires grounded explanatory visual supply")

    text = text.rstrip() + r'''


# NOISE_REDUCTION_RESULT_VISUAL_V1
# Run 33307762835: deterministic primary-result supply after stock/still fail-close.
# This wrapper reuses VisualExplanation's existing budget, rendering, lineage,
# subtitle-safe upper panel, and zero-call behavior.
from video.grounded_explanatory_visual import noise_reduction_result_supported as _noise_result_supported

_noise_result_previous_plan_explanation = plan_explanation
_noise_result_previous_annotation_fact_safe = annotation_fact_safe
_noise_result_previous_draw_concept_panel = _draw_concept_panel


def plan_explanation(scene):
    if _noise_result_supported(scene):
        required_groups = required_explanatory_groups(scene)
        return {
            "scene_role": "result",
            "subject": "aircraft_engine_chevron",
            "action": "noise_reduction",
            "template": "NOISE_REDUCTION_RESULT",
            "label": "셰브론 결과: 소음 감소",
            "required_explanatory_groups": list(required_groups),
            "required_subject_anchors": ["aircraft", "engine"],
            "owned_claim_id": "noise_reduction",
            "causal_role": "primary_result",
            "canonical_subject_continuity": "jet_engine_chevron_family",
            "forbidden_claim_ids": [
                "chevron_flow_mixing", "drag_reduction", "fuel_efficiency",
                "stability", "thrust_improvement", "performance_improvement",
            ],
            "source_priority": ("explanatory_2d",),
        }
    return _noise_result_previous_plan_explanation(scene)


def annotation_fact_safe(scene, plan):
    if plan and plan.get("template") == "NOISE_REDUCTION_RESULT":
        return bool(
            _noise_result_supported(scene)
            and plan.get("owned_claim_id") == "noise_reduction"
            and plan.get("causal_role") == "primary_result"
            and set(plan.get("required_explanatory_groups") or []) == {"noise", "reduction"}
            and {"aircraft", "engine"}.issubset(set(plan.get("required_subject_anchors") or []))
            and "chevron_flow_mixing" in set(plan.get("forbidden_claim_ids") or [])
        )
    return _noise_result_previous_annotation_fact_safe(scene, plan)


def _noise_result_wave_points(x0, x1, center_y, amplitude, phase):
    points = []
    span = max(1, x1 - x0)
    for step in range(49):
        ratio = step / 48.0
        x = x0 + int(span * ratio)
        y = center_y + int(amplitude * math.sin((ratio * math.pi * 5.0) + phase))
        points.append((x, y))
    return points


def _draw_concept_panel(frame, plan, progress):
    if plan.get("template") != "NOISE_REDUCTION_RESULT":
        return _noise_result_previous_draw_concept_panel(frame, plan, progress)

    draw = ImageDraw.Draw(frame, "RGBA")
    panel = (72, 110, VIDEO_WIDTH - 72, 650)
    draw.rounded_rectangle(
        panel, radius=34, fill=(0, 0, 0, 150),
        outline=(255, 255, 255, 175), width=3,
    )
    font = _font(54)
    small = _font(38)
    draw.text((112, 145), plan["label"], font=font, fill=(255, 255, 255, 245))

    # Same rear jet-engine/chevron family used by the mechanism scenes. The
    # drawing states only subject continuity; it does not re-explain flow/mixing.
    draw.line((135, 335, 355, 335), fill=(220, 220, 220, 235), width=22)
    draw.ellipse(
        (285, 285, 575, 515), fill=(82, 86, 94, 245),
        outline=(238, 238, 238, 235), width=5,
    )
    draw.ellipse(
        (395, 330, 560, 475), fill=(30, 33, 40, 255),
        outline=(230, 230, 230, 220), width=4,
    )
    chevron_points = [
        (560, 342), (592, 360), (560, 380), (592, 400),
        (560, 420), (592, 440), (560, 462),
    ]
    draw.line(chevron_points, fill=(255, 255, 255, 250), width=9)

    # Qualitative acoustic-output comparison only. No dB values, numeric axes,
    # invented measurements, flow arrows, or new mechanism claims.
    phase = float(progress) * 1.2
    strong = _noise_result_wave_points(635, 965, 330, 56, phase)
    weak = _noise_result_wave_points(635, 965, 455, 20, phase)
    draw.line(strong, fill=(245, 245, 245, 235), width=10)
    draw.line(weak, fill=(185, 185, 185, 230), width=8)
    draw.text((630, 245), "소음 출력", font=small, fill=(255, 255, 255, 230))
    draw.text((630, 360), "감소", font=small, fill=(255, 255, 255, 230))
    draw.text((630, 500), "정량값 없이 크기만 비교", font=small, fill=(220, 220, 220, 205))
    return frame
'''

    path.write_text(text + "\n", encoding="utf-8")
    print("✅ NOISE_REDUCTION_RESULT deterministic explanatory visual installed")


if __name__ == "__main__":
    main()
