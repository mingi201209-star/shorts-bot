from pathlib import Path


path = Path("main.py")
text = path.read_text(encoding="utf-8")

fact_marker = '''            # =================================================
            # FACT_CRITICAL → Runner-up
            # =================================================

            if (
                quality_result.get(
                    "failure_type"
                )
                == "FACT_CRITICAL"
            ):
'''

fact_replacement = '''            # =================================================
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

generic_hold_marker = '''            # =================================================
            # Generic HOLD
            # =================================================

            raise RuntimeError(
'''

generic_hold_replacement = '''            # =================================================
            # FACT_CRITICAL Candidate Regeneration
            # =================================================
            #
            # 복수의 독립 Fact Judge가 critical risk를 확인한
            # Winner는 절대 PASS시키지 않는다. Runner-up이 없거나
            # Runner-up도 안전하게 통과하지 못했다면, Candidate
            # attempt와 API budget이 남은 경우에만 새 Candidate로
            # 이동한다. for-loop의 다음 iteration을 사용하므로
            # candidate attempt budget은 반드시 1회 소비된다.
            # =================================================

            if fact_critical_recovery:

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
                    "♻️ FACT_CRITICAL CANDIDATE REGENERATION"
                )

                print("=" * 64)

                print(
                    "폐기 소재:",
                    current_topic,
                )

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
                        "FACT_CRITICAL 후보 재탐색을 종료합니다."
                    )

            # =================================================
            # Generic HOLD
            # =================================================

            raise RuntimeError(
'''

if fact_replacement in text and generic_hold_replacement in text:
    print("FACT_CRITICAL candidate recovery hotfix already applied")
else:
    if text.count(fact_marker) != 1:
        raise RuntimeError(
            "main.py FACT_CRITICAL recovery marker count mismatch: "
            f"{text.count(fact_marker)}"
        )

    if text.count(generic_hold_marker) != 1:
        raise RuntimeError(
            "main.py Generic HOLD recovery marker count mismatch: "
            f"{text.count(generic_hold_marker)}"
        )

    text = text.replace(
        fact_marker,
        fact_replacement,
        1,
    )

    text = text.replace(
        generic_hold_marker,
        generic_hold_replacement,
        1,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("✅ FACT_CRITICAL candidate recovery hotfix applied")
