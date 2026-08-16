# quality/review_router.py

from quality.judge_pool import (
    run_specialist_pool,
)


# ============================================================
# Review Router V3
# ============================================================
#
# 책임:
#   - Consensus가 REVIEW를 냈을 때 재검토 경로 결정
#   - 추가 Judge가 필요한지 판단
#   - 특정 전문 영역만 재심
#   - 사람 확인이 필요한 위험 케이스 분리
#
# 하지 않는 것:
#   - 대본 직접 수정
#   - 최종 PASS 강제
#   - Validator 규칙 변경
#
# ============================================================


MAX_EXTRA_REVIEW_DOMAINS = 2

HUMAN_REVIEW_DOMAINS = {
    "fact",
}


# ============================================================
# 재검토 대상 영역 찾기
# ============================================================

def find_review_domains(
    consensus,
):

    domains = []

    # --------------------------------------------------------
    # 심한 Judge 불일치
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 낮은 confidence
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Critical risk
    # --------------------------------------------------------

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
# 사람 확인이 필요한지
# ============================================================

def needs_human_review(
    consensus,
):

    critical_risks = consensus.get(
        "critical_risks",
        [],
    )

    for risk in critical_risks:

        judge_type = risk.get(
            "judge_type"
        )

        if judge_type in (
            HUMAN_REVIEW_DOMAINS
        ):

            return True

    return False


# ============================================================
# Review Route 결정
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
            "reason": (
                "REVIEW 상태가 아닙니다."
            ),
        }

    domains = find_review_domains(
        consensus
    )

    # --------------------------------------------------------
    # 사실성 Critical Risk
    # --------------------------------------------------------

    if needs_human_review(
        consensus
    ):

        return {
            "route": "HOLD",
            "domains": domains,
            "reason": (
                "사실성 critical risk가 있어 "
                "자동 통과를 금지합니다."
            ),
        }

    # --------------------------------------------------------
    # 너무 많은 영역에서 동시에 불확실
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
    # 특정 영역 추가 Judge
    # --------------------------------------------------------

    if domains:

        return {
            "route": "EXTRA_JUDGE",
            "domains": domains,
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
# 추가 전문 Judge 실행
# ============================================================

def execute_extra_review(
    script_data,
    route,
    *,
    model="gpt-4o-mini",
):

    if route.get(
        "route"
    ) != "EXTRA_JUDGE":

        return {}

    results = {}

    for judge_type in route.get(
        "domains",
        [],
    ):

        extra = run_specialist_pool(
            judge_type,
            script_data,
            model=model,
        )

        results[
            judge_type
        ] = extra

    return results


# ============================================================
# 기존 Pool + 추가 Review 합치기
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
# 로그
# ============================================================

def print_review_route(
    route,
):

    print("")
    print("=" * 55)
    print("🧭 V3 REVIEW ROUTER")
    print("=" * 55)

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

    print("=" * 55)
