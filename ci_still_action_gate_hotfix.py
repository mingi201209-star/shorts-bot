from pathlib import Path


STILL_PATH = Path("video/still_image_fallback.py")
MARKER = "# STILL_ACTION_GATE_ROOT_CAUSE_3_V1"
# ci_still_image_verifier_contract_hotfix.py (composed earlier in
# ci_final_visual_semantic_qa_hotfix.py, which this installer must run after)
# already rewrites this exact function to honor evaluate_hook_subject_dominance's
# own `pass` result as the very first check. Detect that already-satisfied
# shape so this installer never has to win a text-anchor race against it.
EXISTING_PASS_GATE_MARKER = "# STILL_IMAGE_VERIFIER_CONTRACT_V1"
ANCHOR = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    if result.get("obvious_generation_artifact", False):\n'''
REPLACEMENT = '''    result = evaluate_hook_subject_dominance(candidate, scene)\n    # STILL_ACTION_GATE_ROOT_CAUSE_3_V1\n    # A generated/reused still is only valid when the same visual-dominance\n    # evaluator that inspected it actually passes.  In Run 34847558126 the\n    # evaluator explicitly reported that the spoiler was visible but its\n    # promised action was not observable; _verify_motion_clip nevertheless\n    # accepted it because it re-checked only artifacts/contradictions/anchors\n    # and ignored result["pass"].  Honor the existing gate here.  This adds no\n    # model call, changes no threshold, and leaves static structure scenes\n    # unaffected because their action_required=False is already handled by\n    # passes_dominance_gate().\n    if not bool(result.get("pass", False)):\n        return False, result\n    if result.get("obvious_generation_artifact", False):\n'''


def main():
    text = STILL_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ still action gate already installed")
        return
    if EXISTING_PASS_GATE_MARKER in text:
        # ci_still_image_verifier_contract_hotfix.py already rewrote this
        # function's top AND bottom blocks to gate on evaluate_hook_subject_
        # dominance's own `pass` result before accepting artifacts/anchors --
        # exactly Root Cause #3's requirement. Nothing left to install, and no
        # text region remains that this installer's own anchor could safely
        # match without colliding with that rewrite.
        print("✅ still action gate already satisfied by existing verifier contract")
        return
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"still action gate anchor count mismatch: {count}")
    text = text.replace(ANCHOR, REPLACEMENT, 1)
    STILL_PATH.write_text(text, encoding="utf-8")
    print("✅ still action gate installed (existing evaluator pass honored)")


if __name__ == "__main__":
    main()
