from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_34645762458_candidate_feedback_hotfix import (
    MARKER,
    apply_candidate_feedback,
)


FIXTURE = '''def main():
    forced_topic = "비행기 창문 모서리는 왜 둥글까"
    fixed_topic_gate_feedback = ""
    explorer_status = "REGENERATE"
    reason = "winner.micro_narrative hook이 Core Question과 같은 내용을 반복합니다."

    print("♻️ CANDIDATE EXPLORER REGENERATE")
    print(
        "이유:",
        reason,
    )

    print_budget_status()

    if (
        topic_attempt
        < total_topic_attempts
    ):
        continue
'''


def test_exact_run_shape_captures_feedback() -> None:
    patched = apply_candidate_feedback(FIXTURE)
    assert MARKER in patched
    assert "if forced_topic:" in patched
    assert "fixed_topic_gate_feedback = str(" in patched
    assert "reason or \"\"" in patched
    assert "print_budget_status()" in patched


def test_non_fixed_topic_behavior_remains_guarded() -> None:
    patched = apply_candidate_feedback(FIXTURE)
    injected = patched.split(MARKER, 1)[1]
    assert "if forced_topic:" in injected
    assert "fixed_topic_gate_feedback = str(" in injected


def test_retry_and_quality_contract_are_not_changed() -> None:
    patched = apply_candidate_feedback(FIXTURE)
    assert "MAX_TOPIC_REGENERATIONS" not in patched
    assert "MAX_REWRITES" not in patched
    assert "HOOK" not in patched.split(MARKER, 1)[1]
    assert "threshold" not in patched.lower()


def test_idempotent() -> None:
    once = apply_candidate_feedback(FIXTURE)
    twice = apply_candidate_feedback(once)
    assert once == twice
    assert twice.count(MARKER) == 1


def test_real_main_composition_shape_is_patchable() -> None:
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    # In an uncomposed checkout, ci_topic_input_hotfix.py has not yet installed
    # the fixed-topic channel, so this may intentionally defer.  Compose that
    # one existing hotfix in-process, then require the Run 34645762458 patch.
    from ci_topic_input_hotfix import patch_main
    patch_main()
    composed = (ROOT / "main.py").read_text(encoding="utf-8")
    patched = apply_candidate_feedback(composed)
    assert MARKER in patched
    assert patched.count(MARKER) == 1
    assert patched != main_text


if __name__ == "__main__":
    test_exact_run_shape_captures_feedback()
    test_non_fixed_topic_behavior_remains_guarded()
    test_retry_and_quality_contract_are_not_changed()
    test_idempotent()
    test_real_main_composition_shape_is_patchable()
    print("RUN 34645762458 CANDIDATE FEEDBACK REGRESSION: PASS")
