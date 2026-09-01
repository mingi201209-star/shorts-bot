from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# STILL_VISION_EVIDENCE_TRACE_V1"


def _patch_parent_domain():
    from ci_still_parent_domain_propagation_hotfix import main as patch_parent_domain
    patch_parent_domain()


def _patch_question_subject_reuse():
    from ci_run_33371268494_scene2_verified_subject_reuse_hotfix import main as patch_question_subject_reuse
    patch_question_subject_reuse()


def _patch_early_verified_asset_presentation():
    from ci_early_verified_asset_presentation_hotfix import main as patch_early_presentation
    patch_early_presentation()


def _patch_viewpoint_structure_proof():
    from ci_run_33377519851_scene1_viewpoint_structure_hotfix import main as patch_viewpoint_structure
    patch_viewpoint_structure()


def main():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        _patch_parent_domain()
        _patch_question_subject_reuse()
        _patch_early_verified_asset_presentation()
        _patch_viewpoint_structure_proof()
        return
    if "STILL_VISION_EVIDENCE_GROUPS_V1" not in text:
        raise RuntimeError("Vision evidence trace requires structured evidence groups")

    function_start = text.find("def _verify_motion_clip(")
    function_end = text.find("\ndef ", function_start + 1)
    if function_start < 0:
        raise RuntimeError("still verifier function missing")
    if function_end < 0:
        function_end = len(text)
    section = text[function_start:function_end]

    eval_anchor = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    # STILL_VISION_EVIDENCE_GROUPS_V1\n'''
    eval_replacement = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n\n    # STILL_VISION_EVIDENCE_TRACE_V1\n    def _vision_evidence_trace(decision, missing=None):\n        required = list(result.get("required_subject_groups") or [])\n        visible_groups = result.get("visible_subject_groups") or {}\n        visible_components = list(result.get("visible_components") or [])\n        parent_domain = list(result.get("parent_domain_satisfied") or [])\n        missing = list(missing or [])\n        print(\n            "[VISION_EVIDENCE_TRACE] "\n            f"pass={bool(result.get('pass', False))} "\n            f"required_subject_groups={'+'.join(required) or 'none'} "\n            f"visible_subject_groups={visible_groups} "\n            f"visible_components={'+'.join(str(value) for value in visible_components) or 'none'} "\n            f"parent_domain_satisfied={'+'.join(parent_domain) or 'none'} "\n            f"missing={'+'.join(missing) or 'none'} "\n            f"schema_parser_consistency={bool(result.get('schema_parser_consistency', True))} "\n            f"result={decision} "\n            f"reason={str(result.get('reason') or '')[:240]}"\n        )\n\n    # STILL_VISION_EVIDENCE_GROUPS_V1\n'''
    if section.count(eval_anchor) != 1:
        raise RuntimeError("Vision evidence trace eval anchor mismatch")
    section = section.replace(eval_anchor, eval_replacement, 1)

    consistency_anchor = '''    if not bool(result.get("schema_parser_consistency", True)):\n        return False, result\n'''
    consistency_replacement = '''    if not bool(result.get("schema_parser_consistency", True)):\n        missing = [\n            group for group, visible in (result.get("visible_subject_groups") or {}).items()\n            if not bool(visible)\n        ]\n        _vision_evidence_trace("REJECT", missing)\n        return False, result\n'''
    if section.count(consistency_anchor) != 1:
        raise RuntimeError("Vision evidence trace consistency anchor mismatch")
    section = section.replace(consistency_anchor, consistency_replacement, 1)

    pass_anchor = '''    if not result.get("pass", False):\n        return False, result\n'''
    pass_replacement = '''    if not result.get("pass", False):\n        _vision_evidence_trace("REJECT", result.get("required_subject_groups") or [])\n        return False, result\n'''
    if section.count(pass_anchor) != 1:
        raise RuntimeError("Vision evidence trace pass anchor mismatch")
    section = section.replace(pass_anchor, pass_replacement, 1)

    artifact_anchor = '''    if result.get("obvious_generation_artifact", False):\n        return False, result\n    if result.get("factual_visual_contradiction", False):\n        return False, result\n'''
    artifact_replacement = '''    if result.get("obvious_generation_artifact", False):\n        _vision_evidence_trace("REJECT", result.get("required_subject_groups") or [])\n        return False, result\n    if result.get("factual_visual_contradiction", False):\n        _vision_evidence_trace("REJECT", result.get("required_subject_groups") or [])\n        return False, result\n'''
    if section.count(artifact_anchor) != 1:
        raise RuntimeError("Vision evidence trace contradiction anchor mismatch")
    section = section.replace(artifact_anchor, artifact_replacement, 1)

    anchor_fail = '''        return False, result\n\n    if parent_domain_satisfied:\n'''
    anchor_fail_replacement = '''        _vision_evidence_trace("REJECT", [anchor])\n        return False, result\n\n    if parent_domain_satisfied:\n'''
    if section.count(anchor_fail) != 1:
        raise RuntimeError("Vision evidence trace subject-missing anchor mismatch")
    section = section.replace(anchor_fail, anchor_fail_replacement, 1)

    # The structured-groups patch already emits an ACCEPT trace at the final
    # return. Do not add a duplicate success log here.
    text = text[:function_start] + section + text[function_end:]
    path.write_text(text, encoding="utf-8")
    _patch_parent_domain()
    _patch_question_subject_reuse()
    _patch_early_verified_asset_presentation()
    _patch_viewpoint_structure_proof()
    print("✅ Vision evidence trace records structured accept/reject decisions")


if __name__ == "__main__":
    main()
