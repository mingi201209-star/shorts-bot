from pathlib import Path
import runpy

from ci_fixed_aviation_scope_contract_hotfix import main as patch_fixed_aviation_scope
from ci_fixed_topic_runtime_call_compat_hotfix import main as patch_runtime_call_compat

EXPLORER_PATH = Path("content/candidate_explorer.py")
MAIN_PATH = Path("main.py")
SCRIPT_PATH = Path("content/script_generator.py")


def _ensure_signature_keyword(text, function_name, keyword, default):
    start = text.rfind(f"def {function_name}(")
    if start < 0:
        raise RuntimeError(f"{function_name} definition not found")
    end = text.find("\n):", start)
    if end < 0:
        raise RuntimeError(f"{function_name} signature terminator not found")

    signature = text[start:end]
    if keyword in signature:
        return text

    insertion = f"    {keyword}={default},\n"
    for anchor in (
        "    fixed_topic=None,\n",
        "    rejected_topics=None,\n",
        "    recent_content=None,\n",
        "    recent_topics=None,\n",
    ):
        if anchor not in signature:
            continue
        extra = insertion
        if keyword == "fixed_topic_gate_feedback" and "fixed_topic" not in signature:
            extra = "    fixed_topic=None,\n" + insertion
        signature = signature.replace(anchor, anchor + extra, 1)
        return text[:start] + signature + text[end:]

    prefix = ""
    if keyword == "fixed_topic_gate_feedback" and "fixed_topic" not in signature:
        prefix = "    fixed_topic=None,\n"
    signature = signature.rstrip() + "\n" + prefix + insertion.rstrip("\n")
    return text[:start] + signature + text[end:]


def _ensure_forwarded_keyword(text, function_name, callee, keyword):
    function_start = text.rfind(f"def {function_name}(")
    if function_start < 0:
        raise RuntimeError(f"{function_name} definition not found")

    call_start = text.find(f"{callee}(\n", function_start)
    if call_start < 0:
        raise RuntimeError(f"{callee} call not found in {function_name}")
    call_end = text.find("\n    )", call_start)
    if call_end < 0:
        call_end = text.find("\n        )", call_start)
    if call_end < 0:
        raise RuntimeError(f"{callee} call terminator not found")

    call = text[call_start:call_end]
    if f"{keyword}=" in call:
        return text

    insertion = f"        {keyword}={keyword},\n"
    for anchor in (
        "        fixed_topic=fixed_topic,\n",
        "        rejected_topics=rejected_topics,\n",
        "        recent_content=recent_content,\n",
        "        recent_topics=recent_topics,\n",
    ):
        if anchor not in call:
            continue
        extra = insertion
        if keyword == "fixed_topic_gate_feedback" and "fixed_topic=" not in call:
            extra = "        fixed_topic=fixed_topic,\n" + insertion
        call = call.replace(anchor, anchor + extra, 1)
        return text[:call_start] + call + text[call_end:]

    raise RuntimeError(f"{callee} forwarding anchor not found")


def _patch_automatic_gate_feedback():
    text = MAIN_PATH.read_text(encoding="utf-8")
    marker = '''                if forced_topic:\n                    fixed_topic_gate_feedback = str(\n                        winner_gate.get(\n                            "reason",\n                            "",\n                        )\n                    ).strip()\n\n                print_budget_status()\n'''
    replacement = '''                gate_reject_reason = str(\n                    winner_gate.get(\n                        "reason",\n                        "",\n                    )\n                ).strip()\n\n                if forced_topic:\n                    fixed_topic_gate_feedback = gate_reject_reason\n                elif (\n                    os.environ.get(\n                        "SHORTS_CANDIDATE_SCOPE",\n                        "",\n                    ).strip().lower() == "aviation"\n                    and gate_reject_reason\n                ):\n                    automatic_feedback = (\n                        "[AUTOMATIC AVIATION GATE FEEDBACK] "\n                        f"rejected_topic={current_topic} | "\n                        f"reason={gate_reject_reason}"\n                    )\n                    if automatic_feedback not in rejected_topics:\n                        rejected_topics.append(automatic_feedback)\n                    print(\n                        "🔁 AUTOMATIC AVIATION GATE FEEDBACK:",\n                        gate_reject_reason,\n                    )\n\n                print_budget_status()\n'''

    if "[AUTOMATIC AVIATION GATE FEEDBACK]" in text:
        print("✅ automatic aviation Gate feedback already propagated")
        return

    count = text.count(marker)
    if count != 1:
        raise RuntimeError(
            f"automatic aviation Gate feedback marker count mismatch: {count}"
        )

    MAIN_PATH.write_text(text.replace(marker, replacement, 1), encoding="utf-8")
    print("✅ automatic aviation Gate feedback propagation applied")


def _apply_final_script_scene_recovery_if_ready():
    if not SCRIPT_PATH.exists():
        return
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    if "SCRIPT_OPENING_LOCK_V1" not in source:
        print("⏭️ Scene-local Script recovery deferred until final production state")
        return
    runpy.run_path("ci_script_scene_local_recovery_hotfix.py", run_name="__main__")


def _patch_script_engine_router():
    text = MAIN_PATH.read_text(encoding="utf-8")
    legacy_import = '''from content.script_generator import (\n    generate_script,\n)\n'''
    router_import = '''from content.script_generator_router import (\n    generate_script,\n)\n'''
    if router_import in text:
        print("✅ Script Engine router already connected")
        return
    count = text.count(legacy_import)
    if count != 1:
        raise RuntimeError(f"Script Generator import marker mismatch: {count}")
    MAIN_PATH.write_text(text.replace(legacy_import, router_import, 1), encoding="utf-8")
    print("✅ Script Engine V2 router connected to production main")


def _reapply_final_run_336911_guard():
    # This compatibility installer runs once early and once after Final Visual
    # composition. Reapply only this PR's narrow guard on the final pass; #275
    # itself stays unchanged and is regression-tested independently.
    main_source = MAIN_PATH.read_text(encoding="utf-8")
    if "FINAL_VISUAL_SEMANTIC_QA_V1" not in main_source:
        print("⏭️ Run 33691170895 guard reapply deferred until Final Visual composition")
        return
    from ci_run_33691170895_term_visual_subject_hotfix import main as patch_run_33691170895
    patch_run_33691170895()


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    text = _ensure_signature_keyword(
        text, "build_execution_context", "fixed_topic_gate_feedback", '""'
    )
    text = _ensure_forwarded_keyword(
        text,
        "build_execution_context",
        "_aviation_specificity_previous_build_context",
        "fixed_topic_gate_feedback",
    )
    text = _ensure_signature_keyword(
        text, "explore_candidates", "fixed_topic_gate_feedback", '""'
    )

    if "# CANDIDATE_SUPPLY_RECOVERY_V1" in text:
        print("✅ Candidate supply wrapper preserves aviation context; direct re-forward skipped")
    else:
        text = _ensure_forwarded_keyword(
            text, "explore_candidates", "build_execution_context", "fixed_topic_gate_feedback"
        )

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    patch_fixed_aviation_scope()
    patch_runtime_call_compat()
    _patch_automatic_gate_feedback()
    _apply_final_script_scene_recovery_if_ready()
    _patch_script_engine_router()
    _reapply_final_run_336911_guard()
    print("✅ Aviation fixed-topic + automatic gate-feedback compatibility applied")


if __name__ == "__main__":
    main()
