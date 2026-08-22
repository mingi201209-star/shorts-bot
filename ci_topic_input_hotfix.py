from pathlib import Path


MAIN_PATH = Path("main.py")
EXPLORER_PATH = Path("content/candidate_explorer.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text

    count = text.count(marker)
    if count != 1:
        raise RuntimeError(
            f"{label} marker count mismatch: {count}"
        )

    return text.replace(marker, replacement, 1)


def patch_main():
    text = MAIN_PATH.read_text(encoding="utf-8")

    environment_marker = '''        validate_environment()

        final_script = None
'''

    environment_replacement = '''        validate_environment()

        forced_topic = os.environ.get(
            "SHORTS_TOPIC",
            "",
        ).strip()

        if forced_topic:
            print(
                "🎯 지정 production 주제:",
                forced_topic,
            )

        fixed_topic_gate_feedback = ""

        final_script = None
'''

    direction_marker = '''            topic_info = (
                choose_topic_direction()
            )
'''

    direction_replacement = '''            if forced_topic:

                topic_info = {
                    "category": "지정 주제",
                    "topic": forced_topic,
                }

            else:

                topic_info = (
                    choose_topic_direction()
                )
'''

    explorer_marker = '''                explore_candidates(
                    topic_info,
                    recent_topics=recent_topics,
                    rejected_topics=rejected_topics,
                )
'''

    explorer_replacement = '''                explore_candidates(
                    topic_info,
                    recent_topics=recent_topics,
                    rejected_topics=(
                        []
                        if forced_topic
                        else rejected_topics
                    ),
                    fixed_topic=(
                        forced_topic
                        or None
                    ),
                    fixed_topic_gate_feedback=(
                        fixed_topic_gate_feedback
                        if forced_topic
                        else ""
                    ),
                )
'''

    runner_marker = '''            runner_up = (
                explorer_result.get(
                    "runner_up"
                )
            )
'''

    runner_replacement = '''            runner_up = (
                None
                if forced_topic
                else explorer_result.get(
                    "runner_up"
                )
            )
'''

    rejected_marker = '''            if (
                current_topic
                in rejected_topics
            ):
'''

    rejected_replacement = '''            if (
                not forced_topic
                and current_topic
                in rejected_topics
            ):
'''

    gate_feedback_marker = '''                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):
'''

    gate_feedback_replacement = '''                if forced_topic:
                    fixed_topic_gate_feedback = str(
                        winner_gate.get(
                            "reason",
                            "",
                        )
                    ).strip()

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):
'''

    topic_guard_marker = '''            if not current_topic:

                raise RuntimeError(
                    "Candidate Explorer Winner에 "
                    "topic이 없습니다."
                )

            print("")
'''

    topic_guard_replacement = '''            if not current_topic:

                raise RuntimeError(
                    "Candidate Explorer Winner에 "
                    "topic이 없습니다."
                )

            if (
                forced_topic
                and current_topic != forced_topic
            ):

                raise RuntimeError(
                    "지정 production 주제와 "
                    "Candidate Explorer Winner topic이 "
                    "일치하지 않습니다."
                )

            print("")
'''

    for marker, replacement, label in (
        (
            environment_marker,
            environment_replacement,
            "main forced topic environment",
        ),
        (
            direction_marker,
            direction_replacement,
            "main topic direction",
        ),
        (
            explorer_marker,
            explorer_replacement,
            "main explorer call",
        ),
        (
            runner_marker,
            runner_replacement,
            "main runner-up",
        ),
        (
            rejected_marker,
            rejected_replacement,
            "main rejected topic guard",
        ),
        (
            topic_guard_marker,
            topic_guard_replacement,
            "main fixed topic guard",
        ),
        (
            gate_feedback_marker,
            gate_feedback_replacement,
            "main fixed topic gate feedback",
        ),
    ):
        text = replace_once(
            text,
            marker,
            replacement,
            label,
        )

    MAIN_PATH.write_text(
        text,
        encoding="utf-8",
    )


def patch_candidate_explorer():
    text = EXPLORER_PATH.read_text(
        encoding="utf-8"
    )

    context_signature_marker = '''def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
):
'''

    context_signature_replacement = '''def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
):
'''

    context_return_marker = '''    return f"""
[EXECUTION CONTEXT]

이번 탐색의 넓은 분야:
{category}
'''

    context_return_replacement = '''    fixed_topic = str(
        fixed_topic or ""
    ).strip()

    if fixed_topic:

        fixed_topic_gate_feedback = str(
            fixed_topic_gate_feedback or ""
        ).strip()

        feedback_section = ""

        if fixed_topic_gate_feedback:
            feedback_section = f"""
============================================================
[PREVIOUS CANDIDATE GATE FEEDBACK]
============================================================

직전 fixed-topic Candidate가 아래 이유로 거절되었다.

{fixed_topic_gate_feedback}

주제 문자열은 그대로 유지하되 같은 Core Question,
Reveal, Mechanism을 반복하지 마라.
거절 이유를 직접 해결하도록 Story Angle을 더 좁히고,
눈에 보이는 구체 관찰, 실제 제약, trade-off,
counterintuitive result 중 근거 있는 요소를 질문과 Reveal에
직접 반영하라.

Candidate Gate와 기존 품질 규칙은 그대로 적용한다.
사실을 발명하거나 약한 Candidate를 억지로 통과시키지 마라.
"""

        return f"""
[EXECUTION CONTEXT - FIXED PRODUCTION TOPIC]

지정 production 주제:
{fixed_topic}


중요:

이번 실행은 지정 주제 모드다.
주제를 다른 대상으로 바꾸거나 넓히지 마라.

winner.topic은 반드시 아래 문자열과
정확히 동일해야 한다.

{fixed_topic}

이 지정 주제 안에서만
가장 강한 Story Angle,
Core Question,
Reveal,
Payoff를 탐색하라.

Runner-up으로 다른 주제를 제안하지 마라.
runner_up은 null로 반환하라.

기존 Candidate Explorer의
Hard Gate, Fact safety, visual proof,
Final Sanity 규칙은 그대로 적용한다.

최근 콘텐츠는 참고하되
지정 주제를 다른 주제로 교체하지 마라.

{feedback_section}

Candidate Explorer 전체 규칙을 수행한 뒤
OUTPUT CONTRACT에 맞는
JSON 객체 하나만 반환하라.
"""

    return f"""
[EXECUTION CONTEXT]

이번 탐색의 넓은 분야:
{category}
'''

    explorer_signature_marker = '''def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    model=MODEL,
):
'''

    explorer_signature_replacement = '''def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
    model=MODEL,
):
'''

    context_call_marker = '''            recent_topics=recent_topics,
            recent_content=recent_content,
            rejected_topics=rejected_topics,
        )
'''

    context_call_replacement = '''            recent_topics=recent_topics,
            recent_content=recent_content,
            rejected_topics=rejected_topics,
            fixed_topic=fixed_topic,
            fixed_topic_gate_feedback=(
                fixed_topic_gate_feedback
            ),
        )
'''

    result_marker = '''    result = (
        validate_explorer_output(
            parsed
        )
    )

    status = result[
        "status"
    ]
'''

    result_replacement = '''    result = (
        validate_explorer_output(
            parsed
        )
    )

    fixed_topic = str(
        fixed_topic or ""
    ).strip()

    if (
        fixed_topic
        and result.get("status") == "SELECTED"
    ):

        winner_topic = str(
            result.get(
                "winner",
                {},
            ).get(
                "topic",
                "",
            )
        ).strip()

        if winner_topic != fixed_topic:

            raise ValueError(
                "Candidate Explorer가 지정 production 주제를 "
                "변경했습니다."
            )

        result["runner_up"] = None

    status = result[
        "status"
    ]
'''

    for marker, replacement, label in (
        (
            context_signature_marker,
            context_signature_replacement,
            "explorer context signature",
        ),
        (
            context_return_marker,
            context_return_replacement,
            "explorer fixed context",
        ),
        (
            explorer_signature_marker,
            explorer_signature_replacement,
            "explorer signature",
        ),
        (
            context_call_marker,
            context_call_replacement,
            "explorer context call",
        ),
        (
            result_marker,
            result_replacement,
            "explorer fixed topic result guard",
        ),
    ):
        text = replace_once(
            text,
            marker,
            replacement,
            label,
        )

    EXPLORER_PATH.write_text(
        text,
        encoding="utf-8",
    )


def main():
    patch_main()
    patch_candidate_explorer()
    print("✅ production topic input hotfix applied")


if __name__ == "__main__":
    main()
