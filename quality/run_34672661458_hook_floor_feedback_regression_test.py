import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ci_run_34672661458_hook_floor_feedback_hotfix import (
    HOOK_REASON_PREFIX,
    MARKER,
    apply_hook_floor_feedback,
)


REGEN_ANCHOR = '''                print(
                    "이유:",
                    quality_result.get(
                        "reason",
                        "",
                    ),
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):
'''


def _synthetic_runtime_source():
    return '''def run_case(forced_topic, quality_result, existing_feedback=""):
    fixed_topic_gate_feedback = existing_feedback
    total_topic_attempts = 2

    def print_budget_status():
        return None

    for topic_attempt in range(1, total_topic_attempts + 1):
        status = quality_result.get("status")

        if (
            status
            == "REGENERATE_TOPIC"
        ):

            print("")
            print("=" * 64)
            print("♻️ CANDIDATE REGENERATION")
            print("=" * 64)
            print("폐기 소재:", "fixed")

            print(
                "이유:",
                quality_result.get(
                    "reason",
                    "",
                ),
            )

            print_budget_status()

            if (
                topic_attempt
                < total_topic_attempts
            ):
                return fixed_topic_gate_feedback

    return fixed_topic_gate_feedback

# The installer requires proof that #333 Hook exhaustion recovery is already
# composed. Keep its exact reason prefix present in this executable fixture:
RUN_34641471858_REASON_PREFIX = "Fixed-topic Hook가 bounded rewrite 후에도 기존 품질 floor 미달"
'''


def main():
    source = _synthetic_runtime_source()
    assert 'fixed_topic_gate_feedback = ""' not in source

    # Production has an empty initialization. Add it as a harmless sentinel so
    # the installer prerequisite matches the composed main.py contract while
    # the executable function can still accept pre-existing feedback.
    source = 'fixed_topic_gate_feedback = ""\n' + source
    patched = apply_hook_floor_feedback(source)

    assert MARKER in patched
    assert apply_hook_floor_feedback(patched) == patched
    assert patched.count(MARKER) == 1

    # Guardrails: this patch must not change any quality/retry/cost constants.
    for forbidden in (
        "GOOD_ENOUGH_FLOORS",
        "MAX_REWRITES =",
        "MAX_TOPIC_REGENERATIONS =",
        "V3_MAX_COST_USD",
        "V3_MAX_API_CALLS",
    ):
        assert forbidden not in patched

    namespace = {}
    exec(compile(patched, "<run34672661458-feedback>", "exec"), namespace)
    run_case = namespace["run_case"]

    hook_reason = (
        HOOK_REASON_PREFIX
        + ": 첫 장면이 단순 설명으로 시작함"
    )
    result = run_case(
        True,
        {
            "status": "REGENERATE_TOPIC",
            "reason": hook_reason,
        },
        "older feedback",
    )
    assert hook_reason in result
    assert "첫 장면을 일반 설명이나 메타 예고가 아니라" in result
    assert "사실을 새로 발명하지 마라" in result

    # A different fixed-topic regeneration reason must not overwrite existing
    # feedback. Only #333's exhausted Hook-floor result is eligible.
    result = run_case(
        True,
        {
            "status": "REGENERATE_TOPIC",
            "reason": "FACT_CRITICAL unrelated regeneration",
        },
        "keep this feedback",
    )
    assert result == "keep this feedback"

    # Non-fixed flow remains untouched even with the same reason prefix.
    result = run_case(
        False,
        {
            "status": "REGENERATE_TOPIC",
            "reason": hook_reason,
        },
        "non-fixed feedback",
    )
    assert result == "non-fixed feedback"

    # The feedback is carried through an existing variable only: no model/API
    # call is introduced by the inserted block.
    inserted = patched.split(MARKER, 1)[1].split("print_budget_status()", 1)[0]
    for forbidden_call in (
        "call_llm",
        "generate_script(",
        "explore_candidates(",
        "rewrite",
    ):
        assert forbidden_call not in inserted.lower()

    print("Run 34672661458 Hook-floor feedback regression PASS")


if __name__ == "__main__":
    main()
