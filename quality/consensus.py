from statistics import mean


# ============================================================
# Consensus Engine V3.2.1.2
# ============================================================
#
# 핵심:
# - Fact critical은 계속 hard block
# - 심한 Judge 충돌 / 복수 low confidence는 REVIEW
# - 이상적인 PASS 기준은 유지
# - 그러나 충분히 좋은 콘텐츠는 GOOD_ENOUGH PASS 허용
#
# GOOD_ENOUGH 조건:
#   weighted >= 6.8
#   hook >= 7
#   novelty >= 5
#   fact >= 7
#   visual >= 7
#   fact critical 없음
# ============================================================


PASS_SCORE = 7.5
REWRITE_SCORE = 5.5
DOMAIN_REWRITE_FLOOR = 6.5
MIN_CONFIDENCE = 0.65
DISAGREEMENT_WARNING = 2.0
DISAGREEMENT_CRITICAL = 3.5

GOOD_ENOUGH_SCORE = 6.8
GOOD_ENOUGH_FLOORS = {
    "hook": 7.0,
    "novelty": 5.0,
    "fact": 7.0,
    "visual": 7.0,
}

DOMAIN_WEIGHTS = {
    "hook": 1.2,
    "novelty": 1.1,
    "fact": 1.4,
    "visual": 1.0,
}

CRITICAL_DOMAINS = {
    "fact",
}


# ============================================================
# Utilities
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def clamp(value, minimum, maximum):
    return max(
        minimum,
        min(value, maximum),
    )


# ============================================================
# Reliability
# ============================================================

def get_effective_reliability(
    judge_type,
    reliability_report=None,
):

    if not isinstance(
        reliability_report,
        dict,
    ):
        return 1.0

    judge_data = reliability_report.get(
        judge_type
    )

    if not isinstance(judge_data, dict):
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

    if not isinstance(statistics, dict):
        statistics = {}

    samples = safe_int(
        statistics.get(
            "evaluated",
            0,
        ),
        0,
    )

    if samples < 10:
        return 1.0

    if samples < 30:
        return round(
            clamp(
                raw_reliability,
                0.90,
                1.10,
            ),
            3,
        )

    if samples < 100:
        return round(
            clamp(
                raw_reliability,
                0.80,
                1.20,
            ),
            3,
        )

    return round(
        clamp(
            raw_reliability,
            0.50,
            1.25,
        ),
        3,
    )


# ============================================================
# Domain Summary
# ============================================================

def summarize_domain(
    judge_type,
    results,
    reliability_report=None,
):

    reliability = get_effective_reliability(
        judge_type,
        reliability_report,
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
            "issues": ["Judge 결과 없음"],
            "reliability": reliability,
        }

    scores = []
    confidences = []
    issues = []
    critical_risk = False

    for result in results:

        if not isinstance(result, dict):
            continue

        score = clamp(
            safe_float(
                result.get("score", 0.0)
            ),
            0.0,
            10.0,
        )

        confidence = clamp(
            safe_float(
                result.get(
                    "confidence",
                    0.0,
                )
            ),
            0.0,
            1.0,
        )

        scores.append(score)
        confidences.append(confidence)

        if result.get(
            "critical_risk",
            False,
        ):
            critical_risk = True

        result_issues = result.get(
            "issues",
            [],
        )

        if isinstance(result_issues, list):
            for issue in result_issues:
                if issue:
                    issues.append(str(issue))

    if not scores:
        return {
            "judge_type": judge_type,
            "score": 0.0,
            "adjusted_score": 0.0,
            "confidence": 0.0,
            "disagreement": 10.0,
            "critical_risk": True,
            "review_count": 0,
            "issues": ["유효한 Judge 결과 없음"],
            "reliability": reliability,
        }

    score_avg = mean(scores)
    confidence_avg = (
        mean(confidences)
        if confidences
        else 0.0
    )

    disagreement = (
        max(scores) - min(scores)
        if len(scores) > 1
        else 0.0
    )

    # confidence는 점수에 곱하지 않는다.
    adjusted_score = score_avg

    return {
        "judge_type": judge_type,
        "score": round(score_avg, 3),
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
        "review_count": len(scores),
        "issues": list(
            dict.fromkeys(issues)
        ),
        "reliability": reliability,
    }


def summarize_pool(
    pool_results,
    reliability_report=None,
):

    return {
        judge_type: summarize_domain(
            judge_type,
            results,
            reliability_report,
        )
        for judge_type, results
        in pool_results.items()
    }


# ============================================================
# Weighted Score
# ============================================================

def calculate_domain_weight(
    judge_type,
    summary,
):

    return (
        DOMAIN_WEIGHTS.get(
            judge_type,
            1.0,
        )
        * safe_float(
            summary.get(
                "reliability",
                1.0,
            ),
            1.0,
        )
    )


def calculate_weighted_score(summaries):

    weighted_total = 0.0
    total_weight = 0.0

    for judge_type, summary in summaries.items():

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

        weighted_total += score * weight
        total_weight += weight

    if total_weight <= 0:
        return 0.0

    return round(
        weighted_total / total_weight,
        3,
    )


# ============================================================
# Detectors
# ============================================================

def detect_disagreements(summaries):

    warnings = []
    critical = []

    for judge_type, summary in summaries.items():

        disagreement = safe_float(
            summary.get(
                "disagreement",
                0.0,
            )
        )

        item = {
            "judge_type": judge_type,
            "disagreement": disagreement,
        }

        if disagreement >= DISAGREEMENT_CRITICAL:
            critical.append(item)
        elif disagreement >= DISAGREEMENT_WARNING:
            warnings.append(item)

    return {
        "warnings": warnings,
        "critical": critical,
    }


def detect_low_confidence(summaries):

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
        if safe_float(
            summary.get(
                "confidence",
                0.0,
            )
        ) < MIN_CONFIDENCE
    ]


def detect_critical_risks(summaries):

    risks = []

    for judge_type, summary in summaries.items():

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


def detect_low_reliability(summaries):

    return [
        {
            "judge_type": judge_type,
            "reliability": safe_float(
                summary.get(
                    "reliability",
                    1.0,
                ),
                1.0,
            ),
        }
        for judge_type, summary
        in summaries.items()
        if safe_float(
            summary.get(
                "reliability",
                1.0,
            ),
            1.0,
        ) < 0.80
    ]


def detect_weak_domains(summaries):

    weak_domains = []

    for judge_type, summary in summaries.items():

        score = safe_float(
            summary.get(
                "score",
                0.0,
            )
        )

        if score < DOMAIN_REWRITE_FLOOR:
            weak_domains.append({
                "judge_type": judge_type,
                "score": round(score, 3),
                "minimum": DOMAIN_REWRITE_FLOOR,
            })

    return weak_domains


def meets_good_enough_floors(summaries):

    for judge_type, minimum in (
        GOOD_ENOUGH_FLOORS.items()
    ):

        summary = summaries.get(
            judge_type,
            {},
        )

        score = safe_float(
            summary.get(
                "score",
                0.0,
            )
        )

        if score < minimum:
            return False

    return True


# ============================================================
# Consensus
# ============================================================

def build_consensus(
    pool_results,
    reliability_report=None,
):

    summaries = summarize_pool(
        pool_results,
        reliability_report,
    )

    weighted_score = calculate_weighted_score(
        summaries
    )

    disagreements = detect_disagreements(
        summaries
    )

    low_confidence = detect_low_confidence(
        summaries
    )

    critical_risks = detect_critical_risks(
        summaries
    )

    low_reliability = detect_low_reliability(
        summaries
    )

    weak_domains = detect_weak_domains(
        summaries
    )

    hard_block = any(
        item.get(
            "hard_block",
            False,
        )
        for item in critical_risks
    )

    reasons = []
    pass_tier = None

    # 1. Fact critical은 절대 우회하지 않는다.
    if hard_block:
        decision = "REVIEW"
        reasons.append(
            "사실성 영역에 critical risk가 있습니다."
        )

    # 2. 심한 Judge 충돌은 REVIEW.
    elif disagreements["critical"]:
        decision = "REVIEW"
        reasons.append(
            "전문 Judge 간 심한 의견 충돌이 있습니다."
        )

    # 3. 복수 low confidence도 REVIEW.
    elif len(low_confidence) >= 2:
        decision = "REVIEW"
        reasons.append(
            "복수 전문 영역에서 Judge 확신도가 낮습니다."
        )

    # 4. 기존 이상적 PASS.
    elif (
        not weak_domains
        and weighted_score >= PASS_SCORE
    ):
        decision = "PASS"
        pass_tier = "IDEAL"
        reasons.append(
            "종합 품질 점수와 모든 Domain 기준을 충족했습니다."
        )

    # 5. GOOD_ENOUGH PASS.
    #    한 영역이 6.5 아래여도 실제 제작 가치가 충분하면 렌더한다.
    elif (
        weighted_score >= GOOD_ENOUGH_SCORE
        and meets_good_enough_floors(
            summaries
        )
    ):
        decision = "PASS"
        pass_tier = "GOOD_ENOUGH"
        reasons.append(
            "절대 차단 사유가 없고 Good Enough 제작 기준을 충족했습니다."
        )

    # 6. 그 외 약한 Domain은 Rewrite.
    elif weak_domains:
        decision = "REWRITE"
        weak_names = ", ".join(
            item["judge_type"]
            for item in weak_domains
        )
        reasons.append(
            "일부 전문 영역이 최소 품질 기준 "
            f"{DOMAIN_REWRITE_FLOOR:.1f}점 미만입니다: "
            f"{weak_names}"
        )

    elif weighted_score >= REWRITE_SCORE:
        decision = "REWRITE"
        reasons.append(
            "핵심 구조는 유지 가능하지만 일부 수정이 필요합니다."
        )

    else:
        decision = "REWRITE"
        reasons.append(
            "종합 품질 점수가 낮아 재작성 필요성이 큽니다."
        )

    if disagreements["warnings"]:
        reasons.append(
            "일부 전문 영역에서 Judge 의견 차이가 있습니다."
        )

    if low_reliability:
        reasons.append(
            "장기 신뢰도가 낮은 Judge가 포함되어 있습니다."
        )

    return {
        "decision": decision,
        "pass_tier": pass_tier,
        "weighted_score": weighted_score,
        "domain_summaries": summaries,
        "disagreements": disagreements,
        "low_confidence": low_confidence,
        "critical_risks": critical_risks,
        "low_reliability": low_reliability,
        "weak_domains": weak_domains,
        "reasons": reasons,
    }


# ============================================================
# Logs
# ============================================================

def print_consensus(consensus):

    print("")
    print("=" * 64)
    print("🧠 V3.2 CONSENSUS")
    print("=" * 64)
    print(
        "결정:",
        consensus.get(
            "decision",
            "UNKNOWN",
        ),
    )
    print(
        "PASS Tier:",
        consensus.get(
            "pass_tier"
        )
        or "-",
    )
    print(
        "종합 점수:",
        consensus.get(
            "weighted_score",
            0.0,
        ),
    )

    print("")
    print("전문 영역:")

    for judge_type, summary in (
        consensus.get(
            "domain_summaries",
            {},
        ).items()
    ):
        print(
            f" - {judge_type}: "
            f"score {summary.get('score', 0):.2f} "
            f"| confidence {summary.get('confidence', 0):.2f} "
            f"| reliability {summary.get('reliability', 1):.2f} "
            f"| disagreement {summary.get('disagreement', 0):.2f}"
        )

    weak_domains = consensus.get(
        "weak_domains",
        [],
    )

    if weak_domains:
        print("")
        print("🔧 Weak domains:")
        for item in weak_domains:
            print(
                f" - {item['judge_type']}: "
                f"{item['score']:.2f} < {item['minimum']:.2f}"
            )

    reasons = consensus.get(
        "reasons",
        [],
    )

    if reasons:
        print("")
        print("판단 이유:")
        for reason in reasons:
            print(f" - {reason}")

    risks = consensus.get(
        "critical_risks",
        [],
    )

    if risks:
        print("")
        print("🚨 Critical risks:")
        for risk in risks:
            print(
                f" - {risk['judge_type']}"
            )

    low_confidence = consensus.get(
        "low_confidence",
        [],
    )

    if low_confidence:
        print("")
        print("⚠️ Low confidence:")
        for item in low_confidence:
            print(
                f" - {item['judge_type']}: "
                f"{item['confidence']:.2f}"
            )

    low_reliability = consensus.get(
        "low_reliability",
        [],
    )

    if low_reliability:
        print("")
        print("⚠️ Low reliability Judges:")
        for item in low_reliability:
            print(
                f" - {item['judge_type']}: "
                f"{item['reliability']:.2f}"
            )

    print("=" * 64)
