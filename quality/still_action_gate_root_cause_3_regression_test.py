import tempfile
from pathlib import Path

import ci_still_action_gate_hotfix as hotfix


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "video" / "still_image_fallback.py"
DOMINANCE = ROOT / "video" / "hook_visual_dominance.py"


def main():
    original = SOURCE.read_text(encoding="utf-8")
    dominance = DOMINANCE.read_text(encoding="utf-8")

    # Reproduce the exact structural bug: the verifier calls the evaluator but
    # does not honor its authoritative `pass` result before accepting anchors.
    assert hotfix.MARKER not in original
    assert 'result = evaluate_hook_subject_dominance(candidate, scene)' in original

    with tempfile.TemporaryDirectory(prefix="still_action_gate_rc3_") as temp_dir:
        target = Path(temp_dir) / "still_image_fallback.py"
        target.write_text(original, encoding="utf-8")
        old_path = hotfix.STILL_PATH
        try:
            hotfix.STILL_PATH = target
            hotfix.main()
            patched = target.read_text(encoding="utf-8")
            compile(patched, str(target), "exec")
        finally:
            hotfix.STILL_PATH = old_path

    assert hotfix.MARKER in patched
    assert 'if not bool(result.get("pass", False)):' in patched
    assert patched.index('if not bool(result.get("pass", False)):') < patched.index(
        'if result.get("obvious_generation_artifact", False):'
    )

    # The authoritative gate already distinguishes action scenes from static
    # structure scenes. Root Cause #3 must reuse it, not invent a new threshold.
    assert "HOOK_ACTION_MATCH_MIN = 7.0" in dominance
    assert "if result.get(\"action_required\")" in dominance
    assert "< HOOK_ACTION_MATCH_MIN" in dominance
    assert "passes_dominance_gate(result)" in dominance

    installer = (ROOT / "ci_still_action_gate_hotfix.py").read_text(encoding="utf-8")
    forbidden = (
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "HOOK_ACTION_MATCH_MIN =",
        "HOOK_SUBJECT_DOMINANCE_MIN =",
        "STILL_IMAGE_MAX_PER_VIDEO =",
    )
    for token in forbidden:
        assert token not in installer, token

    composition = (ROOT / "ci_fixed_aviation_scope_contract_hotfix.py").read_text(encoding="utf-8")
    assert "ci_still_action_gate_hotfix" in composition
    assert "patch_still_action_gate()" in composition

    print("PASS: Root Cause #3 still verifier now honors the existing action/dominance gate")


if __name__ == "__main__":
    main()
