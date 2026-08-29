from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1"


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} mismatch count={count}")
    return text.replace(old, new, 1)


def patch_dominance_verifier():
    path = ROOT / "video/hook_visual_dominance.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_VERIFIER_CONTRACT_V1" not in text:
        raise RuntimeError("grounded explanatory verifier requires still verifier contract")

    anchor = "from quality.budget_guard import authorize_call, print_budget_status, record_usage\n"
    text = _replace_once(text, anchor, anchor + (
        "from video.grounded_explanatory_visual import (\n"
        "    generation_requirement, normalize_visible_explanatory_groups, required_explanatory_groups,\n"
        ")\n"
    ), "grounded explanatory verifier import")

    anchor = '''        "visible_components": [\n            str(component or "").strip().lower()\n            for component in (payload.get("visible_components") or [])\n            if str(component or "").strip()\n        ],\n'''
    text = _replace_once(text, anchor, anchor + '''        # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n        "visible_explanatory_groups": normalize_visible_explanatory_groups(\n            payload.get("visible_explanatory_groups") or []\n        ),\n''', "grounded explanatory verifier normalize")

    anchor = '    keyword = str(scene.get("keyword", "") or "").strip()\n'
    text = _replace_once(text, anchor, anchor + '''    required_explanatory = required_explanatory_groups(scene)\n    explanatory_requirement = generation_requirement(scene)\n''', "grounded explanatory verifier keyword")

    anchor = 'Observable action required: {str(action_required).lower()}\n'
    prompt_extra = '''Required explanatory groups: {", ".join(required_explanatory) if required_explanatory else "none"}\nGrounded explanatory visibility rule: {explanatory_requirement or "none"}\nWhen required explanatory groups are present, inspect them independently from subject dominance.\nReturn a group in visible_explanatory_groups ONLY when that relation/state is directly visible in the supplied frames.\nFor interface, a single exhaust plume is insufficient: directly show a meeting, boundary, interface, or junction between distinct visible flow/fluid regions.\nFor mixing, flow arrows or a single plume are insufficient: two or more distinct visible flow regions must visibly interleave, blend, or mix.\nDo not infer an explanatory group from narration, keyword, subject identity, or engineering knowledge.\n'''
    text = _replace_once(text, anchor, anchor + prompt_extra, "grounded explanatory verifier prompt")

    anchor = '  "visible_components": ["aircraft", "wing"],\n'
    text = _replace_once(text, anchor, anchor + '  "visible_explanatory_groups": [],\n', "grounded explanatory verifier JSON")
    path.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")


def patch_still_supply():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_PASS_PROPAGATION_V1" not in text:
        raise RuntimeError("grounded explanatory still supply requires #256 propagation")

    anchor = "from config import OPENAI_KEY\n"
    text = _replace_once(text, anchor, anchor + (
        "from video.grounded_explanatory_visual import (\n"
        "    explanatory_evidence_complete, explanatory_signature, generation_requirement, required_explanatory_groups,\n"
        ")\n"
    ), "grounded explanatory still import")

    text = text.rstrip() + r'''


# GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1
_grounded_explanatory_previous_prompt = _prompt
_grounded_explanatory_previous_anchor_signature = _anchor_signature
_grounded_explanatory_previous_verify_motion_clip = _verify_motion_clip


def _prompt(scene):
    base = _grounded_explanatory_previous_prompt(scene)
    requirement = generation_requirement(scene)
    return base if not requirement else base + " " + requirement


def _anchor_signature(scene):
    subject_signature = tuple(_grounded_explanatory_previous_anchor_signature(scene) or ())
    relation_signature = explanatory_signature(scene)
    return subject_signature if not relation_signature else subject_signature + relation_signature


def _verify_motion_clip(scene, output_path):
    verified, evidence = _grounded_explanatory_previous_verify_motion_clip(scene, output_path)
    if not verified:
        return False, evidence
    required = required_explanatory_groups(scene)
    if not required:
        return True, evidence
    complete, visible, missing = explanatory_evidence_complete(scene, evidence)
    evidence["required_explanatory_groups"] = list(required)
    evidence["visible_explanatory_groups"] = list(visible)
    evidence["missing_explanatory_groups"] = list(missing)
    return bool(complete), evidence
'''
    path.write_text(text, encoding="utf-8")


def patch_visual_explanation():
    path = ROOT / "video/visual_explanation.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    anchor = "from config import VIDEO_HEIGHT, VIDEO_WIDTH\n"
    text = _replace_once(text, anchor, anchor + (
        "from video.grounded_explanatory_visual import (\n"
        "    chevron_flow_mixing_supported, required_explanatory_groups, subject_anchor_words,\n"
        ")\n"
    ), "grounded explanation import")

    anchor = '''    value = _text(scene)\n    if not _winglet_subject(scene):\n        return None\n\n'''
    replacement = '''    value = _text(scene)\n    # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n    required_groups = required_explanatory_groups(scene)\n    subject_anchors = subject_anchor_words(scene)\n    if chevron_flow_mixing_supported(scene):\n        return {\n            "scene_role": "mechanism", "subject": "aircraft_engine_chevron",\n            "action": "chevron_flow_mixing", "template": "CHEVRON_FLOW_MIXING",\n            "label": "셰브론 주변 흐름 혼합",\n            "required_explanatory_groups": list(required_groups),\n            "required_subject_anchors": ["aircraft", "engine", "chevron"],\n            "owned_claim_id": "chevron_flow_mixing",\n            "forbidden_claim_ids": ["noise_reduction"],\n            "source_priority": ("explanatory_2d",),\n        }\n    if set(required_groups) == {"flow", "interface"} and {"aircraft", "engine"}.issubset(set(subject_anchors)):\n        return {\n            "scene_role": "mechanism", "subject": "aircraft_engine",\n            "action": "flow_interface", "template": "FLOW_INTERFACE",\n            "label": "흐름이 만나는 경계",\n            "required_explanatory_groups": list(required_groups),\n            "required_subject_anchors": ["aircraft", "engine"],\n            "source_priority": ("explanatory_2d",),\n        }\n    if not _winglet_subject(scene):\n        return None\n\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation plan")

    anchor = '''    if not plan or not _winglet_subject(scene):\n        return False\n    value = _text(scene)\n'''
    replacement = '''    if not plan:\n        return False\n    if plan.get("template") not in {"FLOW_INTERFACE", "CHEVRON_FLOW_MIXING"} and not _winglet_subject(scene):\n        return False\n    value = _text(scene)\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation guard")

    anchor = '''    value = _text(scene)\n    template = plan.get("template")\n    if template == "WINGLET_VORTEX":\n'''
    replacement = '''    value = _text(scene)\n    template = plan.get("template")\n    if template == "CHEVRON_FLOW_MIXING":\n        return (\n            chevron_flow_mixing_supported(scene)\n            and plan.get("owned_claim_id") == "chevron_flow_mixing"\n            and plan.get("forbidden_claim_ids") == ["noise_reduction"]\n        )\n    if template == "FLOW_INTERFACE":\n        return (\n            set(required_explanatory_groups(scene)) == {"flow", "interface"}\n            and {"aircraft", "engine"}.issubset(set(subject_anchor_words(scene)))\n        )\n    if template == "WINGLET_VORTEX":\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation safety")

    anchor = '''    template = plan["template"]\n    if template == "WINGLET_VORTEX":\n'''
    replacement = '''    template = plan["template"]\n    if template == "CHEVRON_FLOW_MIXING":\n        # Fact-bounded Scene-4 mechanism only: rear engine/nozzle context, a\n        # serrated chevron edge, and two flow regions visibly interleaving at\n        # that edge. No Scene-5 outcome is drawn or labelled.\n        draw.rounded_rectangle((120, 245, 970, 625), radius=24, fill=(20, 23, 30, 250))\n        # aircraft/engine context\n        draw.line((155, 330, 430, 330), fill=(220, 220, 220, 235), width=22)\n        draw.ellipse((315, 300, 610, 520), fill=(82, 86, 94, 245), outline=(238, 238, 238, 235), width=5)\n        draw.ellipse((430, 340, 600, 485), fill=(30, 33, 40, 255), outline=(230, 230, 230, 220), width=4)\n        # explicit serrated trailing edge / chevrons\n        chevron_points = [(600, 352), (630, 372), (600, 392), (630, 412), (600, 432), (630, 452), (600, 472)]\n        draw.line(chevron_points, fill=(255, 255, 255, 250), width=9)\n        # distinct inner and outer flow regions before the serrated edge\n        draw.polygon([(610, 378), (925, 350), (925, 425), (610, 420)], fill=(245, 245, 245, 95))\n        draw.polygon([(610, 300), (925, 270), (925, 332), (610, 350)], fill=(165, 165, 165, 80))\n        # downstream interleaving bands: alternating paths converge across the\n        # chevron edge; arrows state only visible flow direction, not outcome.\n        shift = int(10 * progress)\n        inner_paths = [\n            [(625, 382), (700, 365 + shift), (785, 382), (875, 365), (950, 378)],\n            [(625, 432), (700, 415 - shift), (785, 432), (875, 415), (950, 428)],\n        ]\n        outer_paths = [\n            [(625, 332), (700, 350 - shift), (785, 334), (875, 350), (950, 338)],\n            [(625, 482), (700, 455 + shift), (785, 470), (875, 450), (950, 458)],\n        ]\n        for points in inner_paths:\n            draw.line(points, fill=(255, 255, 255, 235), width=11)\n            _arrow(draw, points[-2], points[-1], width=8)\n        for points in outer_paths:\n            draw.line(points, fill=(185, 185, 185, 220), width=9)\n            _arrow(draw, points[-2], points[-1], width=7)\n        draw.text((575, 535), "두 흐름이 셰브론 가장자리에서 섞임", font=small, fill=(255, 255, 255, 235))\n    elif template == "FLOW_INTERFACE":\n        # Exterior aircraft/engine context plus two visible flow regions meeting\n        # at a boundary. No chevron/performance/internal-structure claim added.\n        draw.line((165, y - 40, 610, y - 40), fill=(235, 235, 235, 245), width=28)\n        draw.ellipse((420, y - 10, 690, y + 150), fill=(92, 92, 92, 235), outline=(240, 240, 240, 230), width=5)\n        draw.rectangle((610, y + 18, 715, y + 122), fill=(35, 35, 35, 245), outline=(240, 240, 240, 220), width=4)\n        draw.polygon([(715, y + 35), (965, y), (965, y + 140), (715, y + 105)], fill=(255, 255, 255, 92))\n        draw.polygon([(715, y - 90), (965, y - 110), (965, y - 35), (715, y - 25)], fill=(180, 180, 180, 80))\n        draw.line([(730, y + 15), (790, y + 5), (850, y - 5), (910, y - 15), (965, y - 20)], fill=(255, 255, 255, 245), width=10)\n        draw.text((650, 535), "두 흐름이 만나는 경계", font=small, fill=(255, 255, 255, 235))\n    elif template == "WINGLET_VORTEX":\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation drawing")

    anchor = '''        "anchor_matched": 2,\n        "anchor_total": 2,\n'''
    replacement = '''        "anchor_matched": len(plan.get("required_subject_anchors") or []) or 2,\n        "anchor_total": len(plan.get("required_subject_anchors") or []) or 2,\n        "required_subject_anchors": list(plan.get("required_subject_anchors") or []),\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation subject result")

    anchor = '''        "annotation_type": "concept_panel",\n        "additional_llm_calls": 0,\n        "additional_vision_calls": 0,\n    }\n'''
    replacement = '''        "annotation_type": "concept_panel",\n        "owned_claim_id": str(plan.get("owned_claim_id") or ""),\n        "forbidden_claim_ids": list(plan.get("forbidden_claim_ids") or []),\n        "required_explanatory_groups": list(plan.get("required_explanatory_groups") or []),\n        "visible_explanatory_groups": list(plan.get("required_explanatory_groups") or []),\n        "explanatory_anchor_matched": len(plan.get("required_explanatory_groups") or []),\n        "explanatory_anchor_total": len(plan.get("required_explanatory_groups") or []),\n        "additional_llm_calls": 0,\n        "additional_vision_calls": 0,\n    }\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation result")
    path.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")


def patch_explanation_lineage():
    path = ROOT / "ci_visual_explanation_retrieval_v1_hotfix.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    anchor = '''                    "source_id": still_result.get("source_id", "generated-still"),\n                    "metadata": " | ".join(part for part in metadata_parts if part),\n                })\n'''
    replacement = '''                    "source_id": still_result.get("source_id", "generated-still"),\n                    "metadata": " | ".join(part for part in metadata_parts if part),\n                    # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n                    "required_explanatory_anchors": list(still_result.get("required_explanatory_groups") or []),\n                    "explanatory_anchor_matched": int(still_result.get("explanatory_anchor_matched", 0) or 0),\n                    "explanatory_anchor_total": int(still_result.get("explanatory_anchor_total", 0) or 0),\n                })\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation lineage")
    path.write_text(text.rstrip() + f"\n\n# {MARKER}\n", encoding="utf-8")


def main():
    patch_dominance_verifier()
    patch_still_supply()
    patch_visual_explanation()
    patch_explanation_lineage()
    print("✅ Grounded explanatory visual supply V1 applied: relation nucleus preserved through still/Vision/explanation")


if __name__ == "__main__":
    main()
