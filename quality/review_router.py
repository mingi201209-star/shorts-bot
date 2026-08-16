# quality/review_router.py

from quality.judge import (
    run_judge,
    print_judge_result,
)


# ============================================================
# Review Router V3.1
# ============================================================
#
# 책임:
#   - Consensus REVIEW 원인 분류
#   - 불확실 영역 재심
#   - Fact Critical 독립 재검증
#   - 무한 재심 차단
#
# 중요:
#   Fact Critical을 한 Judge의 판단만으로
#   바로 확정하지 않는다.
#
#   하지만 추가 Fact Judge도 Critical을 내면
#   HOLD한다.
#
# ============================================================


MAX_EXTRA_REVIEW_DOMAINS = 2


# ============================================================
# 재검토 영역 찾기
# ============================================================

def find_review_domains(
    consensus,
):

    domains = []

    disagreements = consensus.get(
        "disagreements",
        {},
    )

    for item in disagreements.get(
        "critical",
        [],
    ):

        judge_type = item.get(
            "judge_type"
        )

        if judge_type:
            domains.append(
                judge_type
            )

    for item in consensus.get(
        "low_confidence",
        [],
    ):

        judge_type = item.get(
            "judge_type"
        )

        if judge_type:
            domains.append(
                judge_type
            )

    for item in consensus.get(
        "critical_risks",
        [],
    ):

        judge_type = item.get(
            "judge_type"
        )

        if judge_type:
            domains.append(
                judge_type
            )

    return list(
        dict.fromkeys(
            domains
        )
    )


# ============================================================
# Fact Critical 확인
# ============================================================

def has_fact_critical(
    consensus,
):

    for risk in consensus.get(
        "critical_risks",
        [],
    ):

        if (
            risk.get(
                "judge_type"
            )
            == "fact"
        ):

            return True

    return False


# ============================================================
# Route 결정
# ============================================================

def choose_review_route(
    consensus,
):

    if consensus.get(
        "decision"
    ) != "REVIEW":

        return {
            "route": "NONE",
            "domains": [],
            "reason":
                "REVIEW 상태가 아닙니다.",
        }

    domains = find_review_domains(
        consensus
    )

    # --------------------------------------------------------
    # Fact Critical
    #
    # 바로 HOLD하지 않고
    # 독립 Fact Judge 1회 재심.
    # --------------------------------------------------------

    if has_fact_critical(
        consensus
    ):

        return {
            "route":
                "FACT_EXTRA_JUDGE",

            "domains": [
                "fact"
            ],

            "reason": (
                "Fact Judge가 critical risk를 "
                "탐지했습니다. 독립 Fact Judge "
                "1회 재심을 실시합니다."
            ),
        }

    # --------------------------------------------------------
    # 너무 많은 영역이 동시에 불확실
    # --------------------------------------------------------

    if len(
        domains
    ) > MAX_EXTRA_REVIEW_DOMAINS:

        return {
            "route": "HOLD",
            "domains": domains,
            "reason": (
                "여러 전문 영역에서 동시에 "
                "판단 불확실성이 발생했습니다."
            ),
        }

    # --------------------------------------------------------
    # 일반 추가심사
    # --------------------------------------------------------

    if domains:

        return {
            "route":
                "EXTRA_JUDGE",

            "domains":
                domains,

            "reason": (
                "불확실한 전문 영역만 "
                "추가 독립 심사합니다."
            ),
        }

    return {
        "route": "HOLD",
        "domains": [],
        "reason": (
            "REVIEW 원인을 명확히 "
            "분류하지 못했습니다."
        ),
    }


# ============================================================
# Fact 재심 정확히 1회
# ============================================================

def execute_fact_extra_review(
    script_data,
    *,
    model="gpt-4o-mini",
):

    print("")
    print(
        "🧪 FACT 독립 재심 1회"
    )

    result = run_judge(
        "fact",
        script_data,
        model=model,
    )

    print_judge_result(
        result
    )

    return {
        "fact": [
            result
        ]
    }


# ============================================================
# 일반 추가 Review
#
# 현재는 각 영역 정확히 1회만 호출.
# 비용 및 무한 호출 방지.
# ============================================================

def execute_extra_review(
    script_data,
    route,
    *,
    model="gpt-4o-mini",
):

    route_type = route.get(
        "route"
    )

    if route_type == (
        "FACT_EXTRA_JUDGE"
    ):

        return (
            execute_fact_extra_review(
                script_data,
                model=model,
            )
        )

    if route_type != (
        "EXTRA_JUDGE"
    ):

        return {}

    results = {}

    for judge_type in route.get(
        "domains",
        [],
    ):

        result = run_judge(
            judge_type,
            script_data,
            model=model,
        )

        print_judge_result(
            result
        )

        results[
            judge_type
        ] = [
            result
        ]

    return results


# ============================================================
# 기존 + 추가 결과 병합
# ============================================================

def merge_review_results(
    original_pool,
    extra_results,
):

    merged = {}

    for judge_type, results in (
        original_pool.items()
    ):

        merged[
            judge_type
        ] = list(
            results
        )

    for judge_type, results in (
        extra_results.items()
    ):

        merged.setdefault(
            judge_type,
            []
        )

        merged[
            judge_type
        ].extend(
            results
        )

    return merged


# ============================================================
# Fact 재심 결과 판정
# ============================================================

def evaluate_fact_appeal(
    merged_pool,
):

    fact_results = (
        merged_pool.get(
            "fact",
            []
        )
    )

    if len(
        fact_results
    ) < 2:

        return {
            "status": "INSUFFICIENT",
            "reason":
                "Fact 재심 결과가 부족합니다.",
        }

    critical_count = sum(
        1
        for result in fact_results
        if result.get(
            "critical_risk",
            False,
        )
    )

    # --------------------------------------------------------
    # 둘 이상 Critical
    # --------------------------------------------------------

    if critical_count >= 2:

        return {
            "status": "HOLD",
            "reason": (
                "복수의 독립 Fact Judge가 "
                "critical risk를 확인했습니다."
            ),
        }

    # --------------------------------------------------------
    # 의견 충돌
    # --------------------------------------------------------

    if critical_count == 1:

        return {
            "status":
                "DISAGREEMENT",

            "reason": (
                "Fact Judge 간 critical risk "
                "판단이 충돌했습니다."
            ),
        }

    # --------------------------------------------------------
    # 둘 다 Critical 아님
    # --------------------------------------------------------

    return {
        "status": "CLEARED",
        "reason": (
            "독립 Fact 재심에서 "
            "critical risk가 재확인되지 않았습니다."
        ),
    }


# ============================================================
# 로그
# ============================================================

def print_review_route(
    route,
):

    print("")
    print("=" * 58)
    print(
        "🧭 V3.1 REVIEW ROUTER"
    )
    print("=" * 58)

    print(
        "경로:",
        route.get(
            "route",
            "UNKNOWN",
        )
    )

    domains = route.get(
        "domains",
        [],
    )

    if domains:

        print(
            "대상:",
            ", ".join(
                domains
            )
        )

    print(
        "이유:",
        route.get(
            "reason",
            "",
        )
    )

    print("=" * 58)
