import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import ci_still_action_gate_hotfix as hotfix


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "video" / "still_image_fallback.py"
DOMINANCE = ROOT / "video" / "hook_visual_dominance.py"


def _run(script, cwd):
    subprocess.run(
        [sys.executable, script], check=True, cwd=cwd, capture_output=True, text=True,
    )


def case_a_standalone_install_on_pristine_source(original):
    # Defense in depth: applied alone (no other still hotfix has touched the
    # file yet), the installer still gates on the evaluator's own `pass`.
    with tempfile.TemporaryDirectory(prefix="still_action_gate_rc3_a_") as temp_dir:
        target = Path(temp_dir) / "still_image_fallback.py"
        target.write_text(original, encoding="utf-8")
        old_still = hotfix.STILL_PATH
        try:
            hotfix.STILL_PATH = target
            hotfix.main()
            patched = target.read_text(encoding="utf-8")
            compile(patched, str(target), "exec")
        finally:
            hotfix.STILL_PATH = old_still

    assert hotfix.MARKER in patched
    assert 'if not bool(result.get("pass", False)):' in patched
    assert patched.index('if not bool(result.get("pass", False)):') < patched.index(
        'if result.get("obvious_generation_artifact", False):'
    )
    print("CASE A standalone install on pristine source: PASS")


def case_b_real_composition_order_verifier_contract_then_action_gate():
    # The actual production order: ci_final_visual_semantic_qa_hotfix.py runs
    # ci_still_image_verifier_contract_hotfix.py (which rewrites the function's
    # top AND bottom blocks to honor `pass`), THEN this installer. This is
    # exactly the sequence that previously crashed with "still fallback
    # verifier anchor mismatch" when this installer's own early call site
    # (inside ci_fixed_aviation_scope_contract_hotfix.py) ran first instead.
    with tempfile.TemporaryDirectory(prefix="still_action_gate_rc3_b_") as temp_dir:
        scratch = Path(temp_dir) / "repo"
        shutil.copytree(
            ROOT, scratch, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        before = (scratch / "video" / "still_image_fallback.py").read_text(encoding="utf-8")

        _run("ci_still_image_verifier_contract_hotfix.py", cwd=scratch)
        after_verifier_contract = (scratch / "video" / "still_image_fallback.py").read_text(
            encoding="utf-8"
        )
        assert after_verifier_contract != before
        compile(after_verifier_contract, "still_image_fallback.py", "exec")

        # This is the exact step that previously crashed.
        _run("ci_still_action_gate_hotfix.py", cwd=scratch)
        final_text = (scratch / "video" / "still_image_fallback.py").read_text(encoding="utf-8")
        compile(final_text, "still_image_fallback.py", "exec")

    # The installer must have skipped (already-satisfied), not double-patched.
    assert hotfix.MARKER not in final_text
    assert final_text == after_verifier_contract
    assert 'if not result.get("pass", False):' in final_text
    print("CASE B real composition order (verifier-contract then action-gate): PASS")


def case_c_wiring_lives_at_the_correct_call_site():
    qa_hotfix = (ROOT / "ci_final_visual_semantic_qa_hotfix.py").read_text(encoding="utf-8")
    assert "ci_still_action_gate_hotfix" in qa_hotfix
    assert "_patch_still_action_gate()" in qa_hotfix
    install_index = qa_hotfix.index("_patch_still_action_gate()")
    verifier_index = qa_hotfix.index("_patch_still_image_verifier_contract()")
    assert verifier_index < install_index, (
        "still action gate must be composed after the verifier contract hotfix"
    )

    aviation_compat = (ROOT / "ci_fixed_aviation_scope_contract_hotfix.py").read_text(encoding="utf-8")
    assert "ci_still_action_gate_hotfix" not in aviation_compat, (
        "still action gate must not be wired into the early aviation-compat "
        "call site again -- that ordering is exactly what broke "
        "ci_still_image_verifier_contract_hotfix.py's anchor match"
    )
    print("CASE C wiring lives at the correct (post-verifier-contract) call site: PASS")


def main():
    original = SOURCE.read_text(encoding="utf-8")
    dominance = DOMINANCE.read_text(encoding="utf-8")

    # Reproduce the exact structural bug: the verifier calls the evaluator but
    # does not honor its authoritative `pass` result before accepting anchors.
    assert hotfix.MARKER not in original
    assert 'result = evaluate_hook_subject_dominance(candidate, scene)' in original

    case_a_standalone_install_on_pristine_source(original)
    case_b_real_composition_order_verifier_contract_then_action_gate()
    case_c_wiring_lives_at_the_correct_call_site()

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

    print("PASS: Root Cause #3 still verifier now honors the existing action/dominance gate")


if __name__ == "__main__":
    main()
