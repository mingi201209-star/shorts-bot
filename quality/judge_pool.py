# quality/judge_pool.py

from quality.judge import (
    run_judge,
    print_judge_result,
)


# ============================================================
# Judge Pool V3
# ============================================================
#
# 목적:
#   - 전문 Judge들을 독립적으로 실행
#   - 불확실한 영역은 추가 심사
#   - 한 번의 AI 판단에 과도하게 의존하지 않음
#
# 아직 하지 않는 것:
#   - 최종 PASS / FAIL
#   - 단순 평균
#   - 자동 Rewrite
#
# 최종 합의는 consensus.py가 담당한다.
#
# ============================================================


DEFAULT_JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
]


# ============================================================
# Pool 설정
# ============================================================

MIN_CONFIDENCE = 0.72

# 한 전문 영역을 최대 몇 번까지
# 독립적으로 재평가할지.
MAX_REVIEWS_PER_TYPE = 3

# critical_risk가 나오면
# 최소 이 횟수까지 독립 검토.
MIN_CRITICAL_REVIEWS = 2


# ============================================================
# Judge 결과가 추가 검토를 필요로 하는지
# ============================================================

def needs_extra_review(
    result,
):

    if not isinstance(
        result,
        dict,
    ):
        return True

    confidence = float(
        result.get(
            "confidence",
            0.0,
        )
    )

    critical_risk = bool(
        result.get(
            "critical_risk",
            False,
        )
    )

    score = float(
        result.get(
            "score",
            0.0,
        )
    )

    # --------------------------------------------------------
    # 낮은 확신도
    # --------------------------------------------------------

    if confidence < MIN_CONFIDENCE:
        return True

    # --------------------------------------------------------
    # 치명적 위험
    # --------------------------------------------------------

    if critical_risk:
        return True

    # --------------------------------------------------------
    # 경계 구간 점수
    #
    # 너무 높거나 낮은 점수보다
    # 5~7점대가 보통 판단이 애매함.
    # --------------------------------------------------------

    if 5.0 <= score <= 7.0:
        return True

    return False


# ============================================================
# 같은 전문 영역 내부 결과 충돌
# ============================================================

def has_internal_disagreement(
    results,
    threshold=2.5,
):

    if len(results) < 2:
        return False

    scores = [
        float(
            item.get(
                "score",
                0.0,
            )
        )
        for item in results
    ]

    difference = (
        max(scores)
        - min(scores)
    )

    return (
        difference >= threshold
    )


# ============================================================
# 전문 영역 하나 평가
# ============================================================

def run_specialist_pool(
    judge_type,
    script_data,
    *,
    model="gpt-4o-mini",
):

    results = []

    # --------------------------------------------------------
    # 1차 독립 평가
    # --------------------------------------------------------

    first = run_judge(
        judge_type,
        script_data,
        model=model,
    )

    results.append(
        first
    )

    print_judge_result(
        first
    )

    # --------------------------------------------------------
    # 필요 없으면 여기서 종료
    # --------------------------------------------------------

    if not needs_extra_review(
        first
    ):

        return results

    # --------------------------------------------------------
    # 2차 독립 평가
    # --------------------------------------------------------

    second = run_judge(
        judge_type,
        script_data,
        model=model,
    )

    results.append(
        second
    )

    print_judge_result(
        second
    )

    # --------------------------------------------------------
    # 2차까지만으로 충분한 경우
    # --------------------------------------------------------

    critical_exists = any(
        item.get(
            "critical_risk",
            False,
        )
        for item in results
    )

    disagreement = (
        has_internal_disagreement(
            results
        )
    )

    if (
        not disagreement
        and not critical_exists
    ):

        return results

    # --------------------------------------------------------
    # 3차 독립 평가
    #
    # 최대 3회.
    # 계속 호출하는 무한 Judge 루프 금지.
    # --------------------------------------------------------

    if (
        len(results)
        < MAX_REVIEWS_PER_TYPE
    ):

        third = run_judge(
            judge_type,
            script_data,
            model=model,
        )

        results.append(
            third
        )

        print_judge_result(
            third
        )

    return results


# ============================================================
# 전체 Judge Pool
# ============================================================

def run_judge_pool(
    script_data,
    *,
    judge_types=None,
    model="gpt-4o-mini",
):

    if judge_types is None:

        judge_types = (
            DEFAULT_JUDGE_TYPES
        )

    pool_results = {}

    print("")
    print("=" * 56)
    print("⚖️ V3 JUDGE POOL START")
    print("=" * 56)

    for judge_type in judge_types:

        print("")
        print(
            f"🔍 전문 심사 시작: "
            f"{judge_type.upper()}"
        )

        results = (
            run_specialist_pool(
                judge_type,
                script_data,
                model=model,
            )
        )

        pool_results[
            judge_type
        ] = results

    print("")
    print("=" * 56)
    print("✅ V3 JUDGE POOL COMPLETE")
    print("=" * 56)

    return pool_results


# ============================================================
# Judge 호출 수 통계
# ============================================================

def get_pool_statistics(
    pool_results,
):

    total_reviews = 0

    by_type = {}

    for judge_type, results in (
        pool_results.items()
    ):

        count = len(
            results
        )

        by_type[
            judge_type
        ] = count

        total_reviews += count

    return {
        "total_reviews": total_reviews,
        "by_type": by_type,
    }


# ============================================================
# 콘솔 통계
# ============================================================

def print_pool_statistics(
    pool_results,
):

    stats = get_pool_statistics(
        pool_results
    )

    print("")
    print("=" * 50)
    print("📊 JUDGE POOL STATISTICS")
    print("=" * 50)

    print(
        "총 Judge 호출:",
        stats["total_reviews"],
    )

    for judge_type, count in (
        stats["by_type"].items()
    ):

        print(
            f" - {judge_type}: "
            f"{count}회"
        )

    print("=" * 50)
