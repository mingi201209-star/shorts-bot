from pathlib import Path


EXPLORER = Path("content/candidate_explorer.py")
MARKER = "# RUN_34685288234_FIXED_TOPIC_CANDIDATE_OPENING_RECOVERY_V1"


def apply_fixed_topic_candidate_opening_recovery(text: str) -> str:
    """Recover Run #527's fixed-topic Hook/Core Question restatement in-place.

    This does not relax the existing restatement validator.  It gives a
    fixed-topic Winner one deterministic chance to substitute an already-owned
    payoff/reveal sentence as Hook, then runs both the Candidate validator and
    final opening-human contract.  No model/API call or retry is added.
    """
    if MARKER in text:
        return text

    prerequisites = (
        "# SCRIPT_HUMAN_QUALITY_V1",
        "def _hook_restates_question(",
        "def _validate_hook_question_progression(",
        "def validate_candidate(",
    )
    missing = [item for item in prerequisites if item not in text]
    if missing:
        raise RuntimeError(
            "Run 34685288234 fixed-topic opening recovery requires final "
            "Script Human Quality Candidate contract: " + ", ".join(missing)
        )

    anchor = "    _validate_hook_question_progression(result, prefix)\n\n    if runner_up:\n"
    replacement = '''    # RUN_34685288234_FIXED_TOPIC_CANDIDATE_OPENING_RECOVERY_V1
    # Run #527 exhausted all seven fixed-topic Candidate attempts because every
    # generated Winner's Hook merely repeated its Core Question.  Preserve the
    # existing validator/floors and, only for an explicit SHORTS_TOPIC Winner,
    # try candidate-owned payoff/reveal text as a zero-call progression beat.
    fixed_topic_for_opening_recovery = os.environ.get("SHORTS_TOPIC", "").strip()
    if fixed_topic_for_opening_recovery and prefix == "winner":
        from content.fixed_topic_candidate_opening_recovery import (
            recover_fixed_topic_candidate_hook,
        )
        from content.script_engine_v2_validation import (
            opening_human_contract_violation_reason,
        )

        result, opening_recovered, opening_recovery_source = (
            recover_fixed_topic_candidate_hook(
                result,
                fixed_topic=fixed_topic_for_opening_recovery,
                prefix=prefix,
                restates_question=_hook_restates_question,
                opening_violation_reason=opening_human_contract_violation_reason,
            )
        )
        if opening_recovered:
            print(
                "[RUN_34685288234_FIXED_TOPIC_CANDIDATE_OPENING_RECOVERY] "
                f"status=recovered source={opening_recovery_source} api_calls=0"
            )

    # Authority stays exactly where it was: projected or untouched Candidates
    # must still pass the original Hook->Question progression validator.
    _validate_hook_question_progression(result, prefix)

    if runner_up:
'''
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            "Run 34685288234 Candidate validator anchor mismatch: "
            f"{count}"
        )
    return text.replace(anchor, replacement, 1)


def main() -> None:
    text = EXPLORER.read_text(encoding="utf-8")
    patched = apply_fixed_topic_candidate_opening_recovery(text)
    if patched == text:
        print("Run 34685288234 fixed-topic Candidate opening recovery already installed")
        return
    EXPLORER.write_text(patched, encoding="utf-8")
    print(
        "✅ Run 34685288234 fixed-topic Candidate opening recovery installed; "
        "validators/floors/retries/API/cost limits unchanged"
    )


if __name__ == "__main__":
    main()
