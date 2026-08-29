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

    # Later first-five/still installers rewrite surrounding prompt prose. This
    # line survives composition, so attach the entire relation instruction here.
    anchor = 'Observable action required: {str(action_required).lower()}\n'
    prompt_extra = '''Required explanatory groups: {", ".join(required_explanatory) if required_explanatory else "none"}\nGrounded explanatory visibility rule: {explanatory_requirement or "none"}\nWhen required explanatory groups are present, inspect them independently from subject dominance.\nReturn a group in visible_explanatory_groups ONLY when that relation/state is directly visible in the supplied frames.\nFor interface, a single exhaust plume is insufficient: directly show a meeting, boundary, interface, or junction between distinct visible flow/fluid regions.\nDo not infer an explanatory group from narration, keyword, subject identity, or engineering knowledge.\n'''
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
        "from video.grounded_explanatory_visual import required_explanatory_groups, subject_anchor_words\n"
    ), "grounded explanation import")

    anchor = '''    value = _text(scene)\n    if not _winglet_subject(scene):\n        return None\n\n'''
    replacement = '''    value = _text(scene)\n    # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n    required_groups = required_explanatory_groups(scene)\n    subject_anchors = subject_anchor_words(scene)\n    if set(required_groups) == {"flow", "interface"} and {"aircraft", "engine"}.issubset(set(subject_anchors)):\n        return {\n            "scene_role": "mechanism", "subject": "aircraft_engine",\n            "action": "flow_interface", "template": "FLOW_INTERFACE",\n            "label": "흐름이 만나는 경계",\n            "required_explanatory_groups": list(required_groups),\n            "required_subject_anchors": ["aircraft", "engine"],\n            "source_priority": ("explanatory_2d",),\n        }\n    if not _winglet_subject(scene):\n        return None\n\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation plan")

    anchor = '''    if not plan or not _winglet_subject(scene):\n        return False\n    value = _text(scene)\n'''
    replacement = '''    if not plan:\n        return False\n    if plan.get("template") != "FLOW_INTERFACE" and not _winglet_subject(scene):\n        return False\n    value = _text(scene)\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation guard")

    anchor = '''    value = _text(scene)\n    template = plan.get("template")\n    if template == "WINGLET_VORTEX":\n'''
    replacement = '''    value = _text(scene)\n    template = plan.get("template")\n    if template == "FLOW_INTERFACE":\n        return (\n            set(required_explanatory_groups(scene)) == {"flow", "interface"}\n            and {"aircraft", "engine"}.issubset(set(subject_anchor_words(scene)))\n        )\n    if template == "WINGLET_VORTEX":\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation safety")

    anchor = '''    template = plan["template"]\n    if template == "WINGLET_VORTEX":\n'''
    replacement = '''    template = plan["template"]\n    if template == "FLOW_INTERFACE":\n        # Exterior aircraft/engine context plus two visible flow regions meeting\n        # at a boundary. No chevron/performance/internal-structure claim added.\n        draw.line((165, y - 40, 610, y - 40), fill=(235, 235, 235, 245), width=28)\n        draw.ellipse((420, y - 10, 690, y + 150), fill=(92, 92, 92, 235), outline=(240, 240, 240, 230), width=5)\n        draw.rectangle((610, y + 18, 715, y + 122), fill=(35, 35, 35, 245), outline=(240, 240, 240, 220), width=4)\n        draw.polygon([(715, y + 35), (965, y), (965, y + 140), (715, y + 105)], fill=(255, 255, 255, 92))\n        draw.polygon([(715, y - 90), (965, y - 110), (965, y - 35), (715, y - 25)], fill=(180, 180, 180, 80))\n        draw.line([(730, y + 15), (790, y + 5), (850, y - 5), (910, y - 15), (965, y - 20)], fill=(255, 255, 255, 245), width=10)\n        draw.text((650, 535), "두 흐름이 만나는 경계", font=small, fill=(255, 255, 255, 235))\n    elif template == "WINGLET_VORTEX":\n'''
    text = _replace_once(text, anchor, replacement, "grounded explanation drawing")

    anchor = '''        "annotation_type": "concept_panel",\n        "additional_llm_calls": 0,\n        "additional_vision_calls": 0,\n    }\n'''
    replacement = '''        "annotation_type": "concept_panel",\n        "required_explanatory_groups": list(plan.get("required_explanatory_groups") or []),\n        "explanatory_anchor_matched": len(plan.get("required_explanatory_groups") or []),\n        "explanatory_anchor_total": len(plan.get("required_explanatory_groups") or []),\n        "additional_llm_calls": 0,\n        "additional_vision_calls": 0,\n    }\n'''
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
