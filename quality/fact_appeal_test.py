import os

from quality.judge import (
    run_judge,
    print_judge_result,
)

from quality.review_router import (
    evaluate_fact_appeal,
)

from quality.integration_test import (
    TEST_SCRIPT,
    validate_judge_result,
)


MODEL = os.environ.get(
    "V3_JUDGE_MODEL",
    "gpt-4o-mini",
)


def run_fact_appeal_test():

    print("")
    print("=" * 64)
    print("⚖️ V3.1 REAL FACT APPEAL TEST")
    print("=" * 64)

    if not os.environ.get("OPENAI_KEY"):
        raise RuntimeError(
            "OPENAI_KEY 환경변수가 없습니다."
        )

    fact_results = []

    # ========================================================
    # Fact Judge #1
    # ========================================================

    print("")
    print("▶ FACT JUDGE #1")

    first = run_judge(
        "fact",
        TEST_SCRIPT,
        model=MODEL,
    )

    validate_judge_result(
        "fact",
        first,
    )

    print_judge_result(first)

    fact_results.append(first)

    # ========================================================
    # 독립 Fact Judge #2
    #
    # 정확히 한 번만 추가 호출한다.
    # #2 결과가 어떻든 #3은 호출하지 않는다.
    # ========================================================

    print("")
    print("▶ FACT JUDGE #2 — APPEAL")

    second = run_judge(
        "fact",
        TEST_SCRIPT,
        model=MODEL,
    )

    validate_judge_result(
        "fact",
        second,
    )

    print_judge_result(second)

    fact_results.append(second)

    # ========================================================
    # Appeal 판정
    # ========================================================

    merged_pool = {
        "fact": fact_results,
    }

    appeal = evaluate_fact_appeal(
        merged_pool
    )

    status = appeal.get(
        "status"
    )

    reason = appeal.get(
        "reason",
        "",
    )

    if status not in (
        "HOLD",
        "DISAGREEMENT",
        "CLEARED",
    ):
        raise RuntimeError(
            f"알 수 없는 Appeal 결과: {status}"
        )

    # ========================================================
    # 결과
    # ========================================================

    print("")
    print("=" * 64)
    print("📊 FACT APPEAL RESULT")
    print("=" * 64)

    print(
        "Judge #1 critical:",
        first.get(
            "critical_risk"
        ),
    )

    print(
        "Judge #2 critical:",
        second.get(
            "critical_risk"
        ),
    )

    print(
        "Appeal status:",
        status,
    )

    print(
        "Reason:",
        reason,
    )

    print("")
    print("API Judge calls: 2")
    print("Maximum appeal depth: 1")
    print("Third Judge allowed: NO")

    print("")
    print(
        "✅ REAL FACT APPEAL TEST COMPLETED"
    )

    print("=" * 64)

    return {
        "first": first,
        "second": second,
        "appeal": appeal,
    }


if __name__ == "__main__":
    run_fact_appeal_test()
