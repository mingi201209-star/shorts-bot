from pathlib import Path


ROOT = Path(__file__).resolve().parent
PATH = ROOT / "video/visual_explanation.py"
MARKER = "# RUN_33981204957_FLAP_DIRECTOR_REPAIR_V1"


PATCH = r'''
# RUN_33981204957_FLAP_DIRECTOR_REPAIR_V1
# Bounded deterministic repair for the exact flap family exposed by production
# Run 33981204957. Director thresholds, still-generation budgets, source-use
# caps, and verified-still rescue policy remain unchanged.
_RUN_33981204957_ORIGINAL_PLAN_EXPLANATION = plan_explanation
_RUN_33981204957_ORIGINAL_ANNOTATION_FACT_SAFE = annotation_fact_safe
_RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET = _cached_verified_asset
_RUN_33981204957_ORIGINAL_DRAW_CONCEPT_PANEL = _draw_concept_panel


def _run_33981204957_flap_subject(scene):
    value = _text(scene).replace("-", " ")
    return "flap" in value and any(token in value for token in ("aircraft", "wing", "비행기", "날개"))


def plan_explanation(scene):
    value = _text(scene).replace("-", " ")
    if _run_33981204957_flap_subject(scene):
        if any(token in value for token in ("camber", "lift", "drag", "캠버", "양력", "항력")):
            return {
                "scene_role": "mechanism",
                "subject": "flap",
                "action": "camber_change",
                "template": "FLAP_CAMBER",
                "label": "플랩 전개와 날개 형상",
                "source_priority": ("explanatory_2d",),
            }
        if any(token in value for token in ("trailing edge", "identity", "뒤쪽", "후연")):
            return {
                "scene_role": "mechanism",
                "subject": "flap",
                "action": "trailing_edge_identity",
                "template": "FLAP_TRAILING_EDGE_IDENTITY",
                "label": "날개 뒤쪽의 플랩",
                "source_priority": ("explanatory_2d",),
            }
    return _RUN_33981204957_ORIGINAL_PLAN_EXPLANATION(scene)


def annotation_fact_safe(scene, plan):
    if plan and plan.get("subject") == "flap" and _run_33981204957_flap_subject(scene):
        value = _text(scene).replace("-", " ")
        template = plan.get("template")
        if template == "FLAP_CAMBER":
            return any(token in value for token in ("camber", "lift", "drag", "캠버", "양력", "항력"))
        if template == "FLAP_TRAILING_EDGE_IDENTITY":
            return any(token in value for token in ("trailing edge", "identity", "뒤쪽", "후연"))
        return False
    return _RUN_33981204957_ORIGINAL_ANNOTATION_FACT_SAFE(scene, plan)


def _cached_verified_asset(scene):
    plan = plan_explanation(scene)
    # A Director repetition repair must create a genuinely distinct physical
    # explanatory asset. Do not disguise the already repeated verified still
    # with a new source_id; flap repair therefore uses the deterministic 2D
    # branch only.
    if plan and plan.get("subject") == "flap":
        return None, None
    return _RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET(scene)


def _draw_concept_panel(frame, plan, progress):
    template = str((plan or {}).get("template") or "")
    if template not in {"FLAP_CAMBER", "FLAP_TRAILING_EDGE_IDENTITY"}:
        return _RUN_33981204957_ORIGINAL_DRAW_CONCEPT_PANEL(frame, plan, progress)

    draw = ImageDraw.Draw(frame, "RGBA")
    panel = (72, 110, VIDEO_WIDTH - 72, 650)
    draw.rounded_rectangle(panel, radius=34, fill=(0, 0, 0, 145), outline=(255, 255, 255, 175), width=3)
    font = _font(54)
    small = _font(38)
    draw.text((112, 145), plan["label"], font=font, fill=(255, 255, 255, 245))

    # Deterministic side-view schematic: fixed wing section plus a visibly
    # hinged trailing-edge flap. It illustrates only relationships already
    # present in the scene text/visual goal; no extra factual claim is added.
    y = 390
    hinge_x = 700
    draw.line((170, y, hinge_x, y), fill=(235, 235, 235, 245), width=34)
    flap_end = (900, y + 95)
    draw.line((hinge_x, y, flap_end[0], flap_end[1]), fill=(255, 255, 255, 250), width=34)
    draw.ellipse((hinge_x - 13, y - 13, hinge_x + 13, y + 13), fill=(255, 255, 255, 250))

    if template == "FLAP_CAMBER":
        draw.text((180, 500), "캠버 변화", font=small, fill=(255, 255, 255, 235))
        _arrow(draw, (570, 500), (835, 545), width=10)
    else:
        draw.text((690, 520), "플랩", font=small, fill=(255, 255, 255, 235))
        _arrow(draw, (675, 535), (790, 470), width=10)
    return frame
'''


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("Run 33981204957 flap Director repair already installed")
        return
    required = (
        "def plan_explanation(scene):",
        "def annotation_fact_safe(scene, plan):",
        "def _cached_verified_asset(scene):",
        "def _draw_concept_panel(frame, plan, progress):",
        "def generate_visual_explanation_fallback(",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(f"Run 33981204957 visual explanation composition mismatch: {missing}")
    PATH.write_text(text.rstrip() + "\n\n" + PATCH.strip() + "\n", encoding="utf-8")
    print("✅ Run 33981204957 bounded flap Director repair installed; budgets and thresholds unchanged")


if __name__ == "__main__":
    main()
