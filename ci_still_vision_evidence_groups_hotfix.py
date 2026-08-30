from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "# STILL_VISION_EVIDENCE_GROUPS_V1"

_HELPERS = r'''

# STILL_VISION_EVIDENCE_GROUPS_V1
# Structured evidence is authoritative. Free-text reason is diagnostics only.
_STILL_VISION_GROUP_ALIASES = {
    "engine": {
        "engine", "jet engine",
    },
    "chevron": {
        "chevron", "chevrons", "serrated edge", "serrated nozzle",
        "sawtooth trailing edge", "톱니", "셰브론",
    },
}


def _still_vision_norm_component(value):
    value = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    return re.sub(r"\\s+", " ", value).strip()


def _still_vision_required_subject_groups(scene):
    from video.video_downloader import extract_query_anchors
    groups = list(extract_query_anchors(str((scene or {}).get("keyword") or "")) or [])
    ordered = []
    for group in groups:
        group = _still_vision_norm_component(group)
        if group and group not in ordered:
            ordered.append(group)
    return ordered


def _still_vision_component_matches_group(component, group):
    component = _still_vision_norm_component(component)
    group = _still_vision_norm_component(group)
    aliases = set(_STILL_VISION_GROUP_ALIASES.get(group, ())) | {group}
    return bool(component and group and component in aliases)


def _still_vision_reason_mentions_group(reason, group):
    # Diagnostics only. Never use this to construct visible evidence.
    reason = _still_vision_norm_component(reason)
    aliases = set(_STILL_VISION_GROUP_ALIASES.get(group, ())) | {_still_vision_norm_component(group)}
    return any(alias and alias in reason for alias in aliases)


def _still_vision_apply_structured_evidence(result, payload, required_groups):
    components = [
        _still_vision_norm_component(value)
        for value in (payload.get("visible_components") or [])
        if _still_vision_norm_component(value)
    ]
    explicit = payload.get("visible_subject_groups")
    explicit = explicit if isinstance(explicit, dict) else {}
    explicit = {
        _still_vision_norm_component(key): bool(value)
        for key, value in explicit.items()
        if _still_vision_norm_component(key)
    }

    visible_groups = {}
    component_derived_groups = {}
    inconsistencies = []
    resolved_inconsistencies = []
    for group in required_groups:
        component_visible = any(
            _still_vision_component_matches_group(component, group)
            for component in components
        )
        component_derived_groups[group] = bool(component_visible)
        if group in explicit:
            explicit_visible = bool(explicit[group])
            if explicit_visible != component_visible:
                inconsistency = (
                    f"structured_group_component_disagree:{group}:"
                    f"group={str(explicit_visible).lower()}:"
                    f"component={str(component_visible).lower()}"
                )
                # Run 33301914013: approved structured component evidence
                # "jet engine" is a canonical engine-group alias. Resolve only
                # this narrow false-negative direction. Other structured
                # contradictions remain fail-closed, including chevron.
                if group == "engine" and component_visible and not explicit_visible:
                    resolved_inconsistencies.append(inconsistency)
                else:
                    inconsistencies.append(inconsistency)
            if group == "engine":
                visible = explicit_visible or component_visible
            else:
                visible = explicit_visible and component_visible
        else:
            # Legacy structured-only callers remain supported; reason is never used.
            visible = component_visible
        visible_groups[group] = bool(visible)

    canonical_components = list(components)
    for group, visible in visible_groups.items():
        if visible and group not in canonical_components:
            canonical_components.append(group)

    reason = str(payload.get("reason") or "").strip()[:500]
    for group, visible in visible_groups.items():
        if not visible and _still_vision_reason_mentions_group(reason, group):
            inconsistencies.append(f"reason_claims_missing_structured_group:{group}")

    result["required_subject_groups"] = list(required_groups)
    result["model_visible_subject_groups"] = dict(explicit)
    result["component_derived_subject_groups"] = dict(component_derived_groups)
    result["effective_raw_subject_groups"] = dict(visible_groups)
    result["visible_subject_groups"] = dict(visible_groups)
    result["visible_components"] = canonical_components
    result["schema_parser_consistency"] = not bool(inconsistencies)
    result["evidence_inconsistencies"] = list(inconsistencies)
    result["resolved_evidence_inconsistencies"] = list(resolved_inconsistencies)
    return result
'''


def patch_hook_visual_dominance():
    path = ROOT / "video/hook_visual_dominance.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_VERIFIER_CONTRACT_V1" not in text:
        raise RuntimeError("structured evidence requires still verifier contract")

    anchor = "\ndef _extract_vertical_frames(video_url):\n"
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence helper anchor mismatch")
    text = text.replace(anchor, _HELPERS + anchor, 1)

    anchor = '''    keyword = str(scene.get("keyword", "") or "").strip()\n\n    prompt = f"""\n'''
    replacement = '''    keyword = str(scene.get("keyword", "") or "").strip()\n    required_subject_groups = _still_vision_required_subject_groups(scene)\n    required_subject_groups_json = json.dumps(required_subject_groups, ensure_ascii=False)\n    visible_subject_groups_template = json.dumps(\n        {group: False for group in required_subject_groups}, ensure_ascii=False\n    )\n\n    prompt = f"""\n'''
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence keyword anchor mismatch")
    text = text.replace(anchor, replacement, 1)

    # Other visual hotfixes may add guidance between this line and the score
    # rubric. Patch only the stable line so installer order cannot break us.
    anchor = "Observable action required: {str(action_required).lower()}\n"
    replacement = "Observable action required: {str(action_required).lower()}\nRequired subject groups: {required_subject_groups_json}\n\nStructured subject-evidence contract:\n- visible_components is authoritative structured evidence. List only concrete components visibly identifiable in the supplied frames.\n- visible_subject_groups MUST contain every required subject group above as true/false. Set true only when that group is visibly identifiable.\n- Approved engine component labels are: engine, jet engine.\n- For chevron only, allowed structured aliases are: chevron, chevrons, serrated edge, serrated nozzle, sawtooth trailing edge, 톱니, 셰브론.\n- Never treat wing, engine, blade, fan, or gear as chevron evidence.\n- Keep reason consistent with structured evidence; do not claim a required group is visible when its structured value is false.\n"
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence prompt anchor mismatch")
    text = text.replace(anchor, replacement, 1)

    anchor = "- visible_components: list ONLY concrete physical components visibly identifiable in the frames. Include required search components such as aircraft, wing, winglet, window, engine only when they are actually visible; do not infer them from the keyword.\n"
    replacement = "- visible_components: list ONLY concrete physical components visibly identifiable in the frames. For required groups prefer canonical labels; approved aliases above are equivalent. Do not infer from the keyword.\n- visible_subject_groups: return exactly the required group keys with boolean values. Template: {visible_subject_groups_template}\n"
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence components prompt anchor mismatch")
    text = text.replace(anchor, replacement, 1)

    # Preserve the existing JSON example line because #257 appends its
    # explanatory-group field immediately after this stable anchor.
    anchor = '  "visible_components": ["aircraft", "wing"],\n'
    replacement = anchor + '  "visible_subject_groups": {visible_subject_groups_template},\n'
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence JSON anchor mismatch")
    text = text.replace(anchor, replacement, 1)

    anchor = '''    payload = _extract_json(response.choices[0].message.content)\n    result = normalize_dominance_result(payload, action_required=action_required)\n    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)\n    result["pass"] = passes_dominance_gate(result)\n    return result\n'''
    replacement = '''    payload = _extract_json(response.choices[0].message.content)\n    result = normalize_dominance_result(payload, action_required=action_required)\n    result = _still_vision_apply_structured_evidence(\n        result, payload, required_subject_groups\n    )\n    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)\n    result["pass"] = passes_dominance_gate(result)\n    return result\n'''
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence result anchor mismatch")
    text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_still_verifier():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_PASS_PROPAGATION_V1" not in text:
        raise RuntimeError("structured evidence requires #256 pass propagation")

    anchor = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    # STILL_IMAGE_VERIFIER_CONTRACT_V1\n'''
    replacement = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    # STILL_VISION_EVIDENCE_GROUPS_V1\n    if not bool(result.get("schema_parser_consistency", True)):\n        return False, result\n    # STILL_IMAGE_VERIFIER_CONTRACT_V1\n'''
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence verifier result anchor mismatch")
    text = text.replace(anchor, replacement, 1)

    anchor = '''    def _visible(anchor):\n        groups = result.get("visible_subject_groups") or {}\n        if isinstance(groups, dict) and bool(groups.get(anchor, False)):\n            return True\n        aliases = set(_anchor_aliases(anchor)) | {anchor}\n        return bool(visible_words & aliases)\n'''
    replacement = anchor
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence _visible anchor mismatch")

    anchor = '''    if parent_domain_satisfied:\n        result["parent_domain_satisfied"] = list(parent_domain_satisfied)\n    return True, result\n'''
    replacement = '''    if parent_domain_satisfied:\n        result["parent_domain_satisfied"] = list(parent_domain_satisfied)\n\n    required_groups = list(result.get("required_subject_groups") or anchors)\n    visible_groups = result.get("visible_subject_groups") or {}\n    missing_groups = [group for group in required_groups if not _visible(group)]\n    if parent_domain_satisfied:\n        missing_groups = [group for group in missing_groups if group not in parent_domain_satisfied]\n    accepted = not bool(missing_groups)\n    print(\n        "[VISION_EVIDENCE_TRACE] "\n        f"pass={bool(result.get('pass', False))} "\n        f"required_subject_groups={'+'.join(required_groups) or 'none'} "\n        f"visible_subject_groups={visible_groups} "\n        f"visible_components={'+'.join(str(v) for v in result.get('visible_components', []) or []) or 'none'} "\n        f"parent_domain_satisfied={'+'.join(result.get('parent_domain_satisfied', []) or []) or 'none'} "\n        f"missing={'+'.join(missing_groups) or 'none'} "\n        f"schema_parser_consistency={bool(result.get('schema_parser_consistency', True))} "\n        f"result={'ACCEPT' if accepted else 'REJECT'} "\n        f"reason={str(result.get('reason') or '')[:240]}"\n    )\n    return accepted, result\n'''
    if text.count(anchor) != 1:
        raise RuntimeError("structured evidence verifier return anchor mismatch")
    text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")


def main():
    patch_hook_visual_dominance()
    patch_still_verifier()
    print("✅ Structured still Vision evidence groups preserve approved engine/chevron proof without fail-open")


if __name__ == "__main__":
    main()
