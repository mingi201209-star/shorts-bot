from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "# RUN_33377519851_SCENE1_VIEWPOINT_STRUCTURE_V1"

_HOOK_HELPERS = r'''


def _still_viewpoint_structure_requirement(scene):
    """Return strict rear-view structure proof only for trusted canonical chevrons."""
    try:
        from video.still_image_fallback import _canonical_still_contract
        contract = _canonical_still_contract(scene)
    except Exception:
        contract = {}
    viewpoint = str((contract or {}).get("required_viewpoint") or "").strip().lower()
    priority = {
        str(value or "").strip().lower()
        for value in ((contract or {}).get("subject_proof_priority") or [])
        if str(value or "").strip()
    }
    required = bool(
        viewpoint
        and ("rear" in viewpoint or "trailing" in viewpoint)
        and (priority & {"chevron", "serrated", "sawtooth"})
        and (priority & {"nozzle", "nacelle", "trailing", "edge"})
    )
    return {
        "required": required,
        "required_viewpoint": viewpoint if required else "",
    }


def _still_viewpoint_structure_apply(result, payload, scene):
    normalized = dict(result or {})
    requirement = _still_viewpoint_structure_requirement(scene)
    raw = payload.get("viewpoint_structure_evidence")
    if not isinstance(raw, dict):
        raw = {}
    evidence = {
        "rear_nozzle_or_trailing_edge_identifiable": bool(
            raw.get("rear_nozzle_or_trailing_edge_identifiable", False)
        ),
        "chevron_attached_to_rear_nozzle_or_trailing_edge": bool(
            raw.get("chevron_attached_to_rear_nozzle_or_trailing_edge", False)
        ),
        "front_intake_or_fan_side_dominant": bool(
            raw.get("front_intake_or_fan_side_dominant", False)
        ),
        "mobile_structure_identifiable": bool(
            raw.get("mobile_structure_identifiable", False)
        ),
    }
    normalized["viewpoint_structure_evidence"] = evidence
    normalized["viewpoint_structure_required"] = bool(requirement.get("required"))
    normalized["required_viewpoint"] = requirement.get("required_viewpoint", "")
    if requirement.get("required"):
        viewpoint_pass = bool(
            evidence["rear_nozzle_or_trailing_edge_identifiable"]
            and evidence["chevron_attached_to_rear_nozzle_or_trailing_edge"]
            and not evidence["front_intake_or_fan_side_dominant"]
            and evidence["mobile_structure_identifiable"]
        )
        normalized["viewpoint_structure_pass"] = viewpoint_pass
        if not viewpoint_pass:
            normalized["subject_visibility"] = min(
                float(normalized.get("subject_visibility", 0) or 0), 5.0
            )
            normalized["visual_state"] = "FALSE"
            normalized["reason"] = (
                "trusted canonical rear-view structure proof missing: "
                f"rear={evidence['rear_nozzle_or_trailing_edge_identifiable']} "
                f"owned_edge={evidence['chevron_attached_to_rear_nozzle_or_trailing_edge']} "
                f"front_dominant={evidence['front_intake_or_fan_side_dominant']} "
                f"mobile={evidence['mobile_structure_identifiable']}"
            )
    else:
        normalized["viewpoint_structure_pass"] = True
    return normalized
'''


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} mismatch count={count}")
    return text.replace(old, new, 1)


def patch_hook_visual_dominance():
    path = ROOT / "video/hook_visual_dominance.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_VISION_EVIDENCE_GROUPS_V1" not in text:
        raise RuntimeError("viewpoint proof requires structured still Vision evidence")

    helper_anchor = "\ndef _extract_vertical_frames(video_url):\n"
    text = _replace_once(
        text, helper_anchor, _HOOK_HELPERS + helper_anchor,
        "viewpoint helper anchor",
    )

    setup_anchor = '''    visible_subject_groups_template = json.dumps(\n        {group: False for group in required_subject_groups}, ensure_ascii=False\n    )\n\n    prompt = f"""\n'''
    setup_replacement = '''    visible_subject_groups_template = json.dumps(\n        {group: False for group in required_subject_groups}, ensure_ascii=False\n    )\n    viewpoint_requirement = _still_viewpoint_structure_requirement(scene)\n    viewpoint_required = bool(viewpoint_requirement.get("required"))\n    viewpoint_rule = (\n        viewpoint_requirement.get("required_viewpoint")\n        if viewpoint_required else "none"\n    )\n\n    prompt = f"""\n'''
    text = _replace_once(text, setup_anchor, setup_replacement, "viewpoint prompt setup")

    prompt_anchor = '''- Keep reason consistent with structured evidence; do not claim a required group is visible when its structured value is false.\n'''
    prompt_replacement = prompt_anchor + '''\nStructured viewpoint/structure evidence contract:\n- Trusted canonical viewpoint requirement active: {str(viewpoint_required).lower()}\n- Required viewpoint from trusted canonical evidence: {viewpoint_rule}\n- viewpoint_structure_evidence is authoritative structured evidence for this requirement.\n- rear_nozzle_or_trailing_edge_identifiable=true only when the supplied frames visibly identify the rear nozzle/nacelle trailing edge, not merely a circular engine opening.\n- chevron_attached_to_rear_nozzle_or_trailing_edge=true only when the serrated/chevron edge is visibly part of that rear nozzle/nacelle trailing edge.\n- front_intake_or_fan_side_dominant=true when a front intake, fan face, or fan-side circular opening dominates the composition, even if its rim looks serrated.\n- mobile_structure_identifiable=true only when the rear edge and chevron ownership are large and immediately readable on a phone screen; a wide aircraft shot with tiny chevrons is false.\n- Do not infer these booleans from narration, keyword, engineering knowledge, or free-text reason.\n- When the trusted canonical viewpoint requirement is inactive, do not invent a new viewpoint requirement; report only what is directly visible.\n'''
    text = _replace_once(text, prompt_anchor, prompt_replacement, "viewpoint prompt contract")

    json_anchor = '  "visible_subject_groups": {visible_subject_groups_template},\n'
    # This block is inserted inside an existing f-string. Literal JSON braces must
    # therefore be doubled; otherwise Python interprets the object body as an
    # f-string format specifier and raises ValueError before the Vision call.
    json_replacement = json_anchor + '''  "viewpoint_structure_evidence": {{\n    "rear_nozzle_or_trailing_edge_identifiable": false,\n    "chevron_attached_to_rear_nozzle_or_trailing_edge": false,\n    "front_intake_or_fan_side_dominant": false,\n    "mobile_structure_identifiable": false\n  }},\n'''
    text = _replace_once(text, json_anchor, json_replacement, "viewpoint JSON schema")

    result_anchor = '''    result = _still_vision_apply_structured_evidence(\n        result, payload, required_subject_groups\n    )\n    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)\n'''
    result_replacement = '''    result = _still_vision_apply_structured_evidence(\n        result, payload, required_subject_groups\n    )\n    result = _still_viewpoint_structure_apply(result, payload, scene)\n    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)\n'''
    text = _replace_once(text, result_anchor, result_replacement, "viewpoint structured parser")
    path.write_text(text.rstrip() + f"\n\n{MARKER}\n", encoding="utf-8")


def patch_still_verifier():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "QUESTION_SUBJECT_REUSE_RUN_33371268494_V1" not in text:
        raise RuntimeError("viewpoint proof must compose after #268 verified subject reuse")

    text = text.rstrip() + r'''


# RUN_33377519851_SCENE1_VIEWPOINT_STRUCTURE_V1
_run33377519851_previous_verify_motion_clip = _verify_motion_clip


def _verify_motion_clip(scene, output_path):
    verified, evidence = _run33377519851_previous_verify_motion_clip(scene, output_path)
    evidence = evidence if isinstance(evidence, dict) else {}
    if not verified:
        return False, evidence

    from video.hook_visual_dominance import _still_viewpoint_structure_requirement
    requirement = _still_viewpoint_structure_requirement(scene)
    if not requirement.get("required"):
        return True, evidence

    viewpoint_pass = bool(evidence.get("viewpoint_structure_pass", False))
    structured = evidence.get("viewpoint_structure_evidence") or {}
    print(
        "[VIEWPOINT_STRUCTURE_TRACE] "
        f"scene={_scene_id(scene)} required=true "
        f"required_viewpoint={requirement.get('required_viewpoint', '')} "
        f"rear={bool(structured.get('rear_nozzle_or_trailing_edge_identifiable', False))} "
        f"owned_edge={bool(structured.get('chevron_attached_to_rear_nozzle_or_trailing_edge', False))} "
        f"front_dominant={bool(structured.get('front_intake_or_fan_side_dominant', False))} "
        f"mobile={bool(structured.get('mobile_structure_identifiable', False))} "
        f"result={'ACCEPT' if viewpoint_pass else 'REJECT'}"
    )
    return viewpoint_pass, evidence
'''
    path.write_text(text + "\n", encoding="utf-8")


def main():
    # #268 is the consumer of the verified Scene-1 proof. Install it first so a
    # viewpoint failure happens before any subject proof can enter its reuse cache.
    from ci_run_33371268494_scene2_verified_subject_reuse_hotfix import main as install_question_reuse
    install_question_reuse()
    patch_hook_visual_dominance()
    patch_still_verifier()
    print("✅ Run 33377519851 Scene1 rear-view structure proof installed; zero new calls")


if __name__ == "__main__":
    main()
