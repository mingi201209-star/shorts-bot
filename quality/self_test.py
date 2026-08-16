# quality/self_test.py

from quality.consensus import (
    build_consensus,
)

from quality.review_router import (
    choose_review_route,
)

from quality.rewrite_engine import (
    find_rewrite_domains,
)


# ============================================================
# Shorts V3 Quality System Self Test
# ============================================================
#
# 목적:
#   실제 제작 파이프라인에 연결하기 전에
#   품질 엔진의 의사결정 로직 자체를 검증한다.
#
# 특징:
#   - 영상 생성 없음
#   - Telegram 전송 없음
#
# 테스트:
#   1. 정상 PASS
#   2. 약한 Hook
#   3. Judge 의견 충돌
#   4. Fact Critical Risk
#   5. 낮은 Confidence
#   6. Visual 문제
#   7. REVIEW Router
#   8. 여러 영역 동시 불확실
#   9. Critical Risk 평균점수 은폐 방지
#   10. 선택적 Rewrite
#
# ============================================================


PASSED = 0
FAILED = 0


# ============================================================
# 테스트용 Judge 결과 생성
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
# ASSERT
# ============================================================

def assert_equal(
    name,
    actual,
    expected,
):

    global PASSED
    global FAILED

    if actual == expected:

        PASSED += 1

        print(
            f"✅ PASS | {name}"
        )

        return True

    FAILED += 1

    print(
        f"❌ FAIL | {name}"
    )

    print(
        f"   expected: {expected}"
    )

    print(
        f"   actual:   {actual}"
    )

    return False


def assert_true(
    name,
    condition,
):

    return assert_equal(
        name,
        bool(condition),
        True,
    )


# ============================================================
# 1. 정상 PASS
# ============================================================

def test_normal_pass():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                9.0,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.2,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.4,
            ),
        ],
    }

    result = build_consensus(
        pool
    )

    assert_equal(
        "정상 콘텐츠 → PASS",
        result["decision"],
        "PASS",
    )


# ============================================================
# 2. Hook 약함
# ============================================================

def test_weak_hook():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                4.0,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.0,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.0,
            ),
        ],
    }

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
# 3. 같은 전문 Judge끼리 심한 충돌
# ============================================================

def test_judge_disagreement():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                9.0,
            ),

            make_judge_result(
                "hook",
                4.0,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.5,
            ),
        ],
    }

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
            result[
                "disagreements"
            ]["critical"]
        ) > 0,
    )


# ============================================================
# 4. Fact Critical Risk
# ============================================================

def test_fact_critical():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                9.5,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                9.0,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                8.5,
                critical_risk=True,
                issues=[
                    "확인되지 않은 수치"
                ],
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                9.0,
            ),
        ],
    }

    result = build_consensus(
        pool
    )

    assert_equal(
        "Fact Critical → REVIEW",
        result["decision"],
        "REVIEW",
    )

    route = choose_review_route(
        result
    )

    assert_equal(
        "Fact Critical → HOLD",
        route["route"],
        "HOLD",
    )


# ============================================================
# 5. 복수 Judge 낮은 Confidence
# ============================================================

def test_low_confidence():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                8.5,
                confidence=0.40,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
                confidence=0.45,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
                confidence=0.90,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.5,
                confidence=0.90,
            ),
        ],
    }

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
            result[
                "low_confidence"
            ]
        ),
        2,
    )


# ============================================================
# 6. Visual 문제
# ============================================================

def test_visual_rewrite():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                8.5,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                4.0,
                issues=[
                    "대사와 B-roll 연결 부족",
                    "추상적인 검색어",
                ],
            ),
        ],
    }

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
# 7. REVIEW → EXTRA JUDGE
# ============================================================

def test_review_router():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                9.0,
            ),

            make_judge_result(
                "hook",
                5.0,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.5,
            ),
        ],
    }

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
# 8. 여러 영역 동시에 불확실
# ============================================================

def test_too_many_uncertain_domains():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                9.0,
                confidence=0.4,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                8.5,
                confidence=0.4,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
                confidence=0.4,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                8.5,
            ),
        ],
    }

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
# 9. Critical Risk가 평균점수로 묻히지 않는지
# ============================================================

def test_critical_not_hidden_by_average():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                10.0,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                10.0,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                10.0,
                critical_risk=True,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                10.0,
            ),
        ],
    }

    consensus = build_consensus(
        pool
    )

    assert_equal(
        "10점이어도 Fact Critical → REVIEW",
        consensus["decision"],
        "REVIEW",
    )


# ============================================================
# 10. 한 영역만 낮으면 그 영역만 Rewrite
# ============================================================

def test_selective_rewrite():

    pool = {

        "hook": [
            make_judge_result(
                "hook",
                9.0,
            ),
        ],

        "novelty": [
            make_judge_result(
                "novelty",
                9.0,
            ),
        ],

        "fact": [
            make_judge_result(
                "fact",
                9.0,
            ),
        ],

        "visual": [
            make_judge_result(
                "visual",
                5.0,
            ),
        ],
    }

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
# 전체 실행
# ============================================================

def run_all_tests():

    global PASSED
    global FAILED

    PASSED = 0
    FAILED = 0

    print("")
    print("=" * 64)
    print(
        "🧪 SHORTS V3 QUALITY ENGINE SELF TEST"
    )
    print("=" * 64)

    tests = [
        test_normal_pass,
        test_weak_hook,
        test_judge_disagreement,
        test_fact_critical,
        test_low_confidence,
        test_visual_rewrite,
        test_review_router,
        test_too_many_uncertain_domains,
        test_critical_not_hidden_by_average,
        test_selective_rewrite,
    ]

    for test in tests:

        print("")
        print(
            f"▶ {test.__name__}"
        )

        try:

            test()

        except Exception as e:

            # 중요:
            # global FAILED는
            # run_all_tests() 시작 부분에서
            # 이미 선언했으므로
            # 여기서 다시 선언하지 않는다.

            FAILED += 1

            print(
                f"💥 EXCEPTION | "
                f"{test.__name__}"
            )

            print(
                f"   {type(e).__name__}: {e}"
            )

    print("")
    print("=" * 64)
    print(
        "📊 SELF TEST RESULT"
    )
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
            "🏆 QUALITY ENGINE "
            "SELF TEST PASSED"
        )

        print(
            "다음 단계의 통합 테스트로 "
            "진행할 수 있습니다."
        )

        success = True

    else:

        print("")
        print(
            "🚨 QUALITY ENGINE "
            "SELF TEST FAILED"
        )

        print(
            "main.py 연결 금지."
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
