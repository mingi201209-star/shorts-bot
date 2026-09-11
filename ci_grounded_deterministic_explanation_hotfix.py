from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "video/visual_explanation.py"
MARKER = "# GROUNDED_DETERMINISTIC_EXPLANATION_V1"
LINEAGE_MARKER = '        "presentation_variant": plan.get("presentation_variant", ""),\n'

# PHASE 5 (deterministic renderer) + PHASE 7 (Bounded Visual Escalation router
# integration), combined because the renderer lives inline in the same live
# production consumer file every prior template (WINGLET_*, CHEVRON_FLOW_MIXING,
# FLOW_INTERFACE, NOISE_REDUCTION_RESULT, FLAP_*, STATIC_WICK_*) already uses.
#
# Run 34604725427 Scene 5 authority: stock/reuse failed, still generation
# budget 2/2 exhausted, existing VisualExplanation was wing/winglet-only ->
# QUALITY/VISUAL SUPPLY HOLD. This adds exactly one new PRODUCE/
# DETERMINISTIC_EXPLANATION method (AIRCRAFT_WINDOW_STRESS_V1) to the same
# router chain already live in this file -- not a new independent pipeline,
# no still-budget/API/retry/threshold change, zero external LLM/Vision/AI
# image calls in the renderer itself.
#
# Run 34616204901 human QA then showed a presentation problem, not a grounding
# problem: three distinct claims rendered as effectively the same static split
# panel for ~20 seconds.  Keep the comparison semantics fixed, but make the
# presentation claim-aware and move the viewer's inspection point slightly.
# Rule: structure is fixed; viewpoint moves. No object morphing, no extra API.
_APPEND = r'''

# GROUNDED_DETERMINISTIC_EXPLANATION_V1
from video.aircraft_window_stress_grounding import supports_aircraft_window_stress_from_grounding
from video.aircraft_window_stress_signature import build_deterministic_explanation_params
from video.aircraft_window_stress_comparison import (
    LEFT_CAPTION,
    RIGHT_CAPTION,
    build_window_corner_comparison_segment,
    stable_comparison_segment_id,
)
from video.grounded_visual_template_registry import find_grounded_visual_template
from quality.grounded_deterministic_explanation import validate_deterministic_explanation_params_shape
from quality.visual_escalation_router import (
    EscalationMethod,
    RoutingAction,
    semantic_validate_routing_decision,
)

_GDE_ORIGINAL_PLAN_EXPLANATION = plan_explanation
_GDE_ORIGINAL_ANNOTATION_FACT_SAFE = annotation_fact_safe
_GDE_ORIGINAL_DRAW_CONCEPT_PANEL = _draw_concept_panel

_GDE_SUPPORTED_OWNED_CLAIM_IDS = frozenset({
    "squarish_window_stress_concentration",
    "rounded_window_stress_distribution",
    "squarish_window_fatigue_rupture",
})
_GDE_PRESENTATION_VARIANTS = {
    "squarish_window_stress_concentration": "LEFT_STRESS_INSPECTION",
    "rounded_window_stress_distribution": "RIGHT_FLOW_INSPECTION",
    "squarish_window_fatigue_rupture": "LEFT_FATIGUE_PAYOFF",
}
_GDE_SCENE_ROLES = {
    "squarish_window_stress_concentration": "mechanism",
    "rounded_window_stress_distribution": "mechanism",
    "squarish_window_fatigue_rupture": "result",
}


def _gde_build_plan(scene, eligibility):
    capability = find_grounded_visual_template(eligibility)
    if capability is None:
        return None

    segment_id = stable_comparison_segment_id(
        eligibility["canonical_subject_id"], eligibility["owned_claim_id"]
    )
    scene_id = 0
    for key in ("scene_id", "index"):
        raw = scene.get(key)
        if isinstance(raw, int) or (isinstance(raw, str) and raw.strip().isdigit()):
            scene_id = int(raw)
            break
    contract = build_window_corner_comparison_segment(
        scene_id=scene_id, comparison_segment_id=segment_id, start_sec=0.0, end_sec=6.0,
    )
    if contract is None:
        return None

    params = build_deterministic_explanation_params(eligibility, comparison_segment_id=segment_id)
    if params is None:
        return None
    shape = validate_deterministic_explanation_params_shape(params)
    if not shape.ok:
        return None

    decision = {
        "action": RoutingAction.PRODUCE,
        "method": EscalationMethod.DETERMINISTIC_EXPLANATION,
        "param_signature": params["param_signature"],
        "reason": "grounded window-corner contrast eligible; upstream stock/reuse/still exhausted",
    }
    outer = semantic_validate_routing_decision(decision)
    if not outer.ok:
        return None

    owned_claim_id = params["owned_claim_id"]
    presentation_variant = _GDE_PRESENTATION_VARIANTS.get(owned_claim_id)
    if not presentation_variant:
        return None

    print(
        "[VISUAL_ESCALATION_ROUTING] "
        "action=PRODUCE method=DETERMINISTIC_EXPLANATION "
        f"template={params['template_id']} evidence_source={params['evidence_source']} "
        f"canonical_subject_id={params['canonical_subject_id']} "
        f"owned_claim_id={owned_claim_id} "
        f"presentation_variant={presentation_variant} motion_profile=SUBTLE_INSPECTION "
        f"param_signature={params['param_signature']}"
    )

    return {
        "scene_role": _GDE_SCENE_ROLES[owned_claim_id],
        "subject": "aircraft_window_corner",
        "action": "window_corner_stress_contrast",
        "template": "AIRCRAFT_WINDOW_STRESS_V1",
        "label": "각진 창문 vs 둥근 창문의 응력 비교",
        "owned_claim_id": owned_claim_id,
        "canonical_subject_id": params["canonical_subject_id"],
        "evidence_source": params["evidence_source"],
        "param_signature": params["param_signature"],
        "comparison_segment_id": segment_id,
        "presentation_variant": presentation_variant,
        "motion_profile": "SUBTLE_INSPECTION",
        "_comparison_segment": contract,
        "_routing_decision": decision,
        "source_priority": ("explanatory_2d",),
    }


def plan_explanation(scene):
    eligibility = supports_aircraft_window_stress_from_grounding(scene)
    if eligibility:
        plan = _gde_build_plan(scene, eligibility)
        if plan is not None:
            return plan
    return _GDE_ORIGINAL_PLAN_EXPLANATION(scene)


def annotation_fact_safe(scene, plan):
    if plan and plan.get("template") == "AIRCRAFT_WINDOW_STRESS_V1":
        eligibility = supports_aircraft_window_stress_from_grounding(scene)
        return bool(
            eligibility
            and plan.get("owned_claim_id") in _GDE_SUPPORTED_OWNED_CLAIM_IDS
            and plan.get("evidence_source") == "TRUSTED_GROUNDING"
            and plan.get("_comparison_segment") is not None
            and plan.get("motion_profile") == "SUBTLE_INSPECTION"
            and plan.get("presentation_variant")
        )
    return _GDE_ORIGINAL_ANNOTATION_FACT_SAFE(scene, plan)


def _gde_ease(progress):
    p = min(1.0, max(0.0, float(progress)))
    return p * p * (3.0 - 2.0 * p)


def _gde_apply_subtle_inspection(overlay, plan, progress):
    """Move the composed explanation layer, never its semantic slots.

    LEFT remains LEFT and RIGHT remains RIGHT.  The transform is intentionally
    small enough to read as camera inspection rather than object motion.
    """
    if (plan or {}).get("motion_profile") != "SUBTLE_INSPECTION":
        return overlay

    eased = _gde_ease(progress)
    variant = str((plan or {}).get("presentation_variant") or "")
    scale = 1.0 + 0.022 * eased
    pan_x = 0.0
    pan_y = 0.0
    if variant == "LEFT_STRESS_INSPECTION":
        pan_x = 10.0 * eased
    elif variant == "RIGHT_FLOW_INSPECTION":
        pan_x = -10.0 * eased
    elif variant == "LEFT_FATIGUE_PAYOFF":
        pan_x = 7.0 * eased
        pan_y = -4.0 * eased

    width, height = overlay.size
    scaled_w = max(width, int(round(width * scale)))
    scaled_h = max(height, int(round(height * scale)))
    enlarged = overlay.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
    center_left = (scaled_w - width) // 2
    center_top = (scaled_h - height) // 2
    crop_left = int(round(center_left - pan_x))
    crop_top = int(round(center_top - pan_y))
    crop_left = max(0, min(crop_left, scaled_w - width))
    crop_top = max(0, min(crop_top, scaled_h - height))
    return enlarged.crop((crop_left, crop_top, crop_left + width, crop_top + height))


def _draw_concept_panel(frame, plan, progress):
    if (plan or {}).get("template") != "AIRCRAFT_WINDOW_STRESS_V1":
        return _GDE_ORIGINAL_DRAW_CONCEPT_PANEL(frame, plan, progress)

    base = frame.convert("RGBA")
    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    panel = (72, 110, VIDEO_WIDTH - 72, 650)
    draw.rounded_rectangle(panel, radius=34, fill=(0, 0, 0, 150), outline=(255, 255, 255, 175), width=3)
    font = _font(46)
    small = _font(34)
    detail = _font(28)
    draw.text((100, 138), plan["label"], font=font, fill=(255, 255, 255, 245))

    mid_x = VIDEO_WIDTH // 2
    draw.line((mid_x, 205, mid_x, 615), fill=(255, 255, 255, 120), width=4)

    claim_id = str(plan.get("owned_claim_id") or "")
    variant = str(plan.get("presentation_variant") or "")
    eased = _gde_ease(progress)
    pulse = 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, float(progress))))

    # LEFT: squarish corner -- concentrated stress burst.  Geometry never
    # changes sides; only emphasis and the small inspection transform change.
    lx, ly = 150, 460
    left_alpha = 245 if variant in {"LEFT_STRESS_INSPECTION", "LEFT_FATIGUE_PAYOFF"} else 165
    draw.line((lx, 250, lx, ly), fill=(230, 230, 230, left_alpha), width=24)
    draw.line((lx, ly, 420, ly), fill=(230, 230, 230, left_alpha), width=24)
    burst = 30 + (18 if variant == "LEFT_STRESS_INSPECTION" else 10) * pulse
    if variant == "LEFT_FATIGUE_PAYOFF":
        burst = 38 + 18 * pulse
    for deg in (195, 220, 245, 270, 295, 320):
        angle = math.radians(deg)
        ex = lx + burst * math.cos(angle)
        ey = ly + burst * math.sin(angle)
        draw.line((lx, ly, ex, ey), fill=(235, 90, 90, 240 if left_alpha > 200 else 150), width=8)
    if claim_id == "squarish_window_stress_concentration":
        draw.text((96, 510), "모서리 응력 집중", font=detail, fill=(255, 190, 190, 240))
    elif claim_id == "squarish_window_fatigue_rupture":
        # Directly grounded FAA claim: concentrated corner stress fatigued the
        # surrounding material.  Do not invent crack count/size or timing.
        for radius in (42, 55, 68):
            alpha = int(90 + 80 * eased)
            draw.ellipse((lx - radius, ly - radius, lx + radius, ly + radius), outline=(235, 90, 90, alpha), width=4)
        draw.text((96, 510), "응력 집중 → 재료 피로", font=detail, fill=(255, 190, 190, 240))
    draw.text((95, 555), LEFT_CAPTION, font=small, fill=(255, 255, 255, 235))

    # RIGHT: rounded corner -- stress flows around the curve.  The distribution
    # claim receives brighter moving arcs while the opposite claim stays visible
    # as comparison context.
    right_alpha = 245 if variant == "RIGHT_FLOW_INSPECTION" else 170
    draw.rounded_rectangle((660, 250, 930, 460), radius=95, outline=(230, 230, 230, right_alpha), width=24)
    cx, cy, r = 660 + 95, 460 - 95, 95
    shift = (18 if variant == "RIGHT_FLOW_INSPECTION" else 7) * eased
    for r_off in (-16, 0, 16):
        rr = r + r_off
        points = []
        for deg in range(88, 183, 8):
            angle = math.radians(deg + shift)
            points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
        draw.line(points, fill=(140, 205, 255, 240 if right_alpha > 200 else 150), width=7)
    if claim_id == "rounded_window_stress_distribution":
        draw.text((650, 510), "곡선을 따라 응력이 흐릅니다", font=detail, fill=(175, 220, 255, 240))
    draw.text((650, 555), RIGHT_CAPTION, font=small, fill=(255, 255, 255, 235))

    overlay = _gde_apply_subtle_inspection(overlay, plan, progress)
    return Image.alpha_composite(base, overlay)
'''


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ Grounded Deterministic Explanation V1 already installed")
        return
    if "def plan_explanation(scene):" not in text:
        raise RuntimeError("grounded deterministic explanation requires visual_explanation.plan_explanation")
    if "def annotation_fact_safe(scene, plan):" not in text:
        raise RuntimeError("grounded deterministic explanation requires visual_explanation.annotation_fact_safe")
    if "def _draw_concept_panel(frame, plan, progress):" not in text:
        raise RuntimeError("grounded deterministic explanation requires visual_explanation._draw_concept_panel")

    # Preserve the claim-aware presentation identity in normal Scene lineage so
    # Visual Diversity can tell a real variant change from three claim-specific
    # asset IDs that still look compositionally identical.
    if LINEAGE_MARKER not in text:
        lineage_needle = '        "template_type": plan["template"],\n        "scene_role": plan["scene_role"],\n'
        if text.count(lineage_needle) != 1:
            raise RuntimeError("grounded deterministic explanation lineage marker mismatch")
        text = text.replace(
            lineage_needle,
            '        "template_type": plan["template"],\n'
            '        "presentation_variant": plan.get("presentation_variant", ""),\n'
            '        "motion_profile": plan.get("motion_profile", ""),\n'
            '        "scene_role": plan["scene_role"],\n',
            1,
        )

    PATH.write_text(text.rstrip() + "\n" + _APPEND + "\n", encoding="utf-8")
    print("✅ Grounded Deterministic Explanation V1 (AIRCRAFT_WINDOW_STRESS_V1) wired into Bounded Visual Escalation")
    print("✅ AIRCRAFT_WINDOW_STRESS_V1 claim-aware SUBTLE_INSPECTION presentation enabled")


if __name__ == "__main__":
    main()
