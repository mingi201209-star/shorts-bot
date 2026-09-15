from pathlib import Path

EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "FIXED_AVIATION_SCOPE_CONTRACT_V1"


def _apply_run_34825745612_hook_repair_if_ready():
    from ci_run_34825745612_legacy_hook_repair_hotfix import main as patch_legacy_hook
    patch_legacy_hook()
    # Root Cause #3 is production-composed here so the existing workflow does
    # not need a new step or permission change. This compatibility installer is
    # already invoked by ci_aviation_context_signature_compat_hotfix.py.
    from ci_still_action_gate_hotfix import main as patch_still_action_gate
    patch_still_action_gate()


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ fixed aviation scope contract already applied")
        _apply_run_34825745612_hook_repair_if_ready()
        return

    specificity_marker = "_aviation_specificity_previous_build_context = build_execution_context"
    start = text.rfind(specificity_marker)
    if start < 0:
        raise RuntimeError("aviation specificity build-context wrapper not found")

    old = '''    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":\n        return context\n\n    rejected = [str(item).strip() for item in (rejected_topics or []) if str(item).strip()]\n'''
    idx = text.find(old, start)
    if idx < 0:
        raise RuntimeError("aviation specificity scope guard not found")

    new = '''    # FIXED_AVIATION_SCOPE_CONTRACT_V1\n    # A fixed aviation topic is aviation even when candidate_scope is intentionally\n    # blank. Production fixed-topic runs must still receive the specificity/mechanism\n    # contract instead of silently falling back to the generic Explorer prompt.\n    fixed = str(fixed_topic or "").strip()\n    scope_is_aviation = (\n        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() == "aviation"\n    )\n    fixed_is_aviation = bool(fixed) and any(\n        term in fixed.lower() for term in _AVIATION_DOMAIN_TERMS\n    )\n    if not (scope_is_aviation or fixed_is_aviation):\n        return context\n\n    rejected = [str(item).strip() for item in (rejected_topics or []) if str(item).strip()]\n'''

    text = text[:idx] + text[idx:].replace(old, new, 1)
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ fixed aviation topic now activates specificity contract with blank scope")
    _apply_run_34825745612_hook_repair_if_ready()


if __name__ == "__main__":
    main()
