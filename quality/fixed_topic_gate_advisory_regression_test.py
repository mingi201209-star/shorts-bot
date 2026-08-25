from ci_fixed_topic_gate_advisory_hotfix import (
    MARKER,
    apply_fixed_topic_gate_advisory,
)


FIXTURE = '''                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")

                    print(
                        "➡️ Candidate Explorer 재탐색"
                    )

                    continue

                raise RuntimeError(
                    "Candidate Gate를 통과하는 "
                    "Winner를 확보하지 못했습니다. "
                    "마지막 이유: "
                    f"{winner_gate.get('reason', '')}"
                )
'''


def main():
    patched = apply_fixed_topic_gate_advisory(FIXTURE)

    assert "if forced_topic:" in patched
    assert "if topic_attempt == 1:" in patched
    assert "지정 주제 Gate 피드백으로 1회 재탐색" in patched
    assert MARKER in patched
    assert "FACT 및 downstream 품질 Gate는 유지" in patched

    # Automatic selection keeps the existing hard-fail path.
    assert "else:" in patched
    assert "Candidate Explorer 재탐색" in patched
    assert "raise RuntimeError(" in patched
    assert "Candidate Gate를 통과하는 " in patched

    # Installer must remain idempotent when workflow/tests re-run it.
    assert apply_fixed_topic_gate_advisory(patched) == patched

    print("FIXED TOPIC GATE ADVISORY REGRESSION: PASS")


if __name__ == "__main__":
    main()
