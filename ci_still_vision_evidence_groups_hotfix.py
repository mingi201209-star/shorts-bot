from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# STILL_VISION_EVIDENCE_GROUPS_V1"


_HELPERS = r'''

# STILL_VISION_EVIDENCE_GROUPS_V1
# Run 33259567582: the Vision reason said the engine chevron was clearly
# visible, while the structured visible_components contained engine+wing.
# Keep structured evidence authoritative. Reason text is diagnostics only and
# can never create visible evidence or make a failed subject group pass.
_STILL_VISION_GROUP_ALIASES = {
    "chevron": {
        "chevron", "chevrons", "serrated", "serrated edge",
        "serrated nozzle", "sawtooth", "sawtooth trailing edge",
        "톱니", "셰브론",
    },
}


def _still_vision_norm_component(value):
    value = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    return re.sub(r"\\s+", " ", value).strip()


def _still_vision_required_subject_groups(scene):
    try:
        from video.video_downloader import extract_query_anchors
        groups = list(extract_query_anchors(str((scene or {}).get("keyword") or "")) or [])
    except Exception:
        groups = []
    ordered = []
    for group in groups:
        group = _still_vision_norm_component(group)
        if group and group not in ordered:
            ordered.append(group)
    return ordered


def _still_vision_component_matches_group(component, group):
    component = _still_vision_norm_component(component)
    group = _still_vision_norm_component(group)
    if not component or not group:
        return False
    aliases = set(_STILL_VISION_GROUP_ALIASES.get(group, ())) | {group}
    if component in aliases:
        return True
    component_words = set(component.split())
    for alias in aliases:
        alias = _still_vision_norm_component(alias)
        if alias and (alias == component or set(alias.split()).issubset(component_words)):
            return True
    return False


def _still_vision_reason_mentions_group(reason, group):
    # Diagnostics only. This function MUST NOT influence visible evidence.
    reason = _still_vision_norm_component(reason)
    if not reason:
        return False
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
    inconsistencies = []
    for group in required_groups:
        component_visible = any(
            _still_vision_component_matches_group(component, group)
            for component in components
        )
        if group in explicit:
            explicit_visible = bool(explicit[group])
            if explicit_visible != component_visible:
                inconsistencies.append(
                    f"structured_group_component_disagree:{group}:group={str(explicit_visible).lower()}:component={str(component_visible).lower()}"
                )
            # Require the two structured fields to agree. A free-text reason is
            # never used to repair either side.
            visible = explicit_visible and component_visible
        else:
            # Backward-compatible structured-only path: existing callers that
            # provide visible_components remain authoritative.
            visible = component_visible
        visible_groups[group] = bool(visible)

    # Canonicalize approved STRUCTURED aliases only. This lets a model output
    # `serrated nozzle` while downstream #256 still sees the canonical chevron
    # group. No text is extracted from reason.
    canonical_components = list(components)
    for group, visible in visible_groups.items():
        if visible and group not in canonical_components:
            canonical_components.append(group)

    reason = str(payload.get("reason") or "").strip()[:500]
    for group, visible in visible_groups.items():
        if not visible and _still_vision_reason_mentions_group(reason, group):
            inconsistencies.append(f"reason_claims_missing_structured_group:{group}")

    result["required_subject_groups"] = list(required_groups)
    result["visible_subject_groups"] = dict(visible_groups)
    result["visible_components"] = canonical_components
    result["schema_parser_consistency"] = not bool(inconsistencies)
    result["evidence_inconsistencies"] = list(inconsistencies)
    return result
'''


def patch_hook_visual_dominance():
    path = ROOT / "video/hook_visual_dominance.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_VERIFIER_CONTRACT_V1" not in text:
        raise RuntimeError("structured still evidence patch requires still verifier contract")

    helper_anchor = "\ndef _extract_vertical_frames(video_url):\n"
    if text.count(helper_anchor) != 1:
        raise RuntimeError("structured evidence helper anchor mismatch")
    text = text.replace(helper_anchor, _HELPERS + helper_anchor, 1)

    keyword_anchor = '''    keyword = str(scene.get("keyword", "") or "").strip()\n\n    prompt = f"""\n'''
    keyword_replacement = '''    keyword = str(scene.get("keyword", "") or "").strip()\n    required_subject_groups = _still_vision_required_subject_groups(scene)\n    required_subject_groups_json = json.dumps(required_subject_groups, ensure_ascii=False)\n    visible_subject_groups_template = json.dumps(\n        {group: False for group in required_subject_groups},\n        ensure_ascii=False,\n    )\n\n    prompt = f"""\n'''
    if text.count(keyword_anchor) != 1:
        raise RuntimeError("structured evidence keyword anchor mismatch")
    text = text.replace(keyword_anchor, keyword_replacement, 1)

    observable_anchor = "Observable action required: {str(action_required).lower()}\n\nIdentify the concrete subject explicitly promised by the Hook. Then score:\n"
    observable_replacement = "Observable action required: {str(action_required).lower()}\nRequired subject groups: {required_subject_groups_json}\n\nStructured subject-evidence contract:\n- visible_components is authoritative structured evidence. List only concrete components visibly identifiable in the supplied frames.\n- visible_subject_groups MUST contain every required subject group above as true/false. Set true only when that group is visibly identifiable.\n- For the chevron group, visible structured aliases may include chevron, chevrons, serrated edge, serrated nozzle, sawtooth trailing edge, 톱니, or 셰브론.\n- Never treat wing, engine, blade, fan, or gear as evidence for the chevron group.\n- Keep reason consistent with the structured fields. Do not claim a required group is visible in reason when its structured group is false or absent from visible_components.\n\nIdentify the concrete subject explicitly promised by the Hook. Then score:\n"
    if text.count(observable_anchor) != 1:
        raise RuntimeError("structured evidence prompt anchor mismatch")
    text = text.replace(observable_anchor, observable_replacement, 1)

    visible_prompt_anchor = "- visible_components: list ONLY concrete physical components visibly identifiable in the frames. Include required search components such as aircraft, wing, winglet, window, engine only when they are actually visible; do not infer them from the keyword.\n"
    visible_prompt_replacement = "- visible_components: list ONLY concrete physical components visibly identifiable in the frames. For required groups, prefer their canonical group label; approved structured aliases are allowed only as described above. Do not infer components from the keyword.\n- visible_subject_groups: return exactly the required group keys with boolean visibility values. Template: {visible_subject_groups_template}\n"
    if text.count(visible_prompt_anchor) != 1:
        raise RuntimeError("structured evidence visible-components prompt anchor mismatch")
    text = text.replace(visible_prompt_anchor, visible_prompt_replacement, 1)

    json_anchor = '  "visible_components": ["aircraft", "wing"],\n'
    json_replacement = '  "visible_components": ["concrete visible component"],\n  "visible_subject_groups": {visible_subject_groups_template},\n'
    if text.count(json_anchor) != 1:
        raise RuntimeError("structured evidence JSON example anchor mismatch")
    text = text.replace(json_anchor, json_replacement, 1)

    result_anchor = '''    payload = _extract_json(response.choices[0].message.content)\n    result = normalize_dominance_result(payload, action_required=action_required)\n    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)\n    result["pass"] = passes_dominance_gate(result)\n    return result\n'''
    result_replacement = '''    payload = _extract_json(response.choices[0].message.content)\n    result = normalize_dominance_result(payload, action_required=action_required)\n    result = _still_vision_apply_structured_evidence(\n        result, payload, required_subject_groups\n    )\n    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)\n    result["pass"] = passes_dominance_gate(result)\n    return result\n'''
    if text.count(result_anchor) != 1:
        raise RuntimeError("structured evidence result anchor mismatch")
    text = text.replace(result_anchor, result_replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_still_verifier():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_PASS_PROPAGATION_V1" not in text:
        raise RuntimeError("structured evidence patch requires #256 pass propagation")

    result_anchor = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    # STILL_IMAGE_VERIFIER_CONTRACT_V1\n'''
    result_replacement = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    # STILL_VISION_EVIDENCE_GROUPS_V1\n    if not bool(result.get("schema_parser_consistency", True)):\n        return False, result\n    # STILL_IMAGE_VERIFIER_CONTRACT_V1\n'''
    if text.count(result_anchor) != 1:
        raise RuntimeError("structured evidence still result anchor mismatch")
    text = text.replace(result_anchor, result_replacement, 1)

    visible_anchor = '''    def _visible(anchor):\n        aliases = set(_anchor_aliases(anchor)) | {anchor}\n        return bool(visible_words & aliases)\n'''
    visible_replacement = '''    def _visible(anchor):\n        groups = result.get("visible_subject_groups") or {}\n        if isinstance(groups, dict) and bool(groups.get(anchor, False)):\n            return True\n        aliases = set(_anchor_aliases(anchor)) | {anchor}\n        return bool(visible_words & aliases)\n'''
    if text.count(visible_anchor) != 1:
        raise RuntimeError("structured evidence _visible anchor mismatch")
    text = text.replace(visible_anchor, visible_replacement, 1)

    return_anchor = '''    if parent_domain_satisfied:\n        result["parent_domain_satisfied"] = list(parent_domain_satisfied)\n    return True, result\n'''
    return_replacement = '''    if parent_domain_satisfied:\n        result["parent_domain_satisfied"] = list(parent_domain_satisfied)\n\n    required_groups = list(result.get("required_subject_groups") or anchors)\n    visible_groups = result.get("visible_subject_groups") or {}\n    missing_groups = [group for group in required_groups if not _visible(group)]\n    accepted = not bool(missing_groups)\n    if parent_domain_satisfied:\n        missing_groups = [group for group in missing_groups if group not in parent_domain_satisfied]\n        accepted = not bool(missing_groups)\n    print(\n        "[VISION_EVIDENCE_TRACE] "\n        f"pass={bool(result.get('pass', False))} "\n        f"required_subject_groups={'+'.join(required_groups) or 'none'} "\n        f"visible_subject_groups={visible_groups} "\n        f"visible_components={'+'.join(str(value) for value in result.get('visible_components', []) or []) or 'none'} "\n        f"parent_domain_satisfied={'+'.join(result.get('parent_domain_satisfied', []) or []) or 'none'} "\n        f"missing={'+'.join(missing_groups) or 'none'} "\n        f"schema_parser_consistency={bool(result.get('schema_parser_consistency', True))} "\n        f"result={'ACCEPT' if accepted else 'REJECT'} "\n        f"reason={str(result.get('reason') or '')[:240]}"\n    )\n    return accepted, result\n'''
    if text.count(return_anchor) != 1:
        raise RuntimeError("structured evidence still return anchor mismatch")
    text = text.replace(return_anchor, return_replacement, 1)
    path.write_text(text, encoding="utf-8")


def main():
    patch_hook_visual_dominance()
    patch_still_verifier()
    print("✅ Structured still Vision evidence groups preserve chevron proof without fail-open")


if __name__ == "__main__":
    main()
