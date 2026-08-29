from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1"


def patch_dominance_verifier():
    path = ROOT / "video/hook_visual_dominance.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_VERIFIER_CONTRACT_V1" not in text:
        raise RuntimeError("grounded explanatory verifier requires still verifier contract")

    import_anchor = "from quality.budget_guard import authorize_call, print_budget_status, record_usage\n"
    import_replacement = import_anchor + (
        "from video.grounded_explanatory_visual import (\n"
        "    generation_requirement,\n"
        "    normalize_visible_explanatory_groups,\n"
        "    required_explanatory_groups,\n"
        ")\n"
    )
    if text.count(import_anchor) != 1:
        raise RuntimeError("grounded explanatory verifier import anchor mismatch")
    text = text.replace(import_anchor, import_replacement, 1)

    normalize_anchor = '''        "visible_components": [\n            str(component or "").strip().lower()\n            for component in (payload.get("visible_components") or [])\n            if str(component or "").strip()\n        ],\n'''
    normalize_replacement = normalize_anchor + '''        # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n        "visible_explanatory_groups": normalize_visible_explanatory_groups(\n            payload.get("visible_explanatory_groups") or []\n        ),\n'''
    if text.count(normalize_anchor) != 1:
        raise RuntimeError("grounded explanatory verifier normalize anchor mismatch")
    text = text.replace(normalize_anchor, normalize_replacement, 1)

    keyword_anchor = '''    keyword = str(scene.get("keyword", "") or "").strip()\n\n    prompt = f"""\n'''
    keyword_replacement = '''    keyword = str(scene.get("keyword", "") or "").strip()\n    required_explanatory = required_explanatory_groups(scene)\n    explanatory_requirement = generation_requirement(scene)\n\n    prompt = f"""\n'''
    if text.count(keyword_anchor) != 1:
        raise RuntimeError("grounded explanatory verifier keyword anchor mismatch")
    text = text.replace(keyword_anchor, keyword_replacement, 1)

    prompt_anchor = '''Observable action required: {str(action_required).lower()}\n\nIdentify the concrete subject explicitly promised by the Hook. Then score:\n'''
    prompt_replacement = '''Observable action required: {str(action_required).lower()}\nRequired explanatory groups: {", ".join(required_explanatory) if required_explanatory else "none"}\nGrounded explanatory visibility rule: {explanatory_requirement or "none"}\n\nWhen required explanatory groups are present, inspect them independently from subject dominance.\nReturn a group in visible_explanatory_groups ONLY when that relation/state is directly visible in the supplied frames.\nFor interface, a single exhaust plume is insufficient: the frames must directly show a meeting, boundary, interface, or junction between distinct visible flow/fluid regions.\nDo not infer an explanatory group from narration, keyword, subject identity, or engineering knowledge.\n\nIdentify the concrete subject explicitly promised by the Hook. Then score:\n'''
    if text.count(prompt_anchor) != 1:
        raise RuntimeError("grounded explanatory verifier prompt anchor mismatch")
    text = text.replace(prompt_anchor, prompt_replacement, 1)

    json_anchor = '''  "visible_components": ["aircraft", "wing"],\n  "obvious_generation_artifact": false,\n'''
    json_replacement = '''  "visible_components": ["aircraft", "wing"],\n  "visible_explanatory_groups": [],\n  "obvious_generation_artifact": false,\n'''
    if text.count(json_anchor) != 1:
        raise RuntimeError("grounded explanatory verifier JSON anchor mismatch")
    text = text.replace(json_anchor, json_replacement, 1)
    text = text.rstrip() + f"\n\n# {MARKER}\n"
    path.write_text(text, encoding="utf-8")


def patch_still_supply():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_PASS_PROPAGATION_V1" not in text:
        raise RuntimeError("grounded explanatory still supply requires #256 propagation")

    import_anchor = "from config import OPENAI_KEY\n"
    import_replacement = import_anchor + (
        "from video.grounded_explanatory_visual import (\n"
        "    explanatory_evidence_complete,\n"
        "    explanatory_signature,\n"
        "    generation_requirement,\n"
        "    required_explanatory_groups,\n"
        ")\n"
    )
    if text.count(import_anchor) != 1:
        raise RuntimeError("grounded explanatory still import anchor mismatch")
    text = text.replace(import_anchor, import_replacement, 1)

    text = text.rstrip() + r'''


# GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1
# Preserve #254's complete grounded relation nucleus after stock exhaustion.
# This wraps supply/verification only: subject anchors, Vision thresholds,
# generation count, API calls and retry ceilings are unchanged.
_grounded_explanatory_previous_prompt = _prompt
_grounded_explanatory_previous_anchor_signature = _anchor_signature
_grounded_explanatory_previous_verify_motion_clip = _verify_motion_clip


def _prompt(scene):
    base = _grounded_explanatory_previous_prompt(scene)
    requirement = generation_requirement(scene)
    if not requirement:
        return base
    return base + " " + requirement


def _anchor_signature(scene):
    subject_signature = tuple(_grounded_explanatory_previous_anchor_signature(scene) or ())
    explanation_signature = explanatory_signature(scene)
    if not explanation_signature:
        return subject_signature
    # A previously verified subject still is not proof of a new mechanism claim.
    # Cache/reuse now distinguishes the relation nucleus as well as the subject.
    return subject_signature + explanation_signature


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
    if not complete:
        return False, evidence
    return True, evidence
'''
    path.write_text(text, encoding="utf-8")


def patch_visual_explanation():
    path = ROOT / "video/visual_explanation.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    import_anchor = "from config import VIDEO_HEIGHT, VIDEO_WIDTH\n"
    import_replacement = import_anchor + (
        "from video.grounded_explanatory_visual import (\n"
        "    required_explanatory_groups,\n"
        "    subject_anchor_words,\n"
        ")\n"
    )
    if text.count(import_anchor) != 1:
        raise RuntimeError("grounded explanation import anchor mismatch")
    text = text.replace(import_anchor, import_replacement, 1)

    plan_anchor = '''    value = _text(scene)\n    if not _winglet_subject(scene):\n        return None\n\n'''
    plan_replacement = '''    value = _text(scene)\n    # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n    required_groups = required_explanatory_groups(scene)\n    subject_anchors = subject_anchor_words(scene)\n    if set(required_groups) == {"flow", "interface"} and {"aircraft", "engine"}.issubset(set(subject_anchors)):\n        return {\n            "scene_role": "mechanism",\n            "subject": "aircraft_engine",\n            "action": "flow_interface",\n            "template": "FLOW_INTERFACE",\n            "label": "흐름이 만나는 경계",\n            "required_explanatory_groups": list(required_groups),\n            "required_subject_anchors": ["aircraft", "engine"],\n            "source_priority": ("explanatory_2d",),\n        }\n    if not _winglet_subject(scene):\n        return None\n\n'''
    if text.count(plan_anchor) != 1:
        raise RuntimeError("grounded explanation plan anchor mismatch")
    text = text.replace(plan_anchor, plan_replacement, 1)

    safety_anchor = '''    value = _text(scene)\n    template = plan.get("template")\n    if template == "WINGLET_VORTEX":\n'''
    safety_replacement = '''    value = _text(scene)\n    template = plan.get("template")\n    if template == "FLOW_INTERFACE":\n        required_groups = set(required_explanatory_groups(scene))\n        subject_anchors = set(subject_anchor_words(scene))\n        return required_groups == {"flow", "interface"} and {"aircraft", "engine"}.issubset(subject_anchors)\n    if template == "WINGLET_VORTEX":\n'''
    if text.count(safety_anchor) != 1:
        raise RuntimeError("grounded explanation safety anchor mismatch")
    text = text.replace(safety_anchor, safety_replacement, 1)

    # Existing helper rejects all non-winglet plans before the template-specific
    # checks. Narrowly exempt only the grounded FLOW_INTERFACE template above.
    guard_anchor = '''    if not plan or not _winglet_subject(scene):\n        return False\n    value = _text(scene)\n'''
    guard_replacement = '''    if not plan:\n        return False\n    if plan.get("template") != "FLOW_INTERFACE" and not _winglet_subject(scene):\n        return False\n    value = _text(scene)\n'''
    if text.count(guard_anchor) != 1:
        raise RuntimeError("grounded explanation winglet guard mismatch")
    text = text.replace(guard_anchor, guard_replacement, 1)

    draw_anchor = '''    template = plan["template"]\n    if template == "WINGLET_VORTEX":\n'''
    draw_replacement = '''    template = plan["template"]\n    if template == "FLOW_INTERFACE":\n        # Conservative exterior schematic: aircraft/wing context + nacelle, then\n        # two visible flow regions meeting at a boundary. No chevron, performance\n        # effect, measurements or unsupported internal structure are invented.\n        draw.line((165, y - 40, 610, y - 40), fill=(235, 235, 235, 245), width=28)\n        draw.ellipse((420, y - 10, 690, y + 150), fill=(92, 92, 92, 235), outline=(240, 240, 240, 230), width=5)\n        draw.rectangle((610, y + 18, 715, y + 122), fill=(35, 35, 35, 245), outline=(240, 240, 240, 220), width=4)\n        inner_y = y + 70\n        outer_y = y - 20\n        draw.polygon([(715, inner_y - 35), (965, inner_y - 70), (965, inner_y + 70), (715, inner_y + 35)], fill=(255, 255, 255, 92))\n        draw.polygon([(715, outer_y - 70), (965, outer_y - 90), (965, outer_y - 15), (715, outer_y - 5)], fill=(180, 180, 180, 80))\n        boundary = [(730, y + 15), (790, y + 5), (850, y - 5), (910, y - 15), (965, y - 20)]\n        draw.line(boundary, fill=(255, 255, 255, 245), width=10)\n        draw.text((650, 535), "두 흐름이 만나는 경계", font=small, fill=(255, 255, 255, 235))\n    elif template == "WINGLET_VORTEX":\n'''
    if text.count(draw_anchor) != 1:
        raise RuntimeError("grounded explanation draw anchor mismatch")
    text = text.replace(draw_anchor, draw_replacement, 1)

    return_anchor = '''        "annotation_type": "concept_panel",\n        "additional_llm_calls": 0,\n        "additional_vision_calls": 0,\n    }\n'''
    return_replacement = '''        "annotation_type": "concept_panel",\n        "required_explanatory_groups": list(plan.get("required_explanatory_groups") or []),\n        "explanatory_anchor_matched": len(plan.get("required_explanatory_groups") or []),\n        "explanatory_anchor_total": len(plan.get("required_explanatory_groups") or []),\n        "additional_llm_calls": 0,\n        "additional_vision_calls": 0,\n    }\n'''
    if text.count(return_anchor) != 1:
        raise RuntimeError("grounded explanation return anchor mismatch")
    text = text.replace(return_anchor, return_replacement, 1)
    text = text.rstrip() + f"\n\n# {MARKER}\n"
    path.write_text(text, encoding="utf-8")


def patch_explanation_lineage():
    path = ROOT / "ci_visual_explanation_retrieval_v1_hotfix.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    selection_anchor = '''                    "source_id": still_result.get("source_id", "generated-still"),\n                    "metadata": " | ".join(part for part in metadata_parts if part),\n                })\n'''
    selection_replacement = '''                    "source_id": still_result.get("source_id", "generated-still"),\n                    "metadata": " | ".join(part for part in metadata_parts if part),\n                    # GROUNDED_EXPLANATORY_VISUAL_SUPPLY_V1\n                    "required_explanatory_anchors": list(still_result.get("required_explanatory_groups") or []),\n                    "explanatory_anchor_matched": int(still_result.get("explanatory_anchor_matched", 0) or 0),\n                    "explanatory_anchor_total": int(still_result.get("explanatory_anchor_total", 0) or 0),\n                })\n'''
    if text.count(selection_anchor) != 1:
        raise RuntimeError("grounded explanation lineage anchor mismatch")
    text = text.replace(selection_anchor, selection_replacement, 1)
    text = text.rstrip() + f"\n\n# {MARKER}\n"
    path.write_text(text, encoding="utf-8")


def main():
    patch_dominance_verifier()
    patch_still_supply()
    patch_visual_explanation()
    patch_explanation_lineage()
    print("✅ Grounded explanatory visual supply V1 applied: relation nucleus preserved through still/Vision/explanation")


if __name__ == "__main__":
    main()
