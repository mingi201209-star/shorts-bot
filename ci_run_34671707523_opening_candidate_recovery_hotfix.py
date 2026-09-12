from pathlib import Path


PATH = Path("main.py")
MARKER = "# RUN_34671707523_OPENING_CANDIDATE_RECOVERY_V1"


def apply_opening_candidate_recovery(text: str) -> str:
    """Reject fixed-topic locked openings before spending Writer retries.

    Run 34671707523 proved that the final opening human contract can reject a
    Candidate Hook/Core Question pair that the earlier Candidate-level guard
    allowed. SCRIPT_OPENING_LOCK_V1 restores those two Candidate-owned beats
    after every Writer call, so three Writer retries cannot repair that class
    of failure. Reuse the existing bounded fixed-topic Candidate loop instead:
    preflight the locked pair with the exact final validator and feed its reason
    into the already-existing fixed_topic_gate_feedback channel.

    No threshold, retry ceiling, model/API call allowance, scene count, or cost
    budget is changed.
    """
    if MARKER in text:
        return text

    # Isolated/early fixtures can run this installer before fixed-topic support
    # is composed. Defer safely; production composition installs it after
    # ci_topic_input_hotfix.py and the Run 34663907508 final opening contract.
    prerequisites = (
        'fixed_topic_gate_feedback = ""',
        "if forced_topic:",
        "# Winner Script",
        "generate_script(",
    )
    if not all(marker in text for marker in prerequisites):
        return text

    # Anchor only to the stable Winner Script section header. Later production
    # hotfixes are allowed to wrap or reshape generate_script(...) itself, so
    # coupling this recovery installer to one exact call layout would make a
    # partial regression fixture fail even though the semantic insertion point
    # is still unambiguous.
    anchor = '''            # =================================================
            # Winner Script
            # =================================================
'''

    insertion = '''

            # RUN_34671707523_OPENING_CANDIDATE_RECOVERY_V1
            # The final Script V2 opening contract is stricter than the older
            # Candidate-level overlap heuristic. Because SCRIPT_OPENING_LOCK_V1
            # restores Candidate-owned Scene 1/2 after every Writer call, a
            # violating fixed-topic pair cannot be repaired by Writer retries.
            # Reject it here, before Writer, and reuse the existing bounded
            # Candidate attempt + fixed_topic_gate_feedback path instead.
            if forced_topic:
                micro_narrative = (
                    winner.get("micro_narrative")
                    if isinstance(winner, dict)
                    else None
                ) or {}
                locked_hook = str(
                    micro_narrative.get("hook", "")
                ).strip()
                locked_question = str(
                    micro_narrative.get("core_question", "")
                    or winner.get("core_question", "")
                ).strip()

                if locked_hook and locked_question:
                    from content.script_engine_v2_validation import (
                        opening_human_contract_violation_reason,
                    )

                    opening_reason = (
                        opening_human_contract_violation_reason(
                            locked_hook,
                            locked_question,
                        )
                    )

                    if opening_reason:
                        fixed_topic_gate_feedback = (
                            "Final opening human contract rejected the locked "
                            "Hook/Core Question pair: "
                            f"{opening_reason}. "
                            "Keep the fixed topic unchanged, but make Scene 1 "
                            "advance information with an already-grounded "
                            "observation, constraint, result, contrast, or "
                            "causal clue before Scene 2 asks why. Do not invent "
                            "new facts and do not restate the same proposition."
                        )

                        print("")
                        print("=" * 64)
                        print(
                            "♻️ FIXED-TOPIC OPENING CANDIDATE RECOVERY"
                        )
                        print("=" * 64)
                        print("이유:", opening_reason)
                        print(
                            "🧭 fixed-topic final-opening feedback captured "
                            "for next Candidate attempt"
                        )
                        print_budget_status()

                        if topic_attempt < total_topic_attempts:
                            continue

                        raise RuntimeError(
                            "Fixed-topic Candidate opening exhausted bounded "
                            "attempts under the final opening human contract: "
                            f"{opening_reason}"
                        )
'''

    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            "Run 34671707523 opening Candidate recovery section count mismatch: "
            f"{count}"
        )
    return text.replace(anchor, anchor + insertion, 1)


def _install_hook_floor_feedback() -> None:
    # Run 34672661458 exposed the next bounded-recovery gap: after the single
    # allowed Hook rewrite still misses the floor, #333 returns
    # REGENERATE_TOPIC with a concrete Hook Judge reason, but main.py did not
    # carry that reason into the next fixed-topic Candidate Explorer attempt.
    from ci_run_34672661458_hook_floor_feedback_hotfix import (
        main as _hook_floor_feedback_main,
    )

    _hook_floor_feedback_main()


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    patched = apply_opening_candidate_recovery(text)
    if patched == text:
        if MARKER in text:
            print("Run 34671707523 opening Candidate recovery already installed")
        else:
            print(
                "⏭️ Run 34671707523 opening Candidate recovery deferred until "
                "fixed-topic final composition"
            )
    else:
        PATH.write_text(patched, encoding="utf-8")
        print(
            "✅ Run 34671707523 opening Candidate recovery installed; "
            "Writer/Candidate/API/cost limits unchanged"
        )

    _install_hook_floor_feedback()


if __name__ == "__main__":
    main()
