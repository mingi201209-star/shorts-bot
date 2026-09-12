from pathlib import Path


PATH = Path("main.py")
MARKER = "# RUN_34676516725_FIXED_TOPIC_HOOK_BODY_REUSE_V1"
HOOK_REASON_PREFIX = (
    "Fixed-topic Hook가 bounded rewrite 후에도 기존 품질 floor 미달"
)


def apply_fixed_topic_hook_body_reuse(text: str) -> str:
    """Avoid a second full Writer call for Hook-only fixed-topic recovery.

    Run 34676516725 proved that a fixed-topic script can already have strong
    FACT/Visual results while its Hook alone misses the existing floor. The
    current recovery then asks Candidate Explorer for a better opening, but a
    later accepted Candidate spends another full GPT-5.6 Writer call for the
    same topic/body and can cross the unchanged production cost cap.

    This patch caches the already-produced fixed-topic script only when the
    existing bounded Hook rewrite exhausts. On a later validated Candidate, it
    projects only that Candidate's normalized Hook into Scene 1, preserves
    Scene 2+ exactly, validates Scene 1 -> preserved Scene 2 with the existing
    final opening-human contract, then lets the normal Judge Committee rerun.

    No Hook/FACT/Visual threshold, retry ceiling, Candidate-attempt ceiling,
    model route, API allowance, scene count, or cost cap is changed.
    """
    if MARKER in text:
        return text

    prerequisites = (
        'fixed_topic_gate_feedback = ""',
        "# RUN_34672661458_HOOK_FLOOR_FEEDBACK_V1",
        "# RUN_34671707523_OPENING_CANDIDATE_RECOVERY_V1",
        "# Winner Script",
    )
    if not all(item in text for item in prerequisites):
        return text

    state_anchor = '''        fixed_topic_gate_feedback = ""

        final_script = None
'''
    state_replacement = '''        fixed_topic_gate_feedback = ""

        # RUN_34676516725_FIXED_TOPIC_HOOK_BODY_REUSE_V1
        fixed_topic_hook_recovery_script = None
        fixed_topic_last_writer_script = None

        final_script = None
'''

    writer_anchor = '''            script_data = (
                generate_script(
                    topic_info,
                    winner,
                )
            )
'''
    writer_replacement = '''            if (
                forced_topic
                and fixed_topic_hook_recovery_script is not None
            ):
                from copy import deepcopy as _hook_recovery_deepcopy
                from content.script_engine_v2 import build_narrative_plan
                from content.script_engine_v2_validation import (
                    opening_human_contract_violation_reason,
                )

                recovery_script = _hook_recovery_deepcopy(
                    fixed_topic_hook_recovery_script
                )
                recovery_scenes = recovery_script.get("scenes")
                recovery_plan = build_narrative_plan(winner)
                recovery_contracts = recovery_plan.get("contracts") or []

                recovery_hook = ""
                if recovery_contracts:
                    recovery_hook = str(
                        recovery_contracts[0].get("locked_text", "")
                    ).strip()

                preserved_question = ""
                if (
                    isinstance(recovery_scenes, list)
                    and len(recovery_scenes) >= 2
                    and isinstance(recovery_scenes[0], dict)
                    and isinstance(recovery_scenes[1], dict)
                ):
                    preserved_question = str(
                        recovery_scenes[1].get("text", "")
                    ).strip()

                recovery_reason = ""
                if recovery_hook and preserved_question:
                    recovery_reason = (
                        opening_human_contract_violation_reason(
                            recovery_hook,
                            preserved_question,
                        )
                        or ""
                    )
                else:
                    recovery_reason = (
                        "cached script or normalized Candidate Hook is missing"
                    )

                if recovery_reason:
                    fixed_topic_gate_feedback = (
                        "Hook-only body reuse preflight rejected the new "
                        "Candidate Hook against the preserved Scene 2: "
                        f"{recovery_reason}. Keep the fixed topic unchanged. "
                        "Produce a stronger grounded Scene 1 that advances "
                        "information without restating the preserved question."
                    )
                    print("")
                    print(
                        "♻️ FIXED-TOPIC HOOK BODY REUSE PREFLIGHT REJECT:"
                    )
                    print("   ", recovery_reason)
                    print_budget_status()

                    if topic_attempt < total_topic_attempts:
                        continue

                    raise RuntimeError(
                        "Fixed-topic Hook-only body reuse exhausted bounded "
                        "Candidate attempts: "
                        f"{recovery_reason}"
                    )

                recovery_scenes[0]["text"] = recovery_hook
                script_data = recovery_script
                print(
                    "♻️ fixed-topic Hook-only recovery reused validated "
                    "Scene 2+ body; full Writer call skipped"
                )
            else:
                script_data = (
                    generate_script(
                        topic_info,
                        winner,
                    )
                )
'''

    quality_anchor = '''            # =================================================
            # Quality
            # =================================================

            quality_result = (
                run_quality_process(
                    script_data
                )
            )
'''
    quality_replacement = '''            # =================================================
            # Quality
            # =================================================

            if forced_topic:
                from copy import deepcopy as _hook_recovery_deepcopy
                fixed_topic_last_writer_script = _hook_recovery_deepcopy(
                    script_data
                )

            quality_result = (
                run_quality_process(
                    script_data
                )
            )
'''

    feedback_anchor = '''                    if hook_floor_reason.startswith(
                        "Fixed-topic Hook가 bounded rewrite 후에도 "
                        "기존 품질 floor 미달"
                    ):
                        fixed_topic_gate_feedback = (
'''
    feedback_replacement = '''                    if hook_floor_reason.startswith(
                        "Fixed-topic Hook가 bounded rewrite 후에도 "
                        "기존 품질 floor 미달"
                    ):
                        if fixed_topic_last_writer_script is not None:
                            from copy import deepcopy as _hook_recovery_deepcopy
                            fixed_topic_hook_recovery_script = (
                                _hook_recovery_deepcopy(
                                    fixed_topic_last_writer_script
                                )
                            )
                            print(
                                "🧠 fixed-topic Hook-only recovery cached "
                                "the existing Script body"
                            )

                        fixed_topic_gate_feedback = (
'''

    for anchor, replacement, label in (
        (state_anchor, state_replacement, "state"),
        (writer_anchor, writer_replacement, "Writer call"),
        (quality_anchor, quality_replacement, "quality cache"),
        (feedback_anchor, feedback_replacement, "Hook exhaustion cache"),
    ):
        count = text.count(anchor)
        if count != 1:
            diagnostic = ""
            if label == "Writer call":
                marker_index = text.find("# Winner Script")
                if marker_index >= 0:
                    diagnostic = text[marker_index:marker_index + 1800]
            raise RuntimeError(
                "Run 34676516725 Hook body reuse "
                f"{label} anchor count mismatch: {count}"
                + (f"\nFINAL_COMPOSED_WRITER_EXCERPT:\n{diagnostic}" if diagnostic else "")
            )
        text = text.replace(anchor, replacement, 1)

    return text


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    patched = apply_fixed_topic_hook_body_reuse(text)
    if patched == text:
        if MARKER in text:
            print("Run 34676516725 fixed-topic Hook body reuse already installed")
        else:
            print(
                "⏭️ Run 34676516725 fixed-topic Hook body reuse deferred until "
                "final fixed-topic composition"
            )
        return

    PATH.write_text(patched, encoding="utf-8")
    print(
        "✅ Run 34676516725 fixed-topic Hook body reuse installed; "
        "second full Writer avoided without changing floors/budgets/retries"
    )


if __name__ == "__main__":
    main()
