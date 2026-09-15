from pathlib import Path

MARKER = "# STILL_IMAGE_VERIFIER_CONTRACT_V1"
PASS_PROPAGATION_MARKER = "# STILL_IMAGE_PASS_PROPAGATION_V1"
ACTION_GATE_MARKER = "# STILL_ACTION_GATE_ROOT_CAUSE_3_V1"


def patch_hook_verifier():
    path = Path("video/hook_visual_dominance.py")
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    normalize_start = text.find("def normalize_dominance_result(")
    normalize_end = text.find("\ndef passes_dominance_gate", normalize_start)
    if normalize_start < 0 or normalize_end < 0:
        raise RuntimeError("still verifier normalize function boundary missing")
    normalize_section = text[normalize_start:normalize_end]
    reason_line = '        "reason": str(payload.get("reason", "")).strip()[:500],\n'
    if normalize_section.count(reason_line) != 1:
        raise RuntimeError("still verifier normalize reason anchor mismatch")
    extra_fields = '''        # STILL_IMAGE_VERIFIER_CONTRACT_V1
        "subject_visibility": score("subject_visibility", score("subject_dominance")),
        "visible_components": [
            str(component or "").strip().lower()
            for component in (payload.get("visible_components") or [])
            if str(component or "").strip()
        ],
        "obvious_generation_artifact": bool(payload.get("obvious_generation_artifact", False)),
        "factual_visual_contradiction": bool(payload.get("factual_visual_contradiction", False)),
'''
    normalize_section = normalize_section.replace(reason_line, reason_line + extra_fields, 1)
    text = text[:normalize_start] + normalize_section + text[normalize_end:]

    prompt_needle = "- vertical_crop_subject_visible: false if the 9:16 crop makes the promised subject small, cut off, peripheral, or hard to identify.\n"
    prompt_extra = (
        "- visible_components: list ONLY concrete physical components visibly identifiable in the frames. Include required search components such as aircraft, wing, winglet, window, engine only when they are actually visible; do not infer them from the keyword.\n"
        "- obvious_generation_artifact: true for malformed geometry, impossible duplicate parts, unreadable pseudo-text, or other obvious generated-image artifacts.\n"
        "- factual_visual_contradiction: true if the visible image contradicts the narration/visual goal or depicts a different physical subject.\n"
    )
    if text.count(prompt_needle) != 1:
        raise RuntimeError("still verifier prompt anchor mismatch")
    text = text.replace(prompt_needle, prompt_needle + prompt_extra, 1)

    reason_json = '  "reason": "short concrete explanation"\n'
    json_extra = (
        '  "visible_components": ["aircraft", "wing"],\n'
        '  "obvious_generation_artifact": false,\n'
        '  "factual_visual_contradiction": false,\n'
    )
    if text.count(reason_json) != 1:
        raise RuntimeError("still verifier JSON reason anchor mismatch")
    text = text.replace(reason_json, json_extra + reason_json, 1)
    path.write_text(text, encoding="utf-8")


def patch_still_fallback():
    path = Path("video/still_image_fallback.py")
    text = path.read_text(encoding="utf-8")
    if PASS_PROPAGATION_MARKER in text:
        return

    if MARKER not in text:
        generation_prompt_needle = '''        "Show the exact physical subject named in the narration clearly and prominently. "
        "No text, captions, logos, diagrams with invented labels, unrelated decorative objects, or cross-domain metaphors. "
'''
        generation_prompt_replacement = '''        "Show the exact physical subject named in the narration clearly and prominently. "
        # STILL_IMAGE_VERIFIER_CONTRACT_V1
        "Every concrete physical component named in the Search concept must also be visibly present, clear, and identifiable in-frame; do not merely imply it from context. "
        "For example, an aircraft+wing search concept must visibly show both the aircraft and its wing even when the broader visual goal is landing or runway contact. "
        "No text, captions, logos, diagrams with invented labels, unrelated decorative objects, or cross-domain metaphors. "
'''
        if text.count(generation_prompt_needle) != 1:
            raise RuntimeError("still fallback generation prompt anchor mismatch")
        text = text.replace(generation_prompt_needle, generation_prompt_replacement, 1)

        base_verifier_needle = '''    result = evaluate_hook_subject_dominance(candidate, scene)
    if result.get("obvious_generation_artifact", False):
        return False, result
    if result.get("factual_visual_contradiction", False):
        return False, result
    if float(result.get("subject_visibility", 0) or 0) < 6.0:
        return False, result

    visible_words = set()
'''
        verifier_replacement = '''    result = evaluate_hook_subject_dominance(candidate, scene)
    # STILL_IMAGE_VERIFIER_CONTRACT_V1
    # Use the verifier's real strict gate. This is intentionally idempotent
    # with the Root Cause #3 action-gate installer when that earlier installer
    # has already added the same fail-closed pass propagation.
    if not result.get("pass", False):
        return False, result
    if result.get("obvious_generation_artifact", False):
        return False, result
    if result.get("factual_visual_contradiction", False):
        return False, result

    visible_words = set()
'''
        if text.count(base_verifier_needle) == 1:
            text = text.replace(base_verifier_needle, verifier_replacement, 1)
        elif ACTION_GATE_MARKER in text:
            # The action-gate installer already inserted the authoritative
            # result["pass"] rejection. Preserve it and only add this contract
            # marker so later composition remains deterministic.
            action_comment = "    # STILL_ACTION_GATE_ROOT_CAUSE_3_V1\n"
            if text.count(action_comment) != 1:
                raise RuntimeError("still fallback action-gate marker mismatch")
            text = text.replace(action_comment, "    # STILL_IMAGE_VERIFIER_CONTRACT_V1\n" + action_comment, 1)
        else:
            raise RuntimeError("still fallback verifier anchor mismatch")

    anchor_loop_needle = '''    anchors = extract_query_anchors(str(scene.get("keyword", "") or ""))
    for anchor in anchors:
        aliases = set(_anchor_aliases(anchor)) | {anchor}
        if not (visible_words & aliases):
            return False, result
    return True, result
'''
    anchor_loop_replacement = '''    anchors = extract_query_anchors(str(scene.get("keyword", "") or ""))

    # STILL_IMAGE_PASS_PROPAGATION_V1
    profile = scene.get("_canonical_visual_supply") if isinstance(scene, dict) else None
    profile = profile if isinstance(profile, dict) else {}
    canonical = str(profile.get("canonical_subject") or "").strip().lower()
    try:
        canonical_confidence = float(profile.get("identity_confidence") or 0.0)
    except (TypeError, ValueError):
        canonical_confidence = 0.0
    anchor_set = set(anchors)

    def _visible(anchor):
        aliases = set(_anchor_aliases(anchor)) | {anchor}
        return bool(visible_words & aliases)

    trusted_jet_engine_parent = (
        canonical_confidence >= 0.80
        and "jet engine" in canonical
        and "chevron" in canonical
        and {"aircraft", "engine", "chevron"}.issubset(anchor_set)
        and _visible("engine")
        and _visible("chevron")
    )

    parent_domain_satisfied = []
    for anchor in anchors:
        if _visible(anchor):
            continue
        if anchor == "aircraft" and trusted_jet_engine_parent:
            parent_domain_satisfied.append(anchor)
            continue
        return False, result

    if parent_domain_satisfied:
        result["parent_domain_satisfied"] = list(parent_domain_satisfied)
    return True, result
'''
    if text.count(anchor_loop_needle) != 1:
        raise RuntimeError("still fallback visible-anchor loop mismatch")
    text = text.replace(anchor_loop_needle, anchor_loop_replacement, 1)
    path.write_text(text, encoding="utf-8")


def main():
    patch_hook_verifier()
    patch_still_fallback()
    print("✅ Still-image verifier contract aligned with strict dominance + visible anchors")
    print("✅ Still-image Vision PASS propagation preserves trusted jet-engine closeups without fail-open")


if __name__ == "__main__":
    main()
