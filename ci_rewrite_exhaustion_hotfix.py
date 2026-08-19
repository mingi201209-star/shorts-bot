from pathlib import Path


path = Path("main.py")
text = path.read_text(encoding="utf-8")

# Allow the existing fully validated Runner-up path to be reused for
# rewrite-exhausted Winners. No Candidate Gate / Quality Gate threshold
# is changed; the Runner-up still starts from a fresh script and review.
runner_guard_marker = '''    if (
        failure_type
        != "FACT_CRITICAL"
    ):

        return None
'''
runner_guard_replacement = '''    if failure_type not in (
        "FACT_CRITICAL",
        "REWRITE_EXHAUSTED",
    ):

        return None
'''

# Mark only the exact Quality HOLD produced by run_quality_process when
# the selective Rewrite allowance is exhausted. This marker is captured
# before any Runner-up result replaces quality_result.
quality_marker = '''            # =================================================
            # FACT_CRITICAL → Runner-up
            # =================================================

            fact_critical_recovery = (
                quality_result.get(
                    "failure_type"
                )
                == "FACT_CRITICAL"
            )

            if fact_critical_recovery:
'''
quality_replacement = '''            # =================================================
            # FACT_CRITICAL → Runner-up
            # =================================================

            fact_critical_recovery = (
                quality_result.get(
                    "failure_type"
                )
                == "FACT_CRITICAL"
            )

            rewrite_exhaustion_recovery = (
                quality_result.get(
                    "status"
                )
                == "HOLD"
                and quality_result.get(
                    "reason"
                )
                == "Rewrite 최대 횟수 초과"
            )

            if fact_critical_recovery:
'''

# Reuse the existing safe Runner-up path before deciding whether the
# exhausted Winner should be discarded and Candidate Explorer resumed.
status_marker = '''            status = (
                quality_result.get(
                    "status"
                )
            )
'''
status_replacement = '''            if rewrite_exhaustion_recovery:

                if (
                    current_topic
                    not in rejected_topics
                ):

                    rejected_topics.append(
                        current_topic
                    )

                rewrite_fallback_input = dict(
                    quality_result
                )

                rewrite_fallback_input[
                    "failure_type"
                ] = "REWRITE_EXHAUSTED"

                fallback_result = (
                    try_runner_up_fallback(
                        topic_info,
                        runner_up,
                        rewrite_fallback_input,
                    )
                )

                if (
                    fallback_result
                    is not None
                ):

                    quality_result = (
                        fallback_result
                    )

            status = (
                quality_result.get(
                    "status"
                )
            )
'''

# ci_fact_critical_hotfix.py already protects its own recovery from the
# ordinary REGENERATE_TOPIC branch. Add the same protection for rewrite
# exhaustion so a failed Runner-up cannot skip the API-budget check.
regenerate_marker = '''            if (
                status
                == "REGENERATE_TOPIC"
                and not fact_critical_recovery
            ):
'''
regenerate_replacement = '''            if (
                status
                == "REGENERATE_TOPIC"
                and not fact_critical_recovery
                and not rewrite_exhaustion_recovery
            ):
'''

# Insert bounded candidate regeneration immediately before the existing
# FACT_CRITICAL recovery. The surrounding for-loop owns the attempt budget,
# therefore `continue` consumes exactly one Candidate attempt.
fact_recovery_marker = '''            # =================================================
            # FACT_CRITICAL Candidate Regeneration
            # =================================================
'''
rewrite_recovery_block = '''            # =================================================
            # Rewrite Exhaustion Candidate Regeneration
            # =================================================
            #
            # Rewrite 한도를 모두 사용한 후보는 절대 PASS로 승격하지
            # 않는다. 안전한 Runner-up도 통과하지 못했다면 Candidate
            # attempt와 API budget이 모두 남은 경우에만 다음 Candidate
            # Explorer iteration으로 이동한다.
            # =================================================

            if rewrite_exhaustion_recovery:

                from quality.budget_guard import (
                    get_budget_status,
                )

                budget_status = (
                    get_budget_status()
                )

                budget_remaining = (
                    budget_status["calls"]
                    < budget_status["max_calls"]
                    and budget_status["cost_usd"]
                    < budget_status["max_cost_usd"]
                )

                print("")
                print("=" * 64)

                print(
                    "♻️ REWRITE EXHAUSTION CANDIDATE REGENERATION"
                )

                print("=" * 64)

                print(
                    "폐기 소재:",
                    current_topic,
                )

                print(
                    "이유:",
                    "Rewrite 최대 횟수 초과",
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                    and budget_remaining
                ):

                    print("")

                    print(
                        "➡️ Candidate Explorer 재탐색"
                    )

                    continue

                if not budget_remaining:

                    print("")

                    print(
                        "⛔ API budget 부족으로 "
                        "Rewrite exhaustion 후보 재탐색을 종료합니다."
                    )

''' + fact_recovery_marker

already_applied = (
    runner_guard_replacement in text
    and quality_replacement in text
    and status_replacement in text
    and regenerate_replacement in text
    and rewrite_recovery_block in text
)

if already_applied:
    print("Rewrite exhaustion candidate recovery hotfix already applied")
else:
    markers = (
        ("Runner-up failure-type guard", runner_guard_marker),
        ("Quality recovery marker", quality_marker),
        ("Quality status marker", status_marker),
        ("Candidate regeneration marker", regenerate_marker),
        ("FACT recovery marker", fact_recovery_marker),
    )

    for name, marker in markers:
        count = text.count(marker)
        if count != 1:
            raise RuntimeError(
                f"main.py {name} count mismatch: {count}"
            )

    text = text.replace(
        runner_guard_marker,
        runner_guard_replacement,
        1,
    )
    text = text.replace(
        quality_marker,
        quality_replacement,
        1,
    )
    text = text.replace(
        status_marker,
        status_replacement,
        1,
    )
    text = text.replace(
        regenerate_marker,
        regenerate_replacement,
        1,
    )
    text = text.replace(
        fact_recovery_marker,
        rewrite_recovery_block,
        1,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("✅ Rewrite exhaustion candidate recovery hotfix applied")
