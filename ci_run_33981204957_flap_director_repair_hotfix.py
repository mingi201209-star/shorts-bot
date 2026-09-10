from pathlib import Path


ROOT = Path(__file__).resolve().parent
PATH = ROOT / "video/visual_explanation.py"
MARKER = "# RUN_33981204957_FLAP_DIRECTOR_REPAIR_V1"


PATCH = r'''
# RUN_33981204957_FLAP_DIRECTOR_REPAIR_V1
# Bounded deterministic repair for the exact flap family exposed by production
# Run 33981204957 and the deployment-stage counterexample from Run 34460549351.
# Director thresholds, still-generation budgets, source-use caps, and verified-
# still rescue policy remain unchanged.
_RUN_33981204957_ORIGINAL_PLAN_EXPLANATION = plan_explanation
_RUN_33981204957_ORIGINAL_ANNOTATION_FACT_SAFE = annotation_fact_safe
_RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET = _cached_verified_asset
_RUN_33981204957_ORIGINAL_DRAW_CONCEPT_PANEL = _draw_concept_panel


def _run_33981204957_flap_subject(scene):
    value = _text(scene).replace("-", " ")
    return "flap" in value and any(token in value for token in ("aircraft", "wing", "비행기", "날개"))


def _run_34460549351_flap_deployment_signal(scene):
    value = _text(scene).replace("-", " ")
    # Keep this narrower than generic Korean "펼치" wording because the proven
    # camber Scene 3 also says "플랩을 펼치면". The production opening carries an
    # explicit deployment-stage visual goal/keyword, which is the safe trigger.
    return any(token in value for token in (
        "flap deployment", "deployment stage", "deployment sequence",
        "flap deploy stage", "플랩 전개 단계", "플랩 전개 장면",
    ))


def plan_explanation(scene):
    value = _text(scene).replace("-", " ")
    if _run_33981204957_flap_subject(scene):
        if "identity" in value:
            return {
                "scene_role": "mechanism",
                "subject": "flap",
                "action": "trailing_edge_identity",
                "template": "FLAP_TRAILING_EDGE_IDENTITY",
                "label": "날개 뒤쪽의 플랩",
                "source_priority": ("explanatory_2d",),
            }
        if any(token in value for token in ("camber", "lift", "drag", "캠버", "양력", "항력")):
            return {
                "scene_role": "mechanism",
                "subject": "flap",
                "action": "camber_change",
                "template": "FLAP_CAMBER",
                "label": "플랩 전개와 날개 형상",
                "source_priority": ("explanatory_2d",),
            }
        if _run_34460549351_flap_deployment_signal(scene):
            return {
                "scene_role": "hook",
                "subject": "flap",
                "action": "deployment_sequence",
                "template": "FLAP_DEPLOYMENT",
                "label": "플랩 전개",
                "source_priority": ("explanatory_2d",),
            }
        if any(token in value for token in ("trailing edge", "뒤쪽", "후연")):
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
        if template == "FLAP_DEPLOYMENT":
            return _run_34460549351_flap_deployment_signal(scene)
        return False
    return _RUN_33981204957_ORIGINAL_ANNOTATION_FACT_SAFE(scene, plan)


def _cached_verified_asset(scene):
    plan = plan_explanation(scene)
    if plan and plan.get("subject") == "flap":
        return None, None
    return _RUN_33981204957_ORIGINAL_CACHED_VERIFIED_ASSET(scene)


def _draw_concept_panel(frame, plan, progress):
    template = str((plan or {}).get("template") or "")
    if template not in {"FLAP_CAMBER", "FLAP_TRAILING_EDGE_IDENTITY", "FLAP_DEPLOYMENT"}:
        return _RUN_33981204957_ORIGINAL_DRAW_CONCEPT_PANEL(frame, plan, progress)

    draw = ImageDraw.Draw(frame, "RGBA")
    panel = (72, 110, VIDEO_WIDTH - 72, 650)
    draw.rounded_rectangle(panel, radius=34, fill=(0, 0, 0, 145), outline=(255, 255, 255, 175), width=3)
    font = _font(54)
    small = _font(38)
    draw.text((112, 145), plan["label"], font=font, fill=(255, 255, 255, 245))

    y = 390
    hinge_x = 700
    draw.line((170, y, hinge_x, y), fill=(235, 235, 235, 245), width=34)
    draw.ellipse((hinge_x - 13, y - 13, hinge_x + 13, y + 13), fill=(255, 255, 255, 250))

    if template == "FLAP_DEPLOYMENT":
        # Show state change itself, not camber/lift or identity information.
        # A faint stowed flap plus an animated deployed flap makes this render
        # physically/informationally distinct from the two existing templates.
        draw.line((hinge_x, y, 900, y), fill=(220, 220, 220, 120), width=18)
        angle = math.radians(8.0 + 27.0 * min(1.0, max(0.0, progress)))
        length = 220
        flap_end = (
            int(hinge_x + length * math.cos(angle)),
            int(y + length * math.sin(angle)),
        )
        draw.line((hinge_x, y, flap_end[0], flap_end[1]), fill=(255, 255, 255, 250), width=34)
        draw.text((180, 500), "접힘 → 전개", font=small, fill=(255, 255, 255, 235))
        _arrow(draw, (555, 510), (820, 545), width=10)
        return frame

    flap_end = (900, y + 95)
    draw.line((hinge_x, y, flap_end[0], flap_end[1]), fill=(255, 255, 255, 250), width=34)
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
    else:
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

    # Standalone flap regression runs before Visual Explanation Retrieval V1.
    # Production invokes this module again from the proven late composition hook;
    # install the static-wick repairs only on that final pass.
    engine_path = ROOT / "video/video_engine.py"
    engine_source = engine_path.read_text(encoding="utf-8") if engine_path.exists() else ""
    if "VISUAL_EXPLANATION_RETRIEVAL_V1" in engine_source:
        from ci_static_wick_visual_explanation_hotfix import main as _patch_static_wick_visual
        _patch_static_wick_visual()
        from ci_static_wick_fallback_provenance_hotfix import main as _patch_static_wick_fallback_provenance
        _patch_static_wick_fallback_provenance()
        from ci_static_wick_local_visual_handoff_hotfix import main as _patch_static_wick_local_handoff
        _patch_static_wick_local_handoff()
    else:
        print("⏭️ Static-wick visual repair deferred until final visual composition")


if __name__ == "__main__":
    main()
