# quality/quality_gate.py

from quality.hard_validator import (
    validate_script_hard,
    print_hard_validation_report,
)

from quality.judge_pool import (
    run_judge_pool,
    print_pool_statistics,
)

from quality.consensus import (
    build_consensus,
    print_consensus,
)

from quality.rewrite_engine import (
    rewrite_script,
    print_rewrite_result,
)

from quality.review_router import (
    choose_review_route,
    execute_extra_review,
    merge_review_results,
    print_review_route,
)


# ============================================================
# Quality Gate V3
# ============================================================
#
# 전체 품질 파이프라인 지휘:
#
# Script
#   ↓
# Hard Validator
#   ↓
# Judge Pool
#   ↓
# Consensus
#   ↓
# PASS / REWRITE / REVIEW
#
# REWRITE:
#   선택적 수정 → 처음부터 재검사
#
# REVIEW:
#   추가 Judge 또는 HOLD
#
# 중요:
#   - 무한 Rewrite 금지
#   - 무한 Judge 호출 금지
#   - Hard Validator 실패를 AI 투표로 덮지 않음
#   - HOLD를 억지로 PASS시키지 않음
#
# ============================================================


MAX_REWRITE_ATTEMPTS = 2

MAX_REVIEW_ROUNDS = 1


# ============================================================
# 결과 생성
# ============================================================

def make_result(
    *,
    status,
    script_data,
    hard_report=None,
    pool_results=None,
    consensus=None,
    rewrite_count=0,
    review_count=0,
    reason="",
):

    return {
        "status": status,
        "script_data": script_data,
        "hard_report": hard_report,
        "pool_results": pool_results,
        "consensus": consensus,
        "rewrite_count": rewrite_count,
        "review_count": review_count,
        "reason": reason,
    }


# ============================================================
# Hard Validation
# ============================================================

def run_hard_gate(
    script_data,
):

    report = validate_script_hard(
        script_data
    )

    print_hard_validation_report(
        report
    )

    return report


# ============================================================
# AI Quality Evaluation
# ============================================================

def run_ai_gate(
    script_data,
    *,
    model,
):

    pool_results = run_judge_pool(
        script_data,
        model=model,
    )

    print_pool_statistics(
        pool_results
    )

    consensus = build_consensus(
        pool_results
    )

    print_consensus(
        consensus
    )

    return (
        pool_results,
        consensus,
    )


# ============================================================
# 메인 Quality Gate
# ============================================================

def run_quality_gate(
    script_data,
    *,
    model="gpt-4o-mini",
    max_rewrites=MAX_REWRITE_ATTEMPTS,
):

    if not isinstance(
        script_data,
        dict,
    ):

        raise TypeError(
            "script_data는 dict여야 합니다."
        )

    current_script = script_data

    rewrite_count = 0
    review_count = 0

    print("")
    print("=" * 62)
    print("🛡️ SHORTS V3 QUALITY GATE START")
    print("=" * 62)

    while True:

        # ====================================================
        # 1. HARD VALIDATOR
        # ====================================================

        hard_report = run_hard_gate(
            current_script
        )

        if not hard_report.get(
            "passed",
            False,
        ):

            return make_result(
                status="HOLD",
                script_data=current_script,
                hard_report=hard_report,
                rewrite_count=rewrite_count,
                review_count=review_count,
                reason=(
                    "Hard Validator 실패. "
                    "AI Judge로 우회할 수 없습니다."
                ),
            )

        # ====================================================
        # 2. JUDGE POOL
        # ====================================================

        pool_results, consensus = (
            run_ai_gate(
                current_script,
                model=model,
            )
        )

        decision = consensus.get(
            "decision",
            "REVIEW",
        )

        # ====================================================
        # 3. PASS
        # ====================================================

        if decision == "PASS":

            print("")
            print(
                "🏆 QUALITY GATE PASSED"
            )

            return make_result(
                status="PASS",
                script_data=current_script,
                hard_report=hard_report,
                pool_results=pool_results,
                consensus=consensus,
                rewrite_count=rewrite_count,
                review_count=review_count,
                reason=(
                    "Hard Validator와 "
                    "AI Consensus를 모두 통과했습니다."
                ),
            )

        # ====================================================
        # 4. REWRITE
        # ====================================================

        if decision == "REWRITE":

            if (
                rewrite_count
                >= max_rewrites
            ):

                return make_result(
                    status="HOLD",
                    script_data=current_script,
                    hard_report=hard_report,
                    pool_results=pool_results,
                    consensus=consensus,
                    rewrite_count=rewrite_count,
                    review_count=review_count,
                    reason=(
                        "최대 Rewrite 횟수를 "
                        "초과했습니다."
                    ),
                )

            rewrite_result = (
                rewrite_script(
                    current_script,
                    consensus,
                    model=model,
                )
            )

            print_rewrite_result(
                rewrite_result
            )

            if not rewrite_result.get(
                "changed",
                False,
            ):

                return make_result(
                    status="HOLD",
                    script_data=current_script,
                    hard_report=hard_report,
                    pool_results=pool_results,
                    consensus=consensus,
                    rewrite_count=rewrite_count,
                    review_count=review_count,
                    reason=(
                        "REWRITE 결정이 났지만 "
                        "수정 가능한 영역을 "
                        "찾지 못했습니다."
                    ),
                )

            current_script = (
                rewrite_result[
                    "script_data"
                ]
            )

            rewrite_count += 1

            # 수정된 대본은 반드시
            # Hard Validator부터 다시 시작.
            continue

        # ====================================================
        # 5. REVIEW
        # ====================================================

        if decision == "REVIEW":

            route = choose_review_route(
                consensus
            )

            print_review_route(
                route
            )

            route_type = route.get(
                "route"
            )

            # ------------------------------------------------
            # HOLD
            # ------------------------------------------------

            if route_type == "HOLD":

                return make_result(
                    status="HOLD",
                    script_data=current_script,
                    hard_report=hard_report,
                    pool_results=pool_results,
                    consensus=consensus,
                    rewrite_count=rewrite_count,
                    review_count=review_count,
                    reason=route.get(
                        "reason",
                        "추가 검토 필요",
                    ),
                )

            # ------------------------------------------------
            # 추가 Judge
            # ------------------------------------------------

            if route_type == "EXTRA_JUDGE":

                if (
                    review_count
                    >= MAX_REVIEW_ROUNDS
                ):

                    return make_result(
                        status="HOLD",
                        script_data=current_script,
                        hard_report=hard_report,
                        pool_results=pool_results,
                        consensus=consensus,
                        rewrite_count=rewrite_count,
                        review_count=review_count,
                        reason=(
                            "추가 Review 최대 횟수를 "
                            "초과했습니다."
                        ),
                    )

                extra_results = (
                    execute_extra_review(
                        current_script,
                        route,
                        model=model,
                    )
                )

                merged_pool = (
                    merge_review_results(
                        pool_results,
                        extra_results,
                    )
                )

                review_count += 1

                # 추가 심사 결과로
                # Consensus 재계산
                new_consensus = (
                    build_consensus(
                        merged_pool
                    )
                )

                print_consensus(
                    new_consensus
                )

                new_decision = (
                    new_consensus.get(
                        "decision",
                        "REVIEW",
                    )
                )

                # --------------------------------------------
                # 추가 심사 후 PASS
                # --------------------------------------------

                if new_decision == "PASS":

                    return make_result(
                        status="PASS",
                        script_data=current_script,
                        hard_report=hard_report,
                        pool_results=merged_pool,
                        consensus=new_consensus,
                        rewrite_count=rewrite_count,
                        review_count=review_count,
                        reason=(
                            "추가 독립 심사 후 "
                            "Consensus PASS."
                        ),
                    )

                # --------------------------------------------
                # 추가 심사 후 REWRITE
                # --------------------------------------------

                if (
                    new_decision
                    == "REWRITE"
                ):

                    if (
                        rewrite_count
                        >= max_rewrites
                    ):

                        return make_result(
                            status="HOLD",
                            script_data=current_script,
                            hard_report=hard_report,
                            pool_results=merged_pool,
                            consensus=new_consensus,
                            rewrite_count=rewrite_count,
                            review_count=review_count,
                            reason=(
                                "추가 심사 후 "
                                "Rewrite가 필요하지만 "
                                "최대 수정 횟수에 "
                                "도달했습니다."
                            ),
                        )

                    rewrite_result = (
                        rewrite_script(
                            current_script,
                            new_consensus,
                            model=model,
                        )
                    )

                    print_rewrite_result(
                        rewrite_result
                    )

                    if not rewrite_result.get(
                        "changed",
                        False,
                    ):

                        return make_result(
                            status="HOLD",
                            script_data=current_script,
                            hard_report=hard_report,
                            pool_results=merged_pool,
                            consensus=new_consensus,
                            rewrite_count=rewrite_count,
                            review_count=review_count,
                            reason=(
                                "추가 심사 후 수정이 "
                                "필요하지만 Rewrite "
                                "대상을 찾지 못했습니다."
                            ),
                        )

                    current_script = (
                        rewrite_result[
                            "script_data"
                        ]
                    )

                    rewrite_count += 1

                    # 다시 처음부터 검사
                    continue

                # --------------------------------------------
                # 그래도 REVIEW
                # --------------------------------------------

                return make_result(
                    status="HOLD",
                    script_data=current_script,
                    hard_report=hard_report,
                    pool_results=merged_pool,
                    consensus=new_consensus,
                    rewrite_count=rewrite_count,
                    review_count=review_count,
                    reason=(
                        "추가 독립 심사 후에도 "
                        "판단 불확실성이 "
                        "해소되지 않았습니다."
                    ),
                )

        # ====================================================
        # 알 수 없는 상태
        # ====================================================

        return make_result(
            status="HOLD",
            script_data=current_script,
            hard_report=hard_report,
            pool_results=pool_results,
            consensus=consensus,
            rewrite_count=rewrite_count,
            review_count=review_count,
            reason=(
                f"알 수 없는 Consensus 결정: "
                f"{decision}"
            ),
        )


# ============================================================
# 최종 결과 출력
# ============================================================

def print_quality_gate_result(
    result,
):

    print("")
    print("=" * 62)
    print("🏁 V3 QUALITY GATE RESULT")
    print("=" * 62)

    print(
        "상태:",
        result.get(
            "status",
            "UNKNOWN",
        )
    )

    print(
        "Rewrite:",
        result.get(
            "rewrite_count",
            0,
        )
    )

    print(
        "Review:",
        result.get(
            "review_count",
            0,
        )
    )

    print(
        "이유:",
        result.get(
            "reason",
            "",
        )
    )

    print("=" * 62)
