from pathlib import Path

MARKER = "# STILL_IMAGE_VERIFIER_CONTRACT_V1"


def patch_hook_verifier():
    path = Path("video/hook_visual_dominance.py")
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    normalize_needle = '''        "reason": str(payload.get("reason", "")).strip()[:500],
    }
'''
    normalize_replacement = '''        "reason": str(payload.get("reason", "")).strip()[:500],
        # STILL_IMAGE_VERIFIER_CONTRACT_V1
        "subject_visibility": score("subject_visibility", score("subject_dominance")),
        "visible_components": [
            str(component or "").strip().lower()
            for component in (payload.get("visible_components") or [])
            if str(component or "").strip()
        ],
        "obvious_generation_artifact": bool(payload.get("obvious_generation_artifact", False)),
        "factual_visual_contradiction": bool(payload.get("factual_visual_contradiction", False)),
    }
'''
    if text.count(normalize_needle) != 1:
        raise RuntimeError("still verifier normalize anchor mismatch")
    text = text.replace(normalize_needle, normalize_replacement, 1)

    prompt_needle = '''- vertical_crop_subject_visible: false if the 9:16 crop makes the promised subject small, cut off, peripheral, or hard to identify.

Examples:
'''
    prompt_replacement = '''- vertical_crop_subject_visible: false if the 9:16 crop makes the promised subject small, cut off, peripheral, or hard to identify.
- visible_components: list ONLY concrete physical components visibly identifiable in the frames. Include required search components such as aircraft, wing, winglet, window, engine only when they are actually visible; do not infer them from the keyword.
- obvious_generation_artifact: true for malformed geometry, impossible duplicate parts, unreadable pseudo-text, or other obvious generated-image artifacts.
- factual_visual_contradiction: true if the visible image contradicts the narration/visual goal or depicts a different physical subject.

Examples:
'''
    if text.count(prompt_needle) != 1:
        raise RuntimeError("still verifier prompt anchor mismatch")
    text = text.replace(prompt_needle, prompt_replacement, 1)

    json_needle = '''  "vertical_crop_subject_visible": false,
  "reason": "short concrete explanation"
}}
'''
    json_replacement = '''  "vertical_crop_subject_visible": false,
  "visible_components": ["aircraft", "wing"],
  "obvious_generation_artifact": false,
  "factual_visual_contradiction": false,
  "reason": "short concrete explanation"
}}
'''
    if text.count(json_needle) != 1:
        raise RuntimeError("still verifier JSON anchor mismatch")
    text = text.replace(json_needle, json_replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_still_fallback():
    path = Path("video/still_image_fallback.py")
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    verifier_needle = '''    result = evaluate_hook_subject_dominance(candidate, scene)
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
    # Use the verifier's real strict gate instead of a field that older
    # normalize_dominance_result() never returned. Keep generated artifacts,
    # factual contradictions, crop/dominance and concrete-anchor checks fail-closed.
    if not result.get("pass", False):
        return False, result
    if result.get("obvious_generation_artifact", False):
        return False, result
    if result.get("factual_visual_contradiction", False):
        return False, result

    visible_words = set()
'''
    if text.count(verifier_needle) != 1:
        raise RuntimeError("still fallback verifier anchor mismatch")
    text = text.replace(verifier_needle, verifier_replacement, 1)
    path.write_text(text, encoding="utf-8")


def main():
    patch_hook_verifier()
    patch_still_fallback()
    print("✅ Still-image verifier contract aligned with strict dominance + visible anchors")


if __name__ == "__main__":
    main()
