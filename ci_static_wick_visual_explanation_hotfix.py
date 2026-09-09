from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "STATIC_WICK_VISUAL_EXPLANATION_V1"


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} mismatch count={count}")
    return text.replace(old, new, 1)


def patch_visual_explanation():
    path = ROOT / "video/visual_explanation.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "VISUAL_EXPLANATION_RETRIEVAL_V1" not in (ROOT / "video/video_engine.py").read_text(encoding="utf-8"):
        raise RuntimeError("static-wick visual repair requires Visual Explanation Retrieval V1")

    text = text.rstrip() + r'''


# STATIC_WICK_VISUAL_EXPLANATION_V1
_static_wick_previous_plan_explanation = plan_explanation
_static_wick_previous_annotation_fact_safe = annotation_fact_safe
_static_wick_previous_draw_concept_panel = _draw_concept_panel

_STATIC_WICK_CLAIMS = {
    "static_charge_dissipation": "STATIC_WICK_DISCHARGE",
    "static_wick_location_identity": "STATIC_WICK_LOCATION",
    "radio_interference_reduction": "STATIC_WICK_RF_RESULT",
}


def _static_wick_claim(scene):
    claim = str(scene.get("owned_claim_id") or "").strip().lower()
    if claim in _STATIC_WICK_CLAIMS:
        return claim
    value = _text(scene)
    if "static charge dissipation" in value or "정전기 방전기 작동 원리" in value:
        return "static_charge_dissipation"
    if "static wick location" in value or "정전기 방전기 위치" in value:
        return "static_wick_location_identity"
    if "radio interference reduction" in value or "무선 주파수 간섭 감소" in value:
        return "radio_interference_reduction"
    return ""


def is_static_wick_explanation_scene(scene):
    return bool(_static_wick_claim(scene))


def plan_explanation(scene):
    claim = _static_wick_claim(scene)
    if claim:
        template = _STATIC_WICK_CLAIMS[claim]
        labels = {
            "static_charge_dissipation": "정전기가 빠져나가는 방전 지점",
            "static_wick_location_identity": "날개·조종면 뒤 가장자리의 정전기 방전기",
            "radio_interference_reduction": "정전기 방전으로 무선 간섭 감소",
        }
        roles = {
            "static_charge_dissipation": "mechanism",
            "static_wick_location_identity": "location",
            "radio_interference_reduction": "result",
        }
        return {
            "scene_role": roles[claim],
            "subject": "aircraft_static_discharge_wick",
            "action": claim,
            "template": template,
            "label": labels[claim],
            "owned_claim_id": claim,
            "required_subject_anchors": ["aircraft", "wing", "static_wick"],
            "source_priority": ("explanatory_2d",),
        }
    return _static_wick_previous_plan_explanation(scene)


def annotation_fact_safe(scene, plan):
    claim = _static_wick_claim(scene)
    if claim:
        return bool(plan and plan.get("owned_claim_id") == claim and plan.get("template") == _STATIC_WICK_CLAIMS[claim])
    return _static_wick_previous_annotation_fact_safe(scene, plan)


def _draw_static_wick_aircraft(draw, y=390):
    # Minimal exterior aircraft/wing context. The thin rods are explicitly
    # attached to trailing-edge regions; no model-specific geometry is claimed.
    draw.line((150, y, 760, y), fill=(235, 235, 235, 245), width=34)
    draw.ellipse((250, y - 95, 540, y + 95), fill=(82, 86, 94, 245), outline=(238, 238, 238, 235), width=5)
    for x in (620, 700, 760):
        draw.line((x, y + 8, x + 42, y + 62), fill=(255, 255, 255, 250), width=7)
        draw.ellipse((x + 37, y + 56, x + 47, y + 66), fill=(255, 255, 255, 255))


def _draw_concept_panel(frame, plan, progress):
    template = str((plan or {}).get("template") or "")
    if template not in set(_STATIC_WICK_CLAIMS.values()):
        return _static_wick_previous_draw_concept_panel(frame, plan, progress)
    draw = ImageDraw.Draw(frame, "RGBA")
    panel = (72, 95, VIDEO_WIDTH - 72, 660)
    draw.rounded_rectangle(panel, radius=34, fill=(0, 0, 0, 150), outline=(255, 255, 255, 180), width=3)
    font = _font(50)
    small = _font(38)
    draw.text((108, 130), plan["label"], font=font, fill=(255, 255, 255, 245))
    _draw_static_wick_aircraft(draw, 385)

    if template == "STATIC_WICK_DISCHARGE":
        # Charge marks move from wing surface toward the visible wick tips.
        for i, x in enumerate((500, 565, 630)):
            dx = int(35 * progress)
            draw.text((x + dx, 300 + i * 24), "+", font=small, fill=(255, 255, 255, 235))
        for x in (662, 742, 802):
            _arrow(draw, (x - 20, 430), (x + 68, 505), width=7)
        draw.text((175, 535), "기체에 쌓인 전하 → 정전기 방전기 → 공기 중", font=small, fill=(255, 255, 255, 235))
    elif template == "STATIC_WICK_LOCATION":
        draw.line((570, 455, 900, 555), fill=(255, 255, 255, 120), width=3)
        draw.text((585, 535), "뒤 가장자리의 가느다란 돌기", font=small, fill=(255, 255, 255, 235))
    else:
        # Evidence-bounded result: show discharge at the wick and a separate
        # antenna/RF region with fewer interference marks; do not claim zero RF.
        for x in (665, 745, 805):
            _arrow(draw, (x - 20, 430), (x + 55, 495), width=6)
        draw.line((190, 555, 300, 555), fill=(235, 235, 235, 230), width=8)
        draw.line((245, 555, 245, 495), fill=(235, 235, 235, 230), width=8)
        for r in (28, 48, 68):
            draw.arc((245-r, 495-r, 245+r, 495+r), 205, 335, fill=(220, 220, 220, 190), width=4)
        draw.text((355, 535), "방전 위치를 통해 RF 간섭·잡음 감소에 도움", font=small, fill=(255, 255, 255, 235))
    return frame
'''
    path.write_text(text, encoding="utf-8")


def patch_generic_stock_fail_close():
    path = ROOT / "video/video_downloader.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    text = text.rstrip() + r'''


# STATIC_WICK_VISUAL_EXPLANATION_V1
_static_wick_previous_choose_best_candidate = choose_best_candidate


def _static_wick_explanatory_query(value):
    q = normalize_search_query(value)
    return any(token in q for token in (
        "static charge dissipation",
        "static wick location",
        "static radio interference reduction",
        "radio interference reduction",
    ))


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    if subject_filter_query and not historical and _static_wick_explanatory_query(subject_filter_query):
        # Run 34318241572 proved generic aircraft/wing stock can pass contextual
        # fallback while failing Director explanatory power. For these three
        # trusted static-wick facts, generic stock is not explanatory evidence.
        print(f"[STATIC_WICK_VISUAL] generic_stock_fail_close query={normalize_search_query(subject_filter_query)}")
        return None
    return _static_wick_previous_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
'''
    path.write_text(text, encoding="utf-8")


def patch_retrieval_priority():
    path = ROOT / "video/video_engine.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    import_anchor = "from video.visual_explanation import generate_visual_explanation_fallback\n"
    import_replacement = import_anchor + "from video.visual_explanation import is_static_wick_explanation_scene\n"
    text = _replace_once(text, import_anchor, import_replacement, "static-wick engine import")

    old = '''        if not video_url:\n            still_result = generate_still_motion_fallback(\n                item,\n                output_path=vertical_video_path,\n                duration=duration,\n                trigger_reason="no_semantically_safe_stock",\n            )\n            if not still_result:\n                # Do not increase the raw still-generation budget. Once the\n                # existing bounded still path is unavailable, try a zero-API\n                # explanation transform using a verified cached asset or one\n                # narrowly supported deterministic 2D template.\n                still_result = generate_visual_explanation_fallback(\n                    item,\n                    output_path=vertical_video_path,\n                    duration=duration,\n                    trigger_reason="raw_still_unavailable",\n                )\n'''
    new = '''        if not video_url:\n            # STATIC_WICK_VISUAL_EXPLANATION_V1\n            # Exact trusted static-wick facts have a zero-API deterministic\n            # explanatory renderer, so use it before spending still-generation\n            # budget. All unrelated scenes preserve the existing order.\n            if is_static_wick_explanation_scene(item):\n                still_result = generate_visual_explanation_fallback(\n                    item,\n                    output_path=vertical_video_path,\n                    duration=duration,\n                    trigger_reason="trusted_static_wick_explanation",\n                )\n            else:\n                still_result = generate_still_motion_fallback(\n                    item,\n                    output_path=vertical_video_path,\n                    duration=duration,\n                    trigger_reason="no_semantically_safe_stock",\n                )\n                if not still_result:\n                    # Do not increase the raw still-generation budget. Once the\n                    # existing bounded still path is unavailable, try a zero-API\n                    # explanation transform using a verified cached asset or one\n                    # narrowly supported deterministic 2D template.\n                    still_result = generate_visual_explanation_fallback(\n                        item,\n                        output_path=vertical_video_path,\n                        duration=duration,\n                        trigger_reason="raw_still_unavailable",\n                    )\n'''
    text = _replace_once(text, old, new, "static-wick retrieval priority")
    path.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")


def patch_lineage():
    path = ROOT / "ci_visual_explanation_retrieval_v1_hotfix.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    anchor = '''                    "metadata": " | ".join(part for part in metadata_parts if part),\n'''
    replacement = '''                    "metadata": " | ".join(part for part in metadata_parts if part),\n                    # STATIC_WICK_VISUAL_EXPLANATION_V1\n                    "source_asset_id": still_result.get("source_asset_id"),\n                    "template_type": still_result.get("template_type"),\n                    "scene_role": still_result.get("scene_role"),\n                    "owned_claim_id": still_result.get("owned_claim_id"),\n                    "protected_region": still_result.get("protected_region"),\n'''
    text = _replace_once(text, anchor, replacement, "static-wick lineage")
    path.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")


def main():
    patch_visual_explanation()
    patch_generic_stock_fail_close()
    patch_retrieval_priority()
    patch_lineage()
    print("STATIC_WICK_VISUAL_EXPLANATION_V1 installed")


if __name__ == "__main__":
    main()
