# quality/consensus.py

from statistics import mean


# ============================================================
# Consensus Engine V3.2
# ============================================================
#
# 책임:
#   - Judge 결과 통합
#   - 전문 영역별 품질 점수 계산
#   - confidence 별도 감시
#   - Judge 간 불일치 감지
#   - critical risk 처리
#   - Judge reliability 반영
#   - PASS / REWRITE / REVIEW 결정
#
#
# V3.2 핵심 변경:
#
# 1. confidence가 품질 점수를 직접 깎지 않는다.
#
#    이전:
#       score 8
#       confidence 0.7
#       → adjusted_score 5.6
#
#    문제:
#       "콘텐츠 품질"과
#       "Judge가 자신의 판단을 확신하는 정도"를
#       같은 값처럼 처리하게 됨.
#
#
#    현재:
#       score 8
#       confidence 0.7
#
#       품질 점수 = 8
#       confidence = 0.7
#
#       confidence 문제는 별도로 탐지한다.
#
#
# 2. Domain Floor 추가
#
#    전체 평균이 높아도
#    특정 전문 영역이 너무 약하면 PASS 금지.
#
#    예:
#
#       Hook     8
#       Novelty  6
#       Fact     8
#       Visual   8
#
#       평균만 보면 PASS 가능하지만
#       Novelty가 최소 품질 기준 미달.
#
#       → REWRITE
#
#
# 3. 역할 분리
#
#    score
#       = 콘텐츠 품질
#
#    confidence
#       = Judge가 판정에 얼마나 확신하는가
#
#    reliability
#       = 장기 데이터상 Judge를 얼마나 신뢰하는가
#
#    disagreement
#       = 같은 전문 영역의 Judge들이 얼마나 충돌하는가
#
# ============================================================


# ============================================================
# 전체 판정 기준
# ============================================================

PASS_SCORE = 7.5

REWRITE_SCORE = 5.5


# ============================================================
# 전문 영역 최소 품질
#
# 하나라도 이 값 미만이면
# 전체 평균이 높더라도 REWRITE.
# ============================================================

DOMAIN_REWRITE_FLOOR = 6.5


# ============================================================
# Confidence 기준
# ============================================================

MIN_CONFIDENCE = 0.65


# ============================================================
# Judge 불일치 기준
# ============================================================

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
# Critical Risk 영역
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

        return float(
            value
        )

    except Exception:

        return default


def safe_int(
    value,
    default=0,
):

    try:

        return int(
            value
        )

    except Exception:

        return default


# ============================================================
# Clamp
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
# 표본 수 기반 Reliability 적용
# ============================================================
#
# < 10
#     1.00 고정
#
# 10 ~ 29
#     0.90 ~ 1.10
#
# 30 ~ 99
#     0.80 ~ 1.20
#
# 100+
#     0.50 ~ 1.25
#
# ============================================================

def get_effective_reliability(
    judge_type,
    reliability_report=None,
):

    # --------------------------------------------------------
    # Reliability 데이터 없음
    # --------------------------------------------------------

    if not isinstance(
        reliability_report,
        dict,
    ):

        return 1.0

    judge_data = (
        reliability_report.get(
            judge_type
        )
    )

    if not isinstance(
        judge_data,
        dict,
    ):

        return 1.0

    raw_reliability = (
        safe_float(
            judge_data.get(
                "reliability",
                1.0,
            ),
            1.0,
        )
    )

    statistics = (
        judge_data.get(
            "statistics",
            {},
        )
    )

    if not isinstance(
        statistics,
        dict,
    ):

        statistics = {}

    samples = (
        safe_int(
            statistics.get(
                "evaluated",
                0,
            ),
            0,
        )
    )

    # --------------------------------------------------------
    # 표본 10개 미만
    #
    # Judge 권한 변경 금지.
    # --------------------------------------------------------

    if samples < 10:

        return 1.0

    # --------------------------------------------------------
    # 표본 10 ~ 29
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
    # 표본 30 ~ 99
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
    # 표본 100+
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
# 한 전문 영역 요약
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

    # --------------------------------------------------------
    # 결과 없음
    # --------------------------------------------------------

    if not results:

        return {
            "judge_type":
                judge_type,

            "score":
                0.0,

            "adjusted_score":
                0.0,

            "confidence":
                0.0,

            "disagreement":
                10.0,

            "critical_risk":
                True,

            "review_count":
                0,

            "issues": [
                "Judge 결과 없음"
            ],

            "reliability":
                reliability,
        }

    scores = []

    confidences = []

    issues = []

    critical_risk = False

    # --------------------------------------------------------
    # Judge 결과 수집
    # --------------------------------------------------------

    for result in results:

        if not isinstance(
            result,
            dict,
        ):

            continue

        score = (
            safe_float(
                result.get(
                    "score",
                    0.0,
                )
            )
        )

        confidence = (
            safe_float(
                result.get(
                    "confidence",
                    0.0,
                )
            )
        )

        # 안전 범위
        score = clamp(
            score,
            0.0,
            10.0,
        )

        confidence = clamp(
            confidence,
            0.0,
            1.0,
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

        result_issues = (
            result.get(
                "issues",
                [],
            )
        )

        if isinstance(
            result_issues,
            list,
        ):

            for issue in result_issues:

                if issue:

                    issues.append(
                        str(
                            issue
                        )
                    )

    # --------------------------------------------------------
    # 유효 결과 없음
    # --------------------------------------------------------

    if not scores:

        return {
            "judge_type":
                judge_type,

            "score":
                0.0,

            "adjusted_score":
                0.0,

            "confidence":
                0.0,

            "disagreement":
                10.0,

            "critical_risk":
                True,

            "review_count":
                0,

            "issues": [
                "유효한 Judge 결과 없음"
            ],

            "reliability":
                reliability,
        }

    # --------------------------------------------------------
    # 평균
    # --------------------------------------------------------

    score_avg = mean(
        scores
    )

    if confidences:

        confidence_avg = mean(
            confidences
        )

    else:

        confidence_avg = 0.0

    # --------------------------------------------------------
    # 같은 영역 Judge 간 점수 차이
    # --------------------------------------------------------

    disagreement = (
        max(scores)
        - min(scores)

        if len(scores) > 1

        else 0.0
    )

    # ========================================================
    # V3.2 핵심:
    # Confidence는 품질 점수를 깎지 않는다.
    # ========================================================
    #
    # score:
    #   콘텐츠 품질
    #
    # confidence:
    #   Judge의 자기 확신
    #
    # 둘은 별개다.
    #
    # Low Confidence는
    # detect_low_confidence()에서 별도 처리.
    #
    # ========================================================

    adjusted_score = (
        score_avg
    )

    return {
        "judge_type":
            judge_type,

        "score":
            round(
                score_avg,
                3,
            ),

        # 기존 외부 코드 호환을 위해
        # adjusted_score 필드 자체는 유지.
        #
        # V3.2에서는 score와 동일.
        "adjusted_score":
            round(
                adjusted_score,
                3,
            ),

        "confidence":
            round(
                confidence_avg,
                3,
            ),

        "disagreement":
            round(
                disagreement,
                3,
            ),

        "critical_risk":
            critical_risk,

        "review_count":
            len(
                scores
            ),

        "issues":
            list(
                dict.fromkeys(
                    issues
                )
            ),

        "reliability":
            reliability,
    }


# ============================================================
# 전체 전문 영역 요약
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
# 최종 Domain Weight
# ============================================================

def calculate_domain_weight(
    judge_type,
    summary,
):

    base_weight = (
        DOMAIN_WEIGHTS.get(
            judge_type,
            1.0,
        )
    )

    reliability = (
        safe_float(
            summary.get(
                "reliability",
                1.0,
            ),
            1.0,
        )
    )

    return (
        base_weight
        * reliability
    )


# ============================================================
# Weighted Score
# ============================================================

def calculate_weighted_score(
    summaries,
):

    weighted_total = 0.0

    total_weight = 0.0

    for judge_type, summary in (
        summaries.items()
    ):

        weight = (
            calculate_domain_weight(
                judge_type,
                summary,
            )
        )

        score = (
            safe_float(
                summary.get(
                    "adjusted_score",
                    0.0,
                )
            )
        )

        weighted_total += (
            score
            * weight
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
# Judge 불일치 검사
# ============================================================

def detect_disagreements(
    summaries,
):

    warnings = []

    critical = []

    for judge_type, summary in (
        summaries.items()
    ):

        disagreement = (
            safe_float(
                summary.get(
                    "disagreement",
                    0.0,
                )
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
        "warnings":
            warnings,

        "critical":
            critical,
    }


# ============================================================
# Low Confidence 탐지
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
# Low Reliability 탐지
# ============================================================

def detect_low_reliability(
    summaries,
):

    warnings = []

    for judge_type, summary in (
        summaries.items()
    ):

        reliability = (
            safe_float(
                summary.get(
                    "reliability",
                    1.0,
                ),
                1.0,
            )
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
# V3.2 약한 전문 영역 탐지
# ============================================================

def detect_weak_domains(
    summaries,
):

    weak_domains = []

    for judge_type, summary in (
        summaries.items()
    ):

        score = (
            safe_float(
                summary.get(
                    "score",
                    0.0,
                )
            )
        )

        if (
            score
            < DOMAIN_REWRITE_FLOOR
        ):

            weak_domains.append({
                "judge_type":
                    judge_type,

                "score":
                    round(
                        score,
                        3,
                    ),

                "minimum":
                    DOMAIN_REWRITE_FLOOR,
            })

    return weak_domains


# ============================================================
# 최종 Consensus
# ============================================================

def build_consensus(
    pool_results,
    reliability_report=None,
):

    summaries = (
        summarize_pool(
            pool_results,
            reliability_report,
        )
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

    weak_domains = (
        detect_weak_domains(
            summaries
        )
    )

    reasons = []

    # ========================================================
    # 1. Fact Critical Risk
    #
    # 점수가 아무리 높아도 REVIEW.
    # ========================================================

    hard_block = any(
        item.get(
            "hard_block",
            False,
        )

        for item in (
            critical_risks
        )
    )

    if hard_block:

        decision = "REVIEW"

        reasons.append(
            "사실성 영역에 critical risk가 있습니다."
        )

    # ========================================================
    # 2. Judge 심한 충돌
    # ========================================================

    elif disagreements[
        "critical"
    ]:

        decision = "REVIEW"

        reasons.append(
            "전문 Judge 간 심한 의견 충돌이 있습니다."
        )

    # ========================================================
    # 3. 복수 Low Confidence
    #
    # 한 Judge의 낮은 confidence만으로
    # 전체를 막지는 않는다.
    #
    # 복수 영역이면 판단 자체가 불안정하므로 REVIEW.
    # ========================================================

    elif len(
        low_confidence
    ) >= 2:

        decision = "REVIEW"

        reasons.append(
            "복수 전문 영역에서 Judge 확신도가 낮습니다."
        )

    # ========================================================
    # 4. 전문 영역 최소 품질 Floor
    #
    # 평균으로 약한 영역이 숨는 것 방지.
    # ========================================================

    elif weak_domains:

        decision = "REWRITE"

        weak_names = ", ".join(
            item[
                "judge_type"
            ]

            for item in (
                weak_domains
            )
        )

        reasons.append(
            "일부 전문 영역이 최소 품질 기준 "
            f"{DOMAIN_REWRITE_FLOOR:.1f}점 미만입니다: "
            f"{weak_names}"
        )

    # ========================================================
    # 5. 전체 Weighted Score
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
    # 추가 경고
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

        # V3.2
        "weak_domains":
            weak_domains,

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
        "🧠 V3.2 CONSENSUS"
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

    # --------------------------------------------------------
    # Weak domains
    # --------------------------------------------------------

    weak_domains = (
        consensus.get(
            "weak_domains",
            [],
        )
    )

    if weak_domains:

        print("")
        print(
            "🔧 Weak domains:"
        )

        for item in (
            weak_domains
        ):

            print(
                " - "
                f"{item['judge_type']}: "
                f"{item['score']:.2f} "
                f"< "
                f"{item['minimum']:.2f}"
            )

    # --------------------------------------------------------
    # 판단 이유
    # --------------------------------------------------------

    reasons = (
        consensus.get(
            "reasons",
            [],
        )
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

    # --------------------------------------------------------
    # Critical
    # --------------------------------------------------------

    risks = (
        consensus.get(
            "critical_risks",
            [],
        )
    )

    if risks:

        print("")
        print(
            "🚨 Critical risks:"
        )

        for risk in risks:

            print(
                f" - "
                f"{risk['judge_type']}"
            )

    # --------------------------------------------------------
    # Low Confidence
    # --------------------------------------------------------

    low_confidence = (
        consensus.get(
            "low_confidence",
            [],
        )
    )

    if low_confidence:

        print("")
        print(
            "⚠️ Low confidence:"
        )

        for item in (
            low_confidence
        ):

            print(
                " - "
                f"{item['judge_type']}: "
                f"{item['confidence']:.2f}"
            )

    # --------------------------------------------------------
    # Low Reliability
    # --------------------------------------------------------

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

        for item in (
            low_reliability
        ):

            print(
                " - "
                f"{item['judge_type']}: "
                f"{item['reliability']:.2f}"
            )

    print("=" * 64)
