import os
import threading


# ============================================================
# V3.2 Budget Guard
# ============================================================

DEFAULT_MAX_CALLS = 8
DEFAULT_MAX_COST_USD = 0.05


MODEL_PRICES = {
    "gpt-4o-mini": {
        "input": 0.15 / 1_000_000,
        "output": 0.60 / 1_000_000,
        "cached_input": 0.075 / 1_000_000,
    },
}


_lock = threading.Lock()

_state = {
    "calls": 0,
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0.0,
}


class BudgetExceededError(RuntimeError):
    pass


def _read_int(name, default):
    try:
        return int(
            os.environ.get(
                name,
                default,
            )
        )
    except Exception:
        return default


def _read_float(name, default):
    try:
        return float(
            os.environ.get(
                name,
                default,
            )
        )
    except Exception:
        return default


def get_limits():

    return {
        "max_calls": max(
            1,
            _read_int(
                "V3_MAX_API_CALLS",
                DEFAULT_MAX_CALLS,
            ),
        ),
        "max_cost_usd": max(
            0.001,
            _read_float(
                "V3_MAX_COST_USD",
                DEFAULT_MAX_COST_USD,
            ),
        ),
    }


def get_price(model):

    if model not in MODEL_PRICES:
        raise BudgetExceededError(
            f"가격표에 없는 모델입니다: {model}. "
            "비용을 알 수 없는 모델의 호출을 차단합니다."
        )

    return MODEL_PRICES[model]


# ============================================================
# API 호출 직전 검사
# ============================================================

def authorize_call(model):

    get_price(model)

    limits = get_limits()

    with _lock:

        if _state["calls"] >= limits["max_calls"]:
            raise BudgetExceededError(
                "V3 API 호출 횟수 한도 초과: "
                f"{_state['calls']}/"
                f"{limits['max_calls']}"
            )

        if _state["cost_usd"] >= limits["max_cost_usd"]:
            raise BudgetExceededError(
                "V3 비용 한도 초과: "
                f"${_state['cost_usd']:.6f}/"
                f"${limits['max_cost_usd']:.6f}"
            )

        # 호출 슬롯을 API 요청 전에 소비한다.
        # API 오류/예외가 발생해도 무한 재시도 방지.
        _state["calls"] += 1

        return _state["calls"]


# ============================================================
# 실제 API usage 기록
# ============================================================

def record_usage(
    model,
    response,
):

    price = get_price(model)

    usage = getattr(
        response,
        "usage",
        None,
    )

    if usage is None:
        raise RuntimeError(
            "OpenAI 응답에 usage 정보가 없습니다."
        )

    input_tokens = int(
        getattr(
            usage,
            "prompt_tokens",
            0,
        )
        or 0
    )

    output_tokens = int(
        getattr(
            usage,
            "completion_tokens",
            0,
        )
        or 0
    )

    cached_tokens = 0

    details = getattr(
        usage,
        "prompt_tokens_details",
        None,
    )

    if details is not None:
        cached_tokens = int(
            getattr(
                details,
                "cached_tokens",
                0,
            )
            or 0
        )

    cached_tokens = max(
        0,
        min(
            cached_tokens,
            input_tokens,
        ),
    )

    uncached_tokens = (
        input_tokens
        - cached_tokens
    )

    cost = (
        uncached_tokens
        * price["input"]
        + cached_tokens
        * price["cached_input"]
        + output_tokens
        * price["output"]
    )

    with _lock:

        _state["input_tokens"] += input_tokens

        _state[
            "cached_input_tokens"
        ] += cached_tokens

        _state["output_tokens"] += output_tokens

        _state["cost_usd"] += cost

        # 실제 호출 하나가 예상보다 커서
        # 한도를 넘었더라도 기록은 남긴다.
        over_budget = (
            _state["cost_usd"]
            > get_limits()["max_cost_usd"]
        )

    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "over_budget": over_budget,
    }


def get_budget_status():

    with _lock:
        state = dict(_state)

    limits = get_limits()

    state.update(limits)

    return state


def print_budget_status():

    status = get_budget_status()

    print("")
    print("=" * 50)
    print("💰 V3.2 API BUDGET")
    print("=" * 50)

    print(
        "Calls:",
        f"{status['calls']}/"
        f"{status['max_calls']}",
    )

    print(
        "Input tokens:",
        status["input_tokens"],
    )

    print(
        "Cached input:",
        status["cached_input_tokens"],
    )

    print(
        "Output tokens:",
        status["output_tokens"],
    )

    print(
        "Cost:",
        f"${status['cost_usd']:.6f}",
    )

    print(
        "Limit:",
        f"${status['max_cost_usd']:.6f}",
    )

    print("=" * 50)


def reset_budget():

    with _lock:
        _state["calls"] = 0
        _state["input_tokens"] = 0
        _state["cached_input_tokens"] = 0
        _state["output_tokens"] = 0
        _state["cost_usd"] = 0.0
