from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "video/visual_explanation.py"
DOWNLOADER_PATH = ROOT / "video/video_downloader.py"
MARKER = "# GROUNDED_DETERMINISTIC_EXPLANATION_V1"
WINDOW_STOCK_MARKER = "# WINDOW_HUMAN_VISUAL_QUALITY_V1"
LINEAGE_MARKER = '        "presentation_variant": plan.get("presentation_variant", ""),\n'

# Grounded deterministic aircraft-window explanation.  Run 34625637738 proved
# that semantic correctness alone was not enough for human viewing quality:
# Scenes 1-2 accepted aircraft-window queries whose selected footage had
# visual_state=UNKNOWN, while Scenes 3-5 still looked like one small repeated
# split panel.  Keep grounding/budgets unchanged, but make the deterministic
# presentation large and claim-specific and reject UNKNOWN stock for this
# closed aircraft-window subject family so the existing fallback chain can act.
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
        scene_id=scene_id,
        comparison_segment_id=segment_id,
        start_sec=0.0,
        end_sec=6.0,
    )
    if contract is None:
        return None

    params = build_deterministic_explanation_params(
        eligibility, comparison_segment_id=segment_id
    )
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
    if (plan or {}).get("motion_profile") != "SUBTLE_INSPECTION":
        return overlay

    eased = _gde_ease(progress)
    variant = str((plan or {}).get("presentation_variant") or "")
    scale = 1.0 + 0.026 * eased
    pan_x = 0.0
    pan_y = 0.0
    if variant == "LEFT_STRESS_INSPECTION":
        pan_x = 13.0 * eased
    elif variant == "RIGHT_FLOW_INSPECTION":
        pan_x = -13.0 * eased
    elif variant == "LEFT_FATIGUE_PAYOFF":
        pan_x = 9.0 * eased
        pan_y = -5.0 * eased

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


def _gde_draw_sharp_corner(draw, lx, ly, arm, width, alpha, burst, pulse, fatigue=False):
    draw.line((lx, ly - arm, lx, ly), fill=(238, 238, 238, alpha), width=width)
    draw.line((lx, ly, lx + arm, ly), fill=(238, 238, 238, alpha), width=width)
    ray = burst + int(26 * pulse)
    for deg in (195, 220, 245, 270, 295, 320):
        angle = math.radians(deg)
        ex = lx + ray * math.cos(angle)
        ey = ly + ray * math.sin(angle)
        draw.line((lx, ly, ex, ey), fill=(245, 92, 92, min(245, alpha)), width=max(7, width // 4))
    if fatigue:
        for radius in (72, 100, 128):
            ring_alpha = int(80 + 100 * pulse)
            draw.ellipse(
                (lx - radius, ly - radius, lx + radius, ly + radius),
                outline=(245, 92, 92, ring_alpha),
                width=5,
            )


def _gde_draw_rounded_window(draw, box, alpha, flow_alpha, progress):
    x1, y1, x2, y2 = box
    radius = int(min(x2 - x1, y2 - y1) * 0.30)
    draw.rounded_rectangle(box, radius=radius, outline=(238, 238, 238, alpha), width=30)
    cx = x1 + radius
    cy = y2 - radius
    base_r = radius
    shift = 20 * _gde_ease(progress)
    for r_off in (-28, 0, 28):
        rr = base_r + r_off
        points = []
        for deg in range(88, 184, 6):
            angle = math.radians(deg + shift)
            points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
        draw.line(points, fill=(135, 205, 255, flow_alpha), width=9)


def _draw_concept_panel(frame, plan, progress):
    if (plan or {}).get("template") != "AIRCRAFT_WINDOW_STRESS_V1":
        return _GDE_ORIGINAL_DRAW_CONCEPT_PANEL(frame, plan, progress)

    base = frame.convert("RGBA")
    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rounded_rectangle(
        (48, 86, VIDEO_WIDTH - 48, 1390),
        radius=42,
        fill=(5, 9, 17, 236),
        outline=(255, 255, 255, 150),
        width=3,
    )

    title_font = _font(54)
    label_font = _font(40)
    detail_font = _font(34)
    claim_id = str(plan.get("owned_claim_id") or "")
    variant = str(plan.get("presentation_variant") or "")
    pulse = 0.5 - 0.5 * math.cos(
        math.pi * min(1.0, max(0.0, float(progress)))
    )

    if variant == "LEFT_STRESS_INSPECTION":
        draw.text((92, 132), "각진 모서리에 응력이 몰립니다", font=title_font, fill=(255, 255, 255, 250))
        _gde_draw_sharp_corner(draw, 185, 835, 430, 40, 250, 78, pulse)
        draw.text((105, 950), "각진 모서리", font=label_font, fill=(255, 225, 225, 245))
        draw.text((105, 1012), "응력이 한 지점에 집중", font=detail_font, fill=(255, 165, 165, 245))
        _gde_draw_rounded_window(draw, (735, 405, 945, 660), 120, 110, progress)
        draw.text((730, 705), "둥근 모서리", font=detail_font, fill=(200, 210, 220, 210))
        insight = "초기 Comet의 각진 창문 모서리에는 높은 응력이 집중됐습니다"

    elif variant == "RIGHT_FLOW_INSPECTION":
        draw.text((92, 132), "둥근 모서리는 응력을 흘려보냅니다", font=title_font, fill=(255, 255, 255, 250))
        _gde_draw_sharp_corner(draw, 145, 590, 180, 22, 115, 38, pulse)
        draw.text((92, 730), "각진 모서리", font=detail_font, fill=(210, 180, 180, 190))
        _gde_draw_rounded_window(draw, (390, 330, 945, 920), 250, 245, progress)
        draw.text((470, 990), "곡선을 따라 응력이 분산", font=label_font, fill=(175, 225, 255, 250))
        insight = "현대의 둥근·타원형 창문은 모서리에 쌓이는 응력을 줄입니다"

    else:
        draw.text((92, 132), "응력 집중이 반복되면 재료가 피로해집니다", font=title_font, fill=(255, 255, 255, 250))
        _gde_draw_sharp_corner(draw, 205, 820, 420, 40, 250, 92, pulse, fatigue=True)
        draw.text((110, 972), "응력 집중 → 재료 피로", font=label_font, fill=(255, 170, 170, 250))
        _gde_draw_rounded_window(draw, (750, 420, 950, 655), 105, 95, progress)
        draw.text((745, 700), "둥근 모서리", font=detail_font, fill=(200, 210, 220, 195))
        insight = "각진 창문 모서리의 높은 응력은 주변 재료를 피로하게 했습니다"

    draw.rounded_rectangle(
        (88, 1140, VIDEO_WIDTH - 88, 1315),
        radius=28,
        fill=(255, 255, 255, 18),
        outline=(255, 255, 255, 65),
        width=2,
    )
    draw.text((120, 1195), insight, font=detail_font, fill=(245, 245, 245, 238))

    # V2.1 comparison semantics are still carried by _comparison_segment. The
    # renderer only changes emphasis/scale, never swaps LEFT/RIGHT meaning.
    overlay = _gde_apply_subtle_inspection(overlay, plan, progress)
    return Image.alpha_composite(base, overlay)
'''

_DOWNLOADER_APPEND = r'''

# WINDOW_HUMAN_VISUAL_QUALITY_V1
_window_hq_original_choose_best_candidate = choose_best_candidate


def _window_hq_query(query):
    words = set(normalize_search_query(query).replace("-", " ").split())
    aviation = bool(words & {"aircraft", "airplane", "aviation", "plane"})
    window = bool(words & {"window", "windows", "pane", "panes"})
    return aviation and window


def _window_hq_candidate_ok(candidate, query):
    if not candidate or not _window_hq_query(query):
        return True
    visual = candidate_visible_component_evidence(candidate, query)
    compatibility = candidate_anchor_compatibility(candidate, query)
    state = str(visual.get("state") or "UNKNOWN").upper()
    matched = int(compatibility.get("matched", 0) or 0)
    total = int(compatibility.get("total", 0) or 0)
    return state == "TRUE" and (total < 2 or matched == total)


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    global _LAST_FINAL_VISUAL_SELECTION
    selected = _window_hq_original_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
    query = str(subject_filter_query or "")
    if historical or not selected or not _window_hq_query(query):
        return selected
    if _window_hq_candidate_ok(selected, query):
        return selected

    visual = candidate_visible_component_evidence(selected, query)
    compatibility = candidate_anchor_compatibility(selected, query)
    _LAST_FINAL_VISUAL_SELECTION = {
        "accepted": False,
        "mode": "WINDOW_HUMAN_VISUAL_QUALITY_REJECT",
        "tier": 99,
        "visual_state": str(visual.get("state") or "UNKNOWN").upper(),
        "anchor_matched": int(compatibility.get("matched", 0) or 0),
        "anchor_total": int(compatibility.get("total", 0) or 0),
        "provider": str(selected.get("provider") or ""),
        "source_id": selected.get("source_id", selected.get("id")),
        "metadata": _candidate_metadata(selected),
    }
    print(
        "[WINDOW_HUMAN_VISUAL_QUALITY_REJECT] "
        f"provider={selected.get('provider', '')} "
        f"source_id={selected.get('source_id', selected.get('id', ''))} "
        f"visual_state={_LAST_FINAL_VISUAL_SELECTION['visual_state']} "
        f"anchors={_LAST_FINAL_VISUAL_SELECTION['anchor_matched']}/"
        f"{_LAST_FINAL_VISUAL_SELECTION['anchor_total']}"
    )
    return None
'''


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER not in text:
        if "def plan_explanation(scene):" not in text:
            raise RuntimeError("grounded deterministic explanation requires visual_explanation.plan_explanation")
        if "def annotation_fact_safe(scene, plan):" not in text:
            raise RuntimeError("grounded deterministic explanation requires visual_explanation.annotation_fact_safe")
        if "def _draw_concept_panel(frame, plan, progress):" not in text:
            raise RuntimeError("grounded deterministic explanation requires visual_explanation._draw_concept_panel")

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
        print("✅ Grounded Deterministic Explanation V1 wired into Bounded Visual Escalation")
        print("✅ AIRCRAFT_WINDOW_STRESS_V1 large claim-aware SUBTLE_INSPECTION presentation enabled")
    else:
        print("ℹ️ Grounded Deterministic Explanation V1 already installed")

    downloader = DOWNLOADER_PATH.read_text(encoding="utf-8")
    if WINDOW_STOCK_MARKER not in downloader:
        required = (
            "def choose_best_candidate(",
            "def candidate_visible_component_evidence(",
            "def candidate_anchor_compatibility(",
        )
        missing = [item for item in required if item not in downloader]
        if missing:
            raise RuntimeError(
                "window human visual quality requires final downloader contracts: "
                + ", ".join(missing)
            )
        DOWNLOADER_PATH.write_text(
            downloader.rstrip() + "\n" + _DOWNLOADER_APPEND + "\n",
            encoding="utf-8",
        )
        print("✅ Aircraft-window UNKNOWN stock is rejected before fallback selection")
    else:
        print("ℹ️ Aircraft-window human visual quality gate already installed")


if __name__ == "__main__":
    main()
