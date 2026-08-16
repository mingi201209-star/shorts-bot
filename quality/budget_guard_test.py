# quality/budget_guard_test.py

import os
from types import SimpleNamespace

from quality.budget_guard import (
    authorize_call,
    record_usage,
    get_budget_status,
    reset_budget,
    BudgetExceededError,
)


PASSED = 0
FAILED = 0


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


def make_fake_response(
    prompt_tokens,
    completion_tokens,
    cached_tokens=0,
):
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=SimpleNamespace(
            cached_tokens=cached_tokens,
        ),
    )

    return SimpleNamespace(
        usage=usage
    )


# ============================================================
# 1. 호출 횟수 제한
# ============================================================

def test_call_limit():

    reset_budget()

    old_value = os.environ.get(
        "V3_MAX_API_CALLS"
    )

    os.environ[
        "V3_MAX_API_CALLS"
    ] = "3"

    try:
        assert_equal(
            "1번째 호출 허용",
            authorize_call(
                "gpt-4o-mini"
            ),
            1,
        )

        assert_equal(
            "2번째 호출 허용",
            authorize_call(
                "gpt-4o-mini"
            ),
            2,
        )

        assert_equal(
            "3번째 호출 허용",
            authorize_call(
                "gpt-4o-mini"
            ),
            3,
        )

        blocked = False

        try:
            authorize_call(
                "gpt-4o-mini"
            )
        except BudgetExceededError:
            blocked = True

        assert_true(
            "4번째 호출 차단",
            blocked,
        )

    finally:
        if old_value is None:
            os.environ.pop(
                "V3_MAX_API_CALLS",
                None,
            )
        else:
            os.environ[
                "V3_MAX_API_CALLS"
            ] = old_value

        reset_budget()


# ============================================================
# 2. 실제 usage 비용 계산
# ============================================================

def test_usage_cost():

    reset_budget()

    response = make_fake_response(
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        cached_tokens=0,
    )

    result = record_usage(
        "gpt-4o-mini",
        response,
    )

    # 현재 가격표 기준:
    #
    # input:
    # 1M × $0.15/M = $0.15
    #
    # output:
    # 1M × $0.60/M = $0.60
    #
    # total = $0.75

    assert_equal(
        "1M input + 1M output 비용",
        round(
            result["cost_usd"],
            6,
        ),
        0.75,
    )

    reset_budget()


# ============================================================
# 3. Cached input 비용
# ============================================================

def test_cached_usage_cost():

    reset_budget()

    response = make_fake_response(
        prompt_tokens=1_000_000,
        completion_tokens=0,
        cached_tokens=1_000_000,
    )

    result = record_usage(
        "gpt-4o-mini",
        response,
    )

    assert_equal(
        "1M cached input 비용",
        round(
            result["cost_usd"],
            6,
        ),
        0.075,
    )

    reset_budget()


# ============================================================
# 4. 비용 한도 초과 후 다음 호출 차단
# ============================================================

def test_cost_limit():

    reset_budget()

    old_cost = os.environ.get(
        "V3_MAX_COST_USD"
    )

    old_calls = os.environ.get(
        "V3_MAX_API_CALLS"
    )

    os.environ[
        "V3_MAX_COST_USD"
    ] = "0.01"

    os.environ[
        "V3_MAX_API_CALLS"
    ] = "8"

    try:
        authorize_call(
            "gpt-4o-mini"
        )

        # 실제 API는 부르지 않고
        # 가짜 usage만 넣어서
        # 비용을 $0.01보다 크게 만든다.
        response = make_fake_response(
            prompt_tokens=100_000,
            completion_tokens=10_000,
            cached_tokens=0,
        )

        result = record_usage(
            "gpt-4o-mini",
            response,
        )

        assert_true(
            "가짜 사용량으로 비용 한도 초과",
            result[
                "over_budget"
            ],
        )

        blocked = False

        try:
            authorize_call(
                "gpt-4o-mini"
            )
        except BudgetExceededError:
            blocked = True

        assert_true(
            "비용 초과 후 다음 호출 차단",
            blocked,
        )

    finally:
        if old_cost is None:
            os.environ.pop(
                "V3_MAX_COST_USD",
                None,
            )
        else:
            os.environ[
                "V3_MAX_COST_USD"
            ] = old_cost

        if old_calls is None:
            os.environ.pop(
                "V3_MAX_API_CALLS",
                None,
            )
        else:
            os.environ[
                "V3_MAX_API_CALLS"
            ] = old_calls

        reset_budget()


# ============================================================
# 5. 미등록 모델 차단
# ============================================================

def test_unknown_model_block():

    reset_budget()

    blocked = False

    try:
        authorize_call(
            "unknown-expensive-model"
        )
    except BudgetExceededError:
        blocked = True

    assert_true(
        "미등록 모델 즉시 차단",
        blocked,
    )

    status = get_budget_status()

    assert_equal(
        "미등록 모델은 호출 슬롯도 소비하지 않음",
        status["calls"],
        0,
    )

    reset_budget()


# ============================================================
# 6. Reset 정상 작동
# ============================================================

def test_reset_budget():

    reset_budget()

    authorize_call(
        "gpt-4o-mini"
    )

    response = make_fake_response(
        prompt_tokens=10_000,
        completion_tokens=1_000,
        cached_tokens=0,
    )

    record_usage(
        "gpt-4o-mini",
        response,
    )

    before = get_budget_status()

    assert_true(
        "Reset 전 calls 존재",
        before["calls"] > 0,
    )

    assert_true(
        "Reset 전 비용 존재",
        before["cost_usd"] > 0,
    )

    reset_budget()

    after = get_budget_status()

    assert_equal(
        "Reset 후 calls = 0",
        after["calls"],
        0,
    )

    assert_equal(
        "Reset 후 input = 0",
        after["input_tokens"],
        0,
    )

    assert_equal(
        "Reset 후 cached = 0",
        after[
            "cached_input_tokens"
        ],
        0,
    )

    assert_equal(
        "Reset 후 output = 0",
        after["output_tokens"],
        0,
    )

    assert_equal(
        "Reset 후 cost = 0",
        after["cost_usd"],
        0.0,
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
        "💰 SHORTS V3.2 BUDGET GUARD SELF TEST"
    )
    print("=" * 64)

    tests = [
        test_call_limit,
        test_usage_cost,
        test_cached_usage_cost,
        test_cost_limit,
        test_unknown_model_block,
        test_reset_budget,
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

            reset_budget()

    print("")
    print("=" * 64)
    print("📊 BUDGET GUARD TEST RESULT")
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
            "🏆 V3.2 BUDGET GUARD TEST PASSED"
        )

        success = True

    else:
        print("")
        print(
            "🚨 V3.2 BUDGET GUARD TEST FAILED"
        )

        success = False

    print("=" * 64)

    return success


if __name__ == "__main__":

    success = run_all_tests()

    if not success:
        raise SystemExit(1)
