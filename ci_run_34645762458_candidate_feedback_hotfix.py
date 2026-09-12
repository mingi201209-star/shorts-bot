from pathlib import Path


PATH = Path("main.py")
MARKER = "# RUN_34645762458_FIXED_TOPIC_EXPLORER_FEEDBACK_V1"


def apply_candidate_feedback(text: str) -> str:
    """Feed a fixed-topic Explorer validation failure into the next bounded attempt.

    Run 34645762458 exhausted all seven existing Candidate attempts because the
    same Hook -> Core Question progression validation error was regenerated with
    no feedback from one Explorer attempt to the next.  Keep the validator and
    retry ceilings unchanged; only reuse the already-existing
    fixed_topic_gate_feedback channel for Explorer-level rejection reasons.
    """
    if MARKER in text:
        return text

    # Standalone/early fixtures may not have the fixed-topic production input
    # hotfix composed yet.  There is no fixed-topic feedback channel to wire in
    # that shape, so defer safely until the final production composition pass.
    if (
        "fixed_topic_gate_feedback = \"\"" not in text
        or "if forced_topic:" not in text
        or "CANDIDATE EXPLORER REGENERATE" not in text
    ):
        return text

    anchor = '''                print(
                    "이유:",
                    reason,
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):
'''
    replacement = '''                print(
                    "이유:",
                    reason,
                )

                # RUN_34645762458_FIXED_TOPIC_EXPLORER_FEEDBACK_V1
                # Preserve the existing validator and the existing bounded
                # Candidate-attempt count.  For a pinned topic, make the next
                # Explorer call see exactly why the previous candidate failed
                # instead of blindly repeating the same malformed opening.
                if forced_topic:
                    fixed_topic_gate_feedback = str(
                        reason or ""
                    ).strip()
                    if fixed_topic_gate_feedback:
                        print(
                            "🧭 fixed-topic Explorer feedback captured "
                            "for next Candidate attempt"
                        )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):
'''

    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            "Run 34645762458 Explorer feedback marker count mismatch: "
            f"{count}"
        )
    return text.replace(anchor, replacement, 1)


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    patched = apply_candidate_feedback(text)
    if patched == text:
        if MARKER in text:
            print("Run 34645762458 fixed-topic Explorer feedback already installed")
        else:
            print("⏭️ Run 34645762458 Explorer feedback deferred until fixed-topic composition")
        return
    PATH.write_text(patched, encoding="utf-8")
    print(
        "✅ Run 34645762458 fixed-topic Explorer feedback propagation installed; "
        "validator/retry/API/cost limits unchanged"
    )


if __name__ == "__main__":
    main()
