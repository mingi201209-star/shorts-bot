# quality/consensus.py

from statistics import mean


# ============================================================
# Consensus Engine V3
# ============================================================
#
# 책임:
#   - Judge Pool 결과 통합
#   - 불일치 감지
#   - confidence 반영
#   - critical risk 처리
#   - PASS / REWRITE / REVIEW 결정
#
# 절대 하지 않는 것:
#   - 대본 직접 수정
#   - Judge 재호출
#   - Validator 규칙 변경
#
# ============================================================


PASS_SCORE = 7.5
REWRITE_SCORE = 5.5

MIN_CONFIDENCE = 0.65

DISAGREEMENT_WARNING = 2.0
DISAGREEMENT_CRITICAL = 3.5


# ============================================================
# 전문 영역 중요도
# ============================================================

DOMAIN_WEIGHTS = {
    "hook": 1.2,
    "novelty": 1.1,
    "fact": 1.4,
    "visual": 1.0,
}


# ============================================================
# Critical Risk 영향
# ============================================================

CRITICAL_DOMAINS = {
    "fact",
}


# ============================================================
# 한 전문영역 요약
# ============================================================

def summarize_domain(
    judge_type,
    results,
):

    if not results:

        return {
            "judge_type": judge_type,
            "score": 0.0,
            "confidence": 0.0,
            "disagreement": 10.0,
            "critical_risk": True,
            "review_count": 0,
            "issues": [
                "Judge 결과 없음"
            ],
        }

    scores = []
    confidences = []
    issues = []

    critical_risk = False

    for result in results:

        try:
            score = float(
                result.get(
                    "score",
                    0.0,
                )
            )
        except Exception:
            score = 0.0

        try:
            confidence = float(
                result.get(
                    "confidence",
                    0.0,
                )
            )
        except Exception:
            confidence = 0.0

        scores.append(
            score
        )

        confidences.append(
            confidence
        )

        if result.get(
            "critical_risk",
            False,
        ):
            critical_risk = True

        for issue in result.get(
            "issues",
            [],
        ):
            if issue:
                issues.append(
                    str(issue)
                )

    score_avg = mean(
        scores
    )

    confidence_avg = mean(
        confidences
    )

    disagreement = (
        max(scores)
        - min(scores)
        if len(scores) > 1
        else 0.0
    )

    # 낮은 confidence의 판단은
    # 점수 영향력을 줄임
    adjusted_score = (
        score_avg
        * max(
            0.5,
            confidence_avg,
        )
    )

    return {
        "judge_type": judge_type,
        "score": round(
            score_avg,
            3,
        ),
        "adjusted_score": round(
            adjusted_score,
            3,
        ),
        "confidence": round(
            confidence_avg,
            3,
        ),
        "disagreement": round(
            disagreement,
            3,
        ),
        "critical_risk": critical_risk,
        "review_count": len(
            results
        ),
        "issues": list(
            dict.fromkeys(
                issues
            )
        ),
    }


# ============================================================
# 모든 전문영역 요약
# ============================================================

def summarize_pool(
    pool_results,
):

    summaries = {}

    for judge_type, results in (
        pool_results.items()
    ):

        summaries[
            judge_type
        ] = summarize_domain(
            judge_type,
            results,
        )

    return summaries


# ============================================================
# 전체 weighted score
# ============================================================

def calculate_weighted_score(
    summaries,
):

    weighted_total = 0.0
    total_weight = 0.0

    for judge_type, summary in (
        summaries.items()
    ):

        weight = DOMAIN_WEIGHTS.get(
            judge_type,
            1.0,
        )

        score = summary.get(
            "adjusted_score",
            0.0,
        )

        weighted_total += (
            score * weight
        )

        total_weight += weight

    if total_weight <= 0:
        return 0.0

    return round(
        weighted_total / total_weight,
        3,
    )


# ============================================================
# 불일치 검사
# ============================================================

def detect_disagreements(
    summaries,
):

    warnings = []
    critical = []

    for judge_type, summary in (
        summaries.items()
    ):

        disagreement = float(
            summary.get(
                "disagreement",
                0.0,
            )
        )

        if (
            disagreement
            >= DISAGREEMENT_CRITICAL
        ):

            critical.append({
                "judge_type": judge_type,
                "disagreement": disagreement,
            })

        elif (
            disagreement
            >= DISAGREEMENT_WARNING
        ):

            warnings.append({
                "judge_type": judge_type,
                "disagreement": disagreement,
            })

    return {
        "warnings": warnings,
        "critical": critical,
    }


# ============================================================
# 낮은 confidence 탐지
# ============================================================

def detect_low_confidence(
    summaries,
):

    return [
        {
            "judge_type": judge_type,
            "confidence": summary.get(
                "confidence",
                0.0,
            ),
        }
        for judge_type, summary
        in summaries.items()
        if summary.get(
            "confidence",
            0.0,
        ) < MIN_CONFIDENCE
    ]


# ============================================================
# Critical Risk 탐지
# ============================================================

def detect_critical_risks(
    summaries,
):

    risks = []

    for judge_type, summary in (
        summaries.items()
    ):

        if not summary.get(
            "critical_risk",
            False,
        ):
            continue

        risks.append({
            "judge_type": judge_type,
            "hard_block": (
                judge_type
                in CRITICAL_DOMAINS
            ),
            "issues": summary.get(
                "issues",
                [],
            ),
        })

    return risks


# ============================================================
# 최종 Consensus
# ============================================================

def build_consensus(
    pool_results,
):

    summaries = summarize_pool(
        pool_results
    )

    weighted_score = (
        calculate_weighted_score(
            summaries
        )
    )

    disagreements = (
        detect_disagreements(
            summaries
        )
    )

    low_confidence = (
        detect_low_confidence(
            summaries
        )
    )

    critical_risks = (
        detect_critical_risks(
            summaries
        )
    )

    reasons = []

    # --------------------------------------------------------
    # FACT critical risk는 자동 PASS 금지
    # --------------------------------------------------------

    hard_block = any(
        item.get(
            "hard_block",
            False,
        )
        for item in critical_risks
    )

    if hard_block:

        decision = "REVIEW"

        reasons.append(
            "사실성 영역에 critical risk가 있습니다."
        )

    # --------------------------------------------------------
    # Judge 간 심한 충돌
    # --------------------------------------------------------

    elif disagreements[
        "critical"
    ]:

        decision = "REVIEW"

        reasons.append(
            "전문 Judge 간 심한 의견 충돌이 있습니다."
        )

    # --------------------------------------------------------
    # confidence 부족
    # --------------------------------------------------------

    elif len(
        low_confidence
    ) >= 2:

        decision = "REVIEW"

        reasons.append(
            "복수 전문 영역에서 Judge 확신도가 낮습니다."
        )

    # --------------------------------------------------------
    # 점수 기반
    # --------------------------------------------------------

    elif (
        weighted_score
        >= PASS_SCORE
    ):

        decision = "PASS"

        reasons.append(
            "종합 품질 점수가 PASS 기준을 충족했습니다."
        )

    elif (
        weighted_score
        >= REWRITE_SCORE
    ):

        decision = "REWRITE"

        reasons.append(
            "핵심 구조는 유지 가능하지만 일부 수정이 필요합니다."
        )

    else:

        decision = "REWRITE"

        reasons.append(
            "종합 품질 점수가 낮아 재작성 필요성이 큽니다."
        )

    # --------------------------------------------------------
    # 경고성 disagreement는 PASS라도 기록
    # --------------------------------------------------------

    if disagreements[
        "warnings"
    ]:

        reasons.append(
            "일부 전문 영역에서 Judge 의견 차이가 있습니다."
        )

    return {
        "decision": decision,
        "weighted_score": weighted_score,
        "domain_summaries": summaries,
        "disagreements": disagreements,
        "low_confidence": low_confidence,
        "critical_risks": critical_risks,
        "reasons": reasons,
    }


# ============================================================
# 로그
# ============================================================

def print_consensus(
    consensus,
):

    print("")
    print("=" * 58)
    print(
        "🧠 V3 CONSENSUS"
    )
    print("=" * 58)

    print(
        "결정:",
        consensus.get(
            "decision",
            "UNKNOWN",
        )
    )

    print(
        "종합 점수:",
        consensus.get(
            "weighted_score",
            0.0,
        )
    )

    print("")
    print(
        "전문 영역:"
    )

    for judge_type, summary in (
        consensus.get(
            "domain_summaries",
            {}
        ).items()
    ):

        print(
            f" - {judge_type}: "
            f"{summary.get('score', 0):.2f} "
            f"| confidence "
            f"{summary.get('confidence', 0):.2f} "
            f"| disagreement "
            f"{summary.get('disagreement', 0):.2f}"
        )

    reasons = consensus.get(
        "reasons",
        [],
    )

    if reasons:

        print("")
        print(
            "판단 이유:"
        )

        for reason in reasons:

            print(
                f" - {reason}"
            )

    risks = consensus.get(
        "critical_risks",
        [],
    )

    if risks:

        print("")
        print(
            "🚨 Critical risks:"
        )

        for risk in risks:

            print(
                f" - {risk['judge_type']}"
            )

    print("=" * 58)
