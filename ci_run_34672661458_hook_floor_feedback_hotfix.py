from pathlib import Path


PATH = Path("main.py")
MARKER = "# RUN_34672661458_HOOK_FLOOR_FEEDBACK_V1"
HOOK_EXHAUSTION_MARKER = "# FIXED_TOPIC_HOOK_EXHAUSTION_RECOVERY_V1"
HOOK_REASON_PREFIX = (
    "Fixed-topic Hook가 bounded rewrite 후에도 기존 품질 floor 미달"
)


def apply_hook_floor_feedback(text: str) -> str:
    """Carry an exhausted fixed-topic Hook reason into the next Candidate.

    Run 34672661458 showed that the existing bounded Hook recovery correctly
    returned REGENERATE_TOPIC after one allowed Rewrite, but main.py discarded
    its concrete Hook reason before the next fixed-topic Candidate Explorer
    call. The Explorer therefore retried without knowing that the opening was
    still a generic description.

    Run 34673458379 then proved the first installer guard was too brittle: it
    looked for the full runtime reason as one contiguous source string, while
    #333 composes that reason from adjacent Python string literals. Use #333's
    stable semantic marker instead of depending on source formatting.

    This patch only copies that already-produced reason into the existing
    fixed_topic_gate_feedback channel. It adds no Candidate attempt, Rewrite,
    model/API call, threshold change, scene change, or budget change.
    """
    if MARKER in text:
        return text

    prerequisites = (
        'fixed_topic_gate_feedback = ""',
        'status\n                == "REGENERATE_TOPIC"',
        HOOK_EXHAUSTION_MARKER,
    )
    if not all(marker in text for marker in prerequisites):
        return text

    anchor = '''                print(
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

    replacement = '''                print(
                    "이유:",
                    quality_result.get(
                        "reason",
                        "",
                    ),
                )

                # RUN_34672661458_HOOK_FLOOR_FEEDBACK_V1
                # Only the existing fixed-topic Hook-floor exhaustion result
                # is eligible. Other REGENERATE_TOPIC reasons keep their
                # current behavior and non-fixed-topic flow is untouched.
                if forced_topic:
                    hook_floor_reason = str(
                        quality_result.get(
                            "reason",
                            "",
                        )
                    ).strip()
                    if hook_floor_reason.startswith(
                        "Fixed-topic Hook가 bounded rewrite 후에도 "
                        "기존 품질 floor 미달"
                    ):
                        fixed_topic_gate_feedback = (
                            hook_floor_reason
                            + ". 직전 Hook Judge 실패를 직접 해결하라. "
                            "주제는 그대로 유지하고, 첫 장면을 일반 설명이나 "
                            "메타 예고가 아니라 기존 grounding 안의 구체 관찰, "
                            "결과, 제약, 대조 또는 인과 단서로 시작하라. "
                            "Scene 2는 같은 내용을 다시 묻지 말고 다음 정보 "
                            "beat로 전진시켜라. 사실을 새로 발명하지 마라."
                        )
                        print(
                            "🧭 fixed-topic Hook-floor feedback captured "
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
            "Run 34672661458 Hook-floor feedback marker count mismatch: "
            f"{count}"
        )

    return text.replace(anchor, replacement, 1)


def _install_hook_body_reuse() -> None:
    from ci_run_34676516725_fixed_topic_hook_body_reuse_hotfix import (
        main as _hook_body_reuse_main,
    )

    _hook_body_reuse_main()


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    patched = apply_hook_floor_feedback(text)
    if patched == text:
        if MARKER in text:
            print("Run 34672661458 Hook-floor feedback already installed")
        else:
            print(
                "⏭️ Run 34672661458 Hook-floor feedback deferred until "
                "fixed-topic Hook exhaustion composition"
            )
    else:
        PATH.write_text(patched, encoding="utf-8")
        print(
            "✅ Run 34672661458 Hook-floor feedback propagation installed; "
            "quality floors/retries/API/cost limits unchanged"
        )

    _install_hook_body_reuse()


if __name__ == "__main__":
    main()
