from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "video/visual_explanation.py"
MARKER = "# GROUNDED_DETERMINISTIC_EXPLANATION_V1"

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
# Appended (not anchor-patched) at the very end of whatever
# plan_explanation/annotation_fact_safe/_draw_concept_panel currently are,
# exactly matching the established wrapper-chain pattern already used by
# every one of the templates listed above -- so this hotfix has no fragile
# dependency on any other hotfix's exact injected text and is safe regardless
# of chain-application order, as long as it runs after
# ci_writer_observable_opening_hotfix.py (which installs the last upstream
# wrapper layer, STATIC_WICK_VISUAL_EXPLANATION_V1).
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

    print(
        "[VISUAL_ESCALATION_ROUTING] "
        "action=PRODUCE method=DETERMINISTIC_EXPLANATION "
        f"template={params['template_id']} evidence_source={params['evidence_source']} "
        f"canonical_subject_id={params['canonical_subject_id']} "
        f"owned_claim_id={params['owned_claim_id']} "
        f"param_signature={params['param_signature']}"
    )

    return {
        "scene_role": "result",
        "subject": "aircraft_window_corner",
        "action": "window_corner_stress_contrast",
        "template": "AIRCRAFT_WINDOW_STRESS_V1",
        "label": "각진 창문 vs 둥근 창문의 응력 비교",
        "owned_claim_id": params["owned_claim_id"],
        "canonical_subject_id": params["canonical_subject_id"],
        "evidence_source": params["evidence_source"],
        "param_signature": params["param_signature"],
        "comparison_segment_id": segment_id,
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
        )
    return _GDE_ORIGINAL_ANNOTATION_FACT_SAFE(scene, plan)


def _draw_concept_panel(frame, plan, progress):
    if (plan or {}).get("template") != "AIRCRAFT_WINDOW_STRESS_V1":
        return _GDE_ORIGINAL_DRAW_CONCEPT_PANEL(frame, plan, progress)

    draw = ImageDraw.Draw(frame, "RGBA")
    panel = (72, 110, VIDEO_WIDTH - 72, 650)
    draw.rounded_rectangle(panel, radius=34, fill=(0, 0, 0, 150), outline=(255, 255, 255, 175), width=3)
    font = _font(46)
    small = _font(34)
    draw.text((100, 138), plan["label"], font=font, fill=(255, 255, 255, 245))

    mid_x = VIDEO_WIDTH // 2
    draw.line((mid_x, 205, mid_x, 615), fill=(255, 255, 255, 120), width=4)

    # LEFT: squarish corner -- concentrated stress burst (sharp, tight cluster).
    lx, ly = 150, 460
    draw.line((lx, 250, lx, ly), fill=(230, 230, 230, 240), width=24)
    draw.line((lx, ly, 420, ly), fill=(230, 230, 230, 240), width=24)
    burst = 30 + 16 * progress
    for deg in (195, 220, 245, 270, 295, 320):
        angle = math.radians(deg)
        ex = lx + burst * math.cos(angle)
        ey = ly + burst * math.sin(angle)
        draw.line((lx, ly, ex, ey), fill=(235, 90, 90, 235), width=8)
    draw.text((95, 555), LEFT_CAPTION, font=small, fill=(255, 255, 255, 235))

    # RIGHT: rounded corner -- stress flowing smoothly around the curve.
    draw.rounded_rectangle((660, 250, 930, 460), radius=95, outline=(230, 230, 230, 240), width=24)
    cx, cy, r = 660 + 95, 460 - 95, 95
    shift = 14 * progress
    for r_off in (-16, 0, 16):
        rr = r + r_off
        points = []
        for deg in range(88, 183, 8):
            angle = math.radians(deg + shift)
            points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
        draw.line(points, fill=(140, 205, 255, 225), width=7)
    draw.text((650, 555), RIGHT_CAPTION, font=small, fill=(255, 255, 255, 235))
    return frame
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
    PATH.write_text(text.rstrip() + "\n" + _APPEND + "\n", encoding="utf-8")
    print("✅ Grounded Deterministic Explanation V1 (AIRCRAFT_WINDOW_STRESS_V1) wired into Bounded Visual Escalation")


if __name__ == "__main__":
    main()
