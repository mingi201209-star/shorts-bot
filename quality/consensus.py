# quality/consensus.py

from statistics import mean


# ============================================================
# Consensus Engine V3.1
# ============================================================
#
# 책임:
#   - Judge Pool 결과 통합
#   - confidence 반영
#   - Judge 간 불일치 감지
#   - critical risk 처리
#   - 장기 Judge reliability 반영 준비
#   - PASS / REWRITE / REVIEW 결정
#
# 중요:
#   Judge reliability는 표본 수에 따라 제한적으로 반영한다.
#
# 표본:
#   < 10    → 1.00 고정
#   10~29   → 0.90 ~ 1.10
#   30~99   → 0.80 ~ 1.20
#   100+    → 0.50 ~ 1.25
#
# ============================================================


PASS_SCORE = 7.5
REWRITE_SCORE = 5.5

MIN_CONFIDENCE = 0.65

DISAGREEMENT_WARNING = 2.0
DISAGREEMENT_CRITICAL = 3.5


# ============================================================
# 전문 영역 기본 중요도
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
# 안전한 숫자 변환
# ============================================================

def safe_float(
    value,
    default=0.0,
):

    try:
        return float(value)

    except Exception:
        return default


def safe_int(
    value,
    default=0,
):

    try:
        return int(value)

    except Exception:
        return default


# ============================================================
# Reliability 안전 제한
# ============================================================

def clamp(
    value,
    minimum,
    maximum,
):

    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


# ============================================================
# 표본에 따른 실제 적용 Reliability
# ============================================================

def get_effective_reliability(
    judge_type,
    reliability_report=None,
):

    # --------------------------------------------------------
    # Reliability 시스템을 사용하지 않는 경우
    # --------------------------------------------------------

    if not isinstance(
        reliability_report,
        dict,
    ):

        return 1.0

    judge_data = reliability_report.get(
        judge_type
    )

    if not isinstance(
        judge_data,
        dict,
    ):

        return 1.0

    raw_reliability = safe_float(
        judge_data.get(
            "reliability",
            1.0,
        ),
        1.0,
    )

    statistics = judge_data.get(
        "statistics",
        {},
    )

    if not isinstance(
        statistics,
        dict,
    ):

        statistics = {}

    samples = safe_int(
        statistics.get(
            "evaluated",
            0,
        ),
        0,
    )

    # --------------------------------------------------------
    # 표본 10개 미만
    #
    # Judge 권한 변경 금지.
    # --------------------------------------------------------

    if samples < 10:

        return 1.0

    # --------------------------------------------------------
    # 10 ~ 29
    #
    # 최대 ±10%
    # --------------------------------------------------------

    if samples < 30:

        return round(
            clamp(
                raw_reliability,
                0.90,
                1.10,
            ),
            3,
        )

    # --------------------------------------------------------
    # 30 ~ 99
    #
    # 최대 ±20%
    # --------------------------------------------------------

    if samples < 100:

        return round(
            clamp(
                raw_reliability,
                0.80,
                1.20,
            ),
            3,
        )

    # --------------------------------------------------------
    # 100+
    #
    # 장기 데이터가 충분할 경우
    # 전체 허용 범위 사용.
    # --------------------------------------------------------

    return round(
        clamp(
            raw_reliability,
            0.50,
            1.25,
        ),
        3,
    )


# ============================================================
# 한 전문영역 요약
# ============================================================

def summarize_domain(
    judge_type,
    results,
    reliability_report=None,
):

    reliability = (
        get_effective_reliability(
            judge_type,
            reliability_report,
        )
    )

    if not results:

        return {
            "judge_type": judge_type,
            "score": 0.0,
            "adjusted_score": 0.0,
            "confidence": 0.0,
            "disagreement": 10.0,
            "critical_risk": True,
            "review_count": 0,
            "issues": [
                "Judge 결과 없음"
            ],
            "reliability": reliability,
        }

    scores = []
    confidences = []
    issues = []

    critical_risk = False

    for result in results:

        if not isinstance(
            result,
            dict,
        ):
            continue

        score = safe_float(
            result.get(
                "score",
                0.0,
            )
        )

        confidence = safe_float(
            result.get(
                "confidence",
                0.0,
            )
        )

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

        result_issues = result.get(
            "issues",
            [],
        )

        if isinstance(
            result_issues,
            list,
        ):

            for issue in result_issues:

                if issue:

                    issues.append(
                        str(issue)
                    )

    # 비정상 Judge 결과만 들어온 경우
    if not scores:

        return {
            "judge_type": judge_type,
            "score": 0.0,
            "adjusted_score": 0.0,
            "confidence": 0.0,
            "disagreement": 10.0,
            "critical_risk": True,
            "review_count": 0,
            "issues": [
                "유효한 Judge 결과 없음"
            ],
            "reliability": reliability,
        }

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

    # --------------------------------------------------------
    # Confidence 보정
    # --------------------------------------------------------
    #
    # 낮은 confidence 판단은
    # 점수 영향력을 줄인다.
    #
    # 최소 0.5를 유지하는 이유:
    # confidence 하나만으로 Judge 판단을
    # 완전히 제거하지 않기 위해서.
    # --------------------------------------------------------

    confidence_factor = max(
        0.5,
        min(
            confidence_avg,
            1.0,
        ),
    )

    adjusted_score = (
        score_avg
        * confidence_factor
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

        "critical_risk":
            critical_risk,

        "review_count": len(
            scores
        ),

        "issues": list(
            dict.fromkeys(
                issues
            )
        ),

        # Judge의 장기 신뢰도
        "reliability": reliability,
    }


# ============================================================
# 모든 전문영역 요약
# ============================================================

def summarize_pool(
    pool_results,
    reliability_report=None,
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
            reliability_report,
        )

    return summaries


# ============================================================
# 최종 Judge Weight
# ============================================================

def calculate_domain_weight(
    judge_type,
    summary,
):

    base_weight = DOMAIN_WEIGHTS.get(
        judge_type,
        1.0,
    )

    reliability = safe_float(
        summary.get(
            "reliability",
            1.0,
        ),
        1.0,
    )

    return (
        base_weight
        * reliability
    )


# ============================================================
# 전체 Weighted Score
# ============================================================

def calculate_weighted_score(
    summaries,
):

    weighted_total = 0.0
    total_weight = 0.0

    for judge_type, summary in (
        summaries.items()
    ):

        weight = calculate_domain_weight(
            judge_type,
            summary,
        )

        score = safe_float(
            summary.get(
                "adjusted_score",
                0.0,
            )
        )

        weighted_total += (
            score * weight
        )

        total_weight += weight

    if total_weight <= 0:

        return 0.0

    return round(
        weighted_total
        / total_weight,
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

        disagreement = safe_float(
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
                "judge_type":
                    judge_type,

                "disagreement":
                    disagreement,
            })

        elif (
            disagreement
            >= DISAGREEMENT_WARNING
        ):

            warnings.append({
                "judge_type":
                    judge_type,

                "disagreement":
                    disagreement,
            })

    return {
        "warnings": warnings,
        "critical": critical,
    }


# ============================================================
# 낮은 Confidence 탐지
# ============================================================

def detect_low_confidence(
    summaries,
):

    return [
        {
            "judge_type":
                judge_type,

            "confidence":
                summary.get(
                    "confidence",
                    0.0,
                ),
        }

        for judge_type, summary
        in summaries.items()

        if safe_float(
            summary.get(
                "confidence",
                0.0,
            )
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
            "judge_type":
                judge_type,

            "hard_block": (
                judge_type
                in CRITICAL_DOMAINS
            ),

            "issues":
                summary.get(
                    "issues",
                    [],
                ),
        })

    return risks


# ============================================================
# Judge Reliability 경고
# ============================================================

def detect_low_reliability(
    summaries,
):

    warnings = []

    for judge_type, summary in (
        summaries.items()
    ):

        reliability = safe_float(
            summary.get(
                "reliability",
                1.0,
            ),
            1.0,
        )

        if reliability < 0.80:

            warnings.append({
                "judge_type":
                    judge_type,

                "reliability":
                    reliability,
            })

    return warnings


# ============================================================
# 최종 Consensus
# ============================================================

def build_consensus(
    pool_results,
    reliability_report=None,
):

    summaries = summarize_pool(
        pool_results,
        reliability_report,
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

    low_reliability = (
        detect_low_reliability(
            summaries
        )
    )

    reasons = []

    # ========================================================
    # 1. FACT Critical Risk
    # ========================================================

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

    # ========================================================
    # 2. Judge 간 심한 충돌
    # ========================================================

    elif disagreements[
        "critical"
    ]:

        decision = "REVIEW"

        reasons.append(
            "전문 Judge 간 심한 의견 충돌이 있습니다."
        )

    # ========================================================
    # 3. 복수 영역 Low Confidence
    # ========================================================

    elif len(
        low_confidence
    ) >= 2:

        decision = "REVIEW"

        reasons.append(
            "복수 전문 영역에서 Judge 확신도가 낮습니다."
        )

    # ========================================================
    # 4. 점수 기반
    # ========================================================

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

    # ========================================================
    # 경고 기록
    # ========================================================

    if disagreements[
        "warnings"
    ]:

        reasons.append(
            "일부 전문 영역에서 Judge 의견 차이가 있습니다."
        )

    if low_reliability:

        reasons.append(
            "장기 신뢰도가 낮은 Judge가 포함되어 있습니다."
        )

    return {
        "decision":
            decision,

        "weighted_score":
            weighted_score,

        "domain_summaries":
            summaries,

        "disagreements":
            disagreements,

        "low_confidence":
            low_confidence,

        "critical_risks":
            critical_risks,

        "low_reliability":
            low_reliability,

        "reasons":
            reasons,
    }


# ============================================================
# 로그
# ============================================================

def print_consensus(
    consensus,
):

    print("")
    print("=" * 64)
    print(
        "🧠 V3.1 CONSENSUS"
    )
    print("=" * 64)

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
            f"score "
            f"{summary.get('score', 0):.2f} "
            f"| confidence "
            f"{summary.get('confidence', 0):.2f} "
            f"| reliability "
            f"{summary.get('reliability', 1):.2f} "
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

    low_reliability = (
        consensus.get(
            "low_reliability",
            [],
        )
    )

    if low_reliability:

        print("")
        print(
            "⚠️ Low reliability Judges:"
        )

        for item in low_reliability:

            print(
                f" - "
                f"{item['judge_type']}: "
                f"{item['reliability']:.2f}"
            )

    print("=" * 64)
