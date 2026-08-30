from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# STILL_PARENT_DOMAIN_PROPAGATION_V1"


def main():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "STILL_IMAGE_PASS_PROPAGATION_V1" not in text:
        raise RuntimeError("parent-domain propagation requires #256 pass propagation")
    if "STILL_VISION_EVIDENCE_GROUPS_V1" not in text:
        raise RuntimeError("parent-domain propagation requires #259 structured evidence")
    if "STILL_VISION_EVIDENCE_TRACE_V1" not in text:
        raise RuntimeError("parent-domain propagation requires Vision evidence trace")

    function_start = text.find("def _verify_motion_clip(")
    function_end = text.find("\ndef ", function_start + 1)
    if function_start < 0:
        raise RuntimeError("still verifier function missing")
    if function_end < 0:
        function_end = len(text)
    section = text[function_start:function_end]

    stale_anchor_read = '''    anchors = extract_query_anchors(str(scene.get("keyword", "") or ""))

    # STILL_IMAGE_PASS_PROPAGATION_V1
'''
    authoritative_anchor_read = '''    # STILL_PARENT_DOMAIN_PROPAGATION_V1
    # Authority order:
    #   1) structured verifier required_subject_groups
    #   2) current, scene-matching visual subject contract required_anchors
    #   3) current, scene-matching authoritative effective visual query
    #   4) legacy scene["keyword"] fallback
    # Never let a global contract left by another Scene override this Scene.
    required_subject_groups = [
        str(group or "").strip().lower()
        for group in (result.get("required_subject_groups") or [])
        if str(group or "").strip()
    ]
    anchors = []
    parent_domain_anchor_source = "legacy_scene_keyword"

    if required_subject_groups:
        anchors = list(dict.fromkeys(required_subject_groups))
        parent_domain_anchor_source = "required_subject_groups"
    else:
        try:
            from video.video_downloader import get_current_visual_subject_anchor_contract
            visual_subject_contract = get_current_visual_subject_anchor_contract() or {}
        except (ImportError, AttributeError, TypeError):
            visual_subject_contract = {}

        def _query_key(value):
            return " ".join(str(value or "").strip().lower().split())

        scene_keyword_key = _query_key(scene.get("keyword", ""))
        contract_original_key = _query_key(visual_subject_contract.get("original_query", ""))
        contract_effective_key = _query_key(visual_subject_contract.get("effective_query", ""))
        contract_matches_scene = bool(
            scene_keyword_key
            and scene_keyword_key in {contract_original_key, contract_effective_key}
        )

        contract_required = [
            str(group or "").strip().lower()
            for group in (visual_subject_contract.get("required_anchors") or [])
            if str(group or "").strip()
        ]
        if contract_matches_scene and contract_required:
            anchors = list(dict.fromkeys(contract_required))
            parent_domain_anchor_source = "visual_subject_contract"
        elif contract_matches_scene and contract_effective_key:
            parsed = list(extract_query_anchors(contract_effective_key))
            if parsed:
                anchors = parsed
                parent_domain_anchor_source = "effective_query"

    if not anchors:
        anchors = extract_query_anchors(str(scene.get("keyword", "") or ""))
        parent_domain_anchor_source = "legacy_scene_keyword"

    result["parent_domain_anchor_source"] = parent_domain_anchor_source

    # STILL_IMAGE_PASS_PROPAGATION_V1
'''
    if section.count(stale_anchor_read) != 1:
        raise RuntimeError("parent-domain stale anchor read boundary mismatch")
    section = section.replace(stale_anchor_read, authoritative_anchor_read, 1)

    # #259 structured evidence remains authoritative. Explicit structured False
    # must not fall through to loose component aliases (for example, `jet` from
    # `jet engine` must not silently become aircraft=True).
    visible_fallback = '''    def _visible(anchor):
        groups = result.get("visible_subject_groups") or {}
        if isinstance(groups, dict) and bool(groups.get(anchor, False)):
            return True
        aliases = set(_anchor_aliases(anchor)) | {anchor}
        return bool(visible_words & aliases)
'''
    visible_authority = '''    def _visible(anchor):
        groups = result.get("visible_subject_groups") or {}
        if isinstance(groups, dict) and anchor in groups:
            return bool(groups.get(anchor, False))
        aliases = set(_anchor_aliases(anchor)) | {anchor}
        return bool(visible_words & aliases)
'''
    if section.count(visible_fallback) != 1:
        raise RuntimeError("parent-domain structured visibility authority boundary mismatch")
    section = section.replace(visible_fallback, visible_authority, 1)

    early_consistency = '''    if not bool(result.get("schema_parser_consistency", True)):
        missing = [
            group for group, visible in (result.get("visible_subject_groups") or {}).items()
            if not bool(visible)
        ]
        _vision_evidence_trace("REJECT", missing)
        return False, result
'''
    deferred_consistency = '''    raw_schema_parser_consistency = bool(result.get("schema_parser_consistency", True))
    raw_evidence_inconsistencies = list(result.get("evidence_inconsistencies") or [])
    raw_visible_subject_groups = dict(result.get("visible_subject_groups") or {})
    result["raw_schema_parser_consistency"] = raw_schema_parser_consistency
    result["raw_evidence_inconsistencies"] = list(raw_evidence_inconsistencies)
    result["raw_visible_subject_groups"] = dict(raw_visible_subject_groups)
'''
    if section.count(early_consistency) != 1:
        raise RuntimeError("parent-domain early consistency boundary mismatch")
    section = section.replace(early_consistency, deferred_consistency, 1)

    final_block = '''    if parent_domain_satisfied:
        result["parent_domain_satisfied"] = list(parent_domain_satisfied)

    required_groups = list(result.get("required_subject_groups") or anchors)
    visible_groups = result.get("visible_subject_groups") or {}
    missing_groups = [group for group in required_groups if not _visible(group)]
    if parent_domain_satisfied:
        missing_groups = [group for group in missing_groups if group not in parent_domain_satisfied]
    accepted = not bool(missing_groups)
    print(
        "[VISION_EVIDENCE_TRACE] "
        f"pass={bool(result.get('pass', False))} "
        f"required_subject_groups={'+'.join(required_groups) or 'none'} "
        f"visible_subject_groups={visible_groups} "
        f"visible_components={'+'.join(str(v) for v in result.get('visible_components', []) or []) or 'none'} "
        f"parent_domain_satisfied={'+'.join(result.get('parent_domain_satisfied', []) or []) or 'none'} "
        f"missing={'+'.join(missing_groups) or 'none'} "
        f"schema_parser_consistency={bool(result.get('schema_parser_consistency', True))} "
        f"result={'ACCEPT' if accepted else 'REJECT'} "
        f"reason={str(result.get('reason') or '')[:240]}"
    )
    return accepted, result
'''
    resolved_block = '''    if parent_domain_satisfied:
        result["parent_domain_satisfied"] = list(parent_domain_satisfied)

    required_groups = list(result.get("required_subject_groups") or anchors)
    raw_visible_groups = dict(result.get("raw_visible_subject_groups") or result.get("visible_subject_groups") or {})
    effective_subject_groups = {
        group: (
            bool(raw_visible_groups[group])
            if group in raw_visible_groups
            else bool(_visible(group))
        )
        for group in required_groups
    }
    for group in parent_domain_satisfied:
        if group in effective_subject_groups:
            effective_subject_groups[group] = True

    resolved_inconsistencies = []
    unresolved_inconsistencies = []
    for inconsistency in raw_evidence_inconsistencies:
        if (
            inconsistency == "structured_group_component_disagree:aircraft:group=true:component=false"
            and "aircraft" in parent_domain_satisfied
        ):
            resolved_inconsistencies.append(inconsistency)
        else:
            unresolved_inconsistencies.append(inconsistency)

    result["resolved_evidence_inconsistencies"] = list(resolved_inconsistencies)
    result["evidence_inconsistencies"] = list(unresolved_inconsistencies)
    result["schema_parser_consistency"] = not bool(unresolved_inconsistencies)
    result["effective_subject_groups"] = dict(effective_subject_groups)

    missing_groups = [
        group for group in required_groups
        if not bool(effective_subject_groups.get(group, False))
    ]
    result["missing_subject_groups"] = list(missing_groups)
    accepted = (
        bool(result.get("pass", False))
        and bool(result.get("schema_parser_consistency", True))
        and not bool(missing_groups)
    )
    print(
        "[VISION_EVIDENCE_TRACE] "
        f"pass={bool(result.get('pass', False))} "
        f"required_subject_groups={'+'.join(required_groups) or 'none'} "
        f"raw_visible_subject_groups={raw_visible_groups} "
        f"visible_components={'+'.join(str(v) for v in result.get('visible_components', []) or []) or 'none'} "
        f"parent_domain_anchor_source={str(result.get('parent_domain_anchor_source') or 'legacy_scene_keyword')} "
        f"parent_domain_satisfied={'+'.join(result.get('parent_domain_satisfied', []) or []) or 'none'} "
        f"effective_subject_groups={effective_subject_groups} "
        f"missing={'+'.join(missing_groups) or 'none'} "
        f"schema_parser_consistency={bool(result.get('schema_parser_consistency', True))} "
        f"result={'ACCEPT' if accepted else 'REJECT'} "
        f"reason={str(result.get('reason') or '')[:240]}"
    )
    return accepted, result
'''
    if section.count(final_block) != 1:
        raise RuntimeError("parent-domain final evidence boundary mismatch")
    section = section.replace(final_block, resolved_block, 1)

    text = text[:function_start] + section + text[function_end:]
    path.write_text(text, encoding="utf-8")
    print("✅ Trusted still parent-domain propagation applied with authoritative anchor source")


if __name__ == "__main__":
    main()
