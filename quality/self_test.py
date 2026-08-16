# quality/self_test.py

from quality.consensus import build_consensus

from quality.review_router import (
    choose_review_route,
    evaluate_fact_appeal,
)

from quality.rewrite_engine import (
    find_rewrite_domains,
)


# ============================================================
# Shorts V3.1 Quality System Self Test
# ============================================================

PASSED = 0
FAILED = 0


# ============================================================
# 테스트용 Judge 결과
# ============================================================

def make_judge_result(
    judge_type,
    score,
    confidence=0.9,
    critical_risk=False,
    issues=None,
):

    if issues is None:
        issues = []

    return {
        "judge_type": judge_type,
        "score": score,
        "confidence": confidence,
        "reason": "SELF TEST",
        "issues": issues,
        "critical_risk": critical_risk,
    }


# ============================================================
# Assert
# ============================================================

def assert_equal(name, actual, expected):

    global PASSED
    global FAILED

    if actual == expected:
        PASSED += 1
        print(f"✅ PASS | {name}")
        return True

    FAILED += 1

    print(f"❌ FAIL | {name}")
    print(f"   expected: {expected}")
    print(f"   actual:   {actual}")

    return False


def assert_true(name, condition):

    return assert_equal(
        name,
        bool(condition),
        True,
    )


# ============================================================
# 기본 Pool 생성
# ============================================================

def make_good_pool():

    return {
        "hook": [
            make_judge_result(
                "hook",
                9.0,
            )
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
            )
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
            )
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.5,
            )
        ],
    }


# ============================================================
# 1. 정상 PASS
# ============================================================

def test_normal_pass():

    result = build_consensus(
        make_good_pool()
    )

    assert_equal(
        "정상 콘텐츠 → PASS",
        result["decision"],
        "PASS",
    )


# ============================================================
# 2. 약한 Hook
# ============================================================

def test_weak_hook():

    pool = make_good_pool()

    pool["hook"] = [
        make_judge_result(
            "hook",
            4.0,
        )
    ]

    result = build_consensus(
        pool
    )

    domains = find_rewrite_domains(
        result
    )

    assert_equal(
        "약한 Hook → REWRITE",
        result["decision"],
        "REWRITE",
    )

    assert_true(
        "Hook Rewrite 대상",
        "hook" in domains,
    )


# ============================================================
# 3. Judge 심한 충돌
# ============================================================

def test_judge_disagreement():

    pool = make_good_pool()

    pool["hook"] = [
        make_judge_result(
            "hook",
            9.0,
        ),
        make_judge_result(
            "hook",
            4.0,
        ),
    ]

    result = build_consensus(
        pool
    )

    assert_equal(
        "Judge 심한 충돌 → REVIEW",
        result["decision"],
        "REVIEW",
    )

    assert_true(
        "Critical disagreement 감지",
        len(
            result["disagreements"]["critical"]
        ) > 0,
    )


# ============================================================
# 4. Fact Critical → REVIEW
# ============================================================

def test_fact_critical_review():

    pool = make_good_pool()

    pool["fact"] = [
        make_judge_result(
            "fact",
            9.5,
            critical_risk=True,
            issues=[
                "검증되지 않은 사실"
            ],
        )
    ]

    result = build_consensus(
        pool
    )

    assert_equal(
        "Fact Critical → REVIEW",
        result["decision"],
        "REVIEW",
    )


# ============================================================
# 5. Fact Critical → FACT_EXTRA_JUDGE
# ============================================================

def test_fact_critical_route():

    pool = make_good_pool()

    pool["fact"] = [
        make_judge_result(
            "fact",
            9.0,
            critical_risk=True,
        )
    ]

    consensus = build_consensus(
        pool
    )

    route = choose_review_route(
        consensus
    )

    assert_equal(
        "Fact Critical → FACT_EXTRA_JUDGE",
        route["route"],
        "FACT_EXTRA_JUDGE",
    )

    assert_equal(
        "Fact 재심 영역 1개",
        route["domains"],
        ["fact"],
    )


# ============================================================
# 6. 복수 Low Confidence
# ============================================================

def test_low_confidence():

    pool = make_good_pool()

    pool["hook"] = [
        make_judge_result(
            "hook",
            8.5,
            confidence=0.40,
        )
    ]

    pool["novelty"] = [
        make_judge_result(
            "novelty",
            8.5,
            confidence=0.45,
        )
    ]

    result = build_consensus(
        pool
    )

    assert_equal(
        "복수 Low Confidence → REVIEW",
        result["decision"],
        "REVIEW",
    )

    assert_equal(
        "Low Confidence 2개 탐지",
        len(
            result["low_confidence"]
        ),
        2,
    )


# ============================================================
# 7. Visual 문제
# ============================================================

def test_visual_rewrite():

    pool = make_good_pool()

    pool["visual"] = [
        make_judge_result(
            "visual",
            4.0,
            issues=[
                "대사와 화면 연결 부족",
            ],
        )
    ]

    result = build_consensus(
        pool
    )

    domains = find_rewrite_domains(
        result
    )

    assert_equal(
        "Visual 문제 → REWRITE",
        result["decision"],
        "REWRITE",
    )

    assert_true(
        "Visual Rewrite 대상",
        "visual" in domains,
    )


# ============================================================
# 8. 일반 REVIEW → EXTRA_JUDGE
# ============================================================

def test_review_router():

    pool = make_good_pool()

    pool["hook"] = [
        make_judge_result(
            "hook",
            9.0,
        ),
        make_judge_result(
            "hook",
            5.0,
        ),
    ]

    consensus = build_consensus(
        pool
    )

    route = choose_review_route(
        consensus
    )

    assert_equal(
        "Hook 충돌 → EXTRA_JUDGE",
        route["route"],
        "EXTRA_JUDGE",
    )

    assert_true(
        "Hook 재심 대상",
        "hook" in route["domains"],
    )


# ============================================================
# 9. 너무 많은 불확실 영역
# ============================================================

def test_too_many_uncertain_domains():

    pool = make_good_pool()

    pool["hook"] = [
        make_judge_result(
            "hook",
            9.0,
            confidence=0.4,
        )
    ]

    pool["novelty"] = [
        make_judge_result(
            "novelty",
            8.5,
            confidence=0.4,
        )
    ]

    pool["visual"] = [
        make_judge_result(
            "visual",
            8.5,
            confidence=0.4,
        )
    ]

    consensus = build_consensus(
        pool
    )

    route = choose_review_route(
        consensus
    )

    assert_equal(
        "3개 영역 불확실 → HOLD",
        route["route"],
        "HOLD",
    )


# ============================================================
# 10. Critical Risk 평균 은폐 방지
# ============================================================

def test_critical_not_hidden_by_average():

    pool = make_good_pool()

    pool["hook"][0]["score"] = 10.0
    pool["novelty"][0]["score"] = 10.0
    pool["visual"][0]["score"] = 10.0

    pool["fact"] = [
        make_judge_result(
            "fact",
            10.0,
            critical_risk=True,
        )
    ]

    consensus = build_consensus(
        pool
    )

    assert_equal(
        "10점이어도 Fact Critical → REVIEW",
        consensus["decision"],
        "REVIEW",
    )


# ============================================================
# 11. 선택적 Rewrite
# ============================================================

def test_selective_rewrite():

    pool = make_good_pool()

    pool["visual"] = [
        make_judge_result(
            "visual",
            5.0,
        )
    ]

    consensus = build_consensus(
        pool
    )

    domains = find_rewrite_domains(
        consensus
    )

    assert_equal(
        "선택적 Rewrite 영역 수",
        len(domains),
        1,
    )

    assert_equal(
        "선택적 Rewrite = visual",
        domains[0],
        "visual",
    )


# ============================================================
# 12. Fact Appeal
# Critical + Critical → HOLD
# ============================================================

def test_fact_appeal_hold():

    merged_pool = {
        "fact": [
            make_judge_result(
                "fact",
                8.0,
                critical_risk=True,
            ),
            make_judge_result(
                "fact",
                7.5,
                critical_risk=True,
            ),
        ]
    }

    result = evaluate_fact_appeal(
        merged_pool
    )

    assert_equal(
        "Fact Critical 2회 → HOLD",
        result["status"],
        "HOLD",
    )


# ============================================================
# 13. Fact Appeal
# Critical + Normal → DISAGREEMENT
# ============================================================

def test_fact_appeal_disagreement():

    merged_pool = {
        "fact": [
            make_judge_result(
                "fact",
                8.0,
                critical_risk=True,
            ),
            make_judge_result(
                "fact",
                8.5,
                critical_risk=False,
            ),
        ]
    }

    result = evaluate_fact_appeal(
        merged_pool
    )

    assert_equal(
        "Fact Judge 충돌 → DISAGREEMENT",
        result["status"],
        "DISAGREEMENT",
    )


# ============================================================
# 14. Fact Appeal
# Normal + Normal → CLEARED
# ============================================================

def test_fact_appeal_cleared():

    merged_pool = {
        "fact": [
            make_judge_result(
                "fact",
                8.0,
                critical_risk=False,
            ),
            make_judge_result(
                "fact",
                9.0,
                critical_risk=False,
            ),
        ]
    }

    result = evaluate_fact_appeal(
        merged_pool
    )

    assert_equal(
        "Fact 둘 다 정상 → CLEARED",
        result["status"],
        "CLEARED",
    )


# ============================================================
# 15. Fact Appeal 결과 부족
# ============================================================

def test_fact_appeal_insufficient():

    merged_pool = {
        "fact": [
            make_judge_result(
                "fact",
                8.0,
                critical_risk=True,
            )
        ]
    }

    result = evaluate_fact_appeal(
        merged_pool
    )

    assert_equal(
        "Fact 재심 결과 부족 → INSUFFICIENT",
        result["status"],
        "INSUFFICIENT",
    )


# ============================================================
# 16. Reliability 표본 부족 보호
# ============================================================

def test_reliability_small_sample():

    report = {
        "hook": {
            "reliability": 0.5,
            "statistics": {
                "evaluated": 5,
            },
        }
    }

    consensus = build_consensus(
        make_good_pool(),
        reliability_report=report,
    )

    reliability = (
        consensus[
            "domain_summaries"
        ]["hook"]["reliability"]
    )

    assert_equal(
        "표본 5개 → Reliability 1.0 고정",
        reliability,
        1.0,
    )


# ============================================================
# 17. Reliability 10~29 보호
# ============================================================

def test_reliability_10_29():

    report = {
        "hook": {
            "reliability": 0.5,
            "statistics": {
                "evaluated": 20,
            },
        }
    }

    consensus = build_consensus(
        make_good_pool(),
        reliability_report=report,
    )

    reliability = (
        consensus[
            "domain_summaries"
        ]["hook"]["reliability"]
    )

    assert_equal(
        "표본 20개 → 최소 Reliability 0.90",
        reliability,
        0.90,
    )


# ============================================================
# 18. Reliability 30~99 보호
# ============================================================

def test_reliability_30_99():

    report = {
        "hook": {
            "reliability": 0.5,
            "statistics": {
                "evaluated": 60,
            },
        }
    }

    consensus = build_consensus(
        make_good_pool(),
        reliability_report=report,
    )

    reliability = (
        consensus[
            "domain_summaries"
        ]["hook"]["reliability"]
    )

    assert_equal(
        "표본 60개 → 최소 Reliability 0.80",
        reliability,
        0.80,
    )


# ============================================================
# 19. Reliability 100+ 본격 적용
# ============================================================

def test_reliability_100_plus():

    report = {
        "hook": {
            "reliability": 0.55,
            "statistics": {
                "evaluated": 150,
            },
        }
    }

    consensus = build_consensus(
        make_good_pool(),
        reliability_report=report,
    )

    reliability = (
        consensus[
            "domain_summaries"
        ]["hook"]["reliability"]
    )

    assert_equal(
        "표본 150개 → Reliability 0.55 적용",
        reliability,
        0.55,
    )


# ============================================================
# 20. Judge 독재 방지 상한
# ============================================================

def test_reliability_upper_limit():

    report = {
        "fact": {
            "reliability": 5.0,
            "statistics": {
                "evaluated": 200,
            },
        }
    }

    consensus = build_consensus(
        make_good_pool(),
        reliability_report=report,
    )

    reliability = (
        consensus[
            "domain_summaries"
        ]["fact"]["reliability"]
    )

    assert_equal(
        "Judge Reliability 최대 1.25",
        reliability,
        1.25,
    )


# ============================================================
# 21. Judge 완전 제거 방지 하한
# ============================================================

def test_reliability_lower_limit():

    report = {
        "visual": {
            "reliability": 0.0,
            "statistics": {
                "evaluated": 200,
            },
        }
    }

    consensus = build_consensus(
        make_good_pool(),
        reliability_report=report,
    )

    reliability = (
        consensus[
            "domain_summaries"
        ]["visual"]["reliability"]
    )

    assert_equal(
        "Judge Reliability 최소 0.50",
        reliability,
        0.50,
    )


# ============================================================
# 전체 실행
# ============================================================

def run_all_tests():

    global PASSED
    global FAILED

    PASSED = 0
    FAILED = 0

    print("")
    print("=" * 64)
    print("🧪 SHORTS V3.1 QUALITY ENGINE SELF TEST")
    print("=" * 64)

    tests = [
        test_normal_pass,
        test_weak_hook,
        test_judge_disagreement,
        test_fact_critical_review,
        test_fact_critical_route,
        test_low_confidence,
        test_visual_rewrite,
        test_review_router,
        test_too_many_uncertain_domains,
        test_critical_not_hidden_by_average,
        test_selective_rewrite,
        test_fact_appeal_hold,
        test_fact_appeal_disagreement,
        test_fact_appeal_cleared,
        test_fact_appeal_insufficient,
        test_reliability_small_sample,
        test_reliability_10_29,
        test_reliability_30_99,
        test_reliability_100_plus,
        test_reliability_upper_limit,
        test_reliability_lower_limit,
    ]

    for test in tests:

        print("")
        print(
            f"▶ {test.__name__}"
        )

        try:
            test()

        except Exception as e:

            FAILED += 1

            print(
                f"💥 EXCEPTION | {test.__name__}"
            )

            print(
                f"   {type(e).__name__}: {e}"
            )

    print("")
    print("=" * 64)
    print("📊 SELF TEST RESULT")
    print("=" * 64)

    print(
        f"✅ PASS: {PASSED}"
    )

    print(
        f"❌ FAIL: {FAILED}"
    )

    if FAILED == 0:

        print("")
        print(
            "🏆 V3.1 QUALITY ENGINE "
            "SELF TEST PASSED"
        )

        success = True

    else:

        print("")
        print(
            "🚨 V3.1 QUALITY ENGINE "
            "SELF TEST FAILED"
        )

        print(
            "실제 API 재심 테스트 금지."
        )

        success = False

    print("=" * 64)

    return success


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":

    success = run_all_tests()

    if not success:
        raise SystemExit(1)
