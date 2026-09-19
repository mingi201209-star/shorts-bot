# quality/budget_guard.py

import os
import threading


DEFAULT_MAX_CALLS = 12
DEFAULT_MAX_COST_USD = 0.05


MODEL_PRICES = {
    "gpt-4o-mini": {
        "input": 0.15 / 1_000_000,
        "output": 0.60 / 1_000_000,
        "cached_input": 0.075 / 1_000_000,
    },
    "gpt-5.6-sol": {
        "input": 4.00 / 1_000_000,
        "output": 20.00 / 1_000_000,
        "cached_input": 0.40 / 1_000_000,
        "cache_write": 5.00 / 1_000_000,
    },
}


_lock = threading.Lock()

_state = {
    "calls": 0,
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "cache_write_tokens": 0,
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

    return MODEL_PRICES[
        model
    ]


def authorize_call(
    model,
):

    get_price(model)

    limits = get_limits()

    with _lock:

        if (
            _state["calls"]
            >= limits["max_calls"]
        ):

            raise BudgetExceededError(
                "V3 API 호출 횟수 한도 초과: "
                f"{_state['calls']}/"
                f"{limits['max_calls']}"
            )

        if (
            _state["cost_usd"]
            >= limits["max_cost_usd"]
        ):

            raise BudgetExceededError(
                "V3 API 비용 한도 초과: "
                f"${_state['cost_usd']:.6f}/"
                f"${limits['max_cost_usd']:.6f}"
            )

        _state["calls"] += 1
        call_number = _state["calls"]

    print(
        "[API_MODEL_ROUTE] "
        f"call={call_number} model={model}"
    )

    return call_number


def record_usage(
    model,
    response,
):

    price = get_price(
        model
    )

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
    cache_write_tokens = 0

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

        cache_write_tokens = int(
            getattr(
                details,
                "cache_write_tokens",
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

    cache_write_tokens = max(
        0,
        min(
            cache_write_tokens,
            input_tokens - cached_tokens,
        ),
    )

    uncached_tokens = (
        input_tokens
        - cached_tokens
        - cache_write_tokens
    )

    cache_write_price = price.get(
        "cache_write",
        price["input"],
    )

    cost = (
        uncached_tokens
        * price["input"]

        + cached_tokens
        * price["cached_input"]

        + cache_write_tokens
        * cache_write_price

        + output_tokens
        * price["output"]
    )

    with _lock:

        _state[
            "input_tokens"
        ] += input_tokens

        _state[
            "cached_input_tokens"
        ] += cached_tokens

        _state[
            "cache_write_tokens"
        ] += cache_write_tokens

        _state[
            "output_tokens"
        ] += output_tokens

        _state[
            "cost_usd"
        ] += cost

        over_budget = (
            _state["cost_usd"]
            > get_limits()[
                "max_cost_usd"
            ]
        )

    return {
        "input_tokens":
            input_tokens,

        "cached_input_tokens":
            cached_tokens,

        "cache_write_tokens":
            cache_write_tokens,

        "output_tokens":
            output_tokens,

        "cost_usd":
            cost,

        "over_budget":
            over_budget,
    }


def get_budget_status():

    with _lock:
        state = dict(
            _state
        )

    state.update(
        get_limits()
    )

    return state


def print_budget_status():

    status = (
        get_budget_status()
    )

    print("")
    print("=" * 52)
    print("💰 V3.2 API BUDGET")
    print("=" * 52)

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
        status[
            "cached_input_tokens"
        ],
    )

    print(
        "Cache writes:",
        status[
            "cache_write_tokens"
        ],
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

    print("=" * 52)


DEFAULT_REWRITE_RESERVE_CALLS = 5
DEFAULT_REWRITE_RESERVE_COST_USD = 0.005


def has_budget_for_rewrite(
    reserve_calls=DEFAULT_REWRITE_RESERVE_CALLS,
    reserve_cost_usd=DEFAULT_REWRITE_RESERVE_COST_USD,
):
    """True if starting one more rewrite-recovery cycle (a rewrite call plus
    at least one recheck call) would still leave a small safety reserve of
    calls/cost, so a run that must fail can still fail cleanly with
    diagnostics instead of dying mid-call when the hard budget cap is hit.

    This never grants extra budget and never bypasses ``authorize_call``'s
    own hard limits -- it only decides, on the caller's side, whether it is
    worth *attempting* another rewrite cycle at all. If the reserve is not
    available, the caller should skip the rewrite and discard the candidate
    exactly as it would if the rewrite bound had been reached.
    """

    status = get_budget_status()

    calls_left = status["max_calls"] - status["calls"]
    cost_left = status["max_cost_usd"] - status["cost_usd"]

    return calls_left > reserve_calls and cost_left > reserve_cost_usd


def reset_budget():

    with _lock:

        _state["calls"] = 0

        _state[
            "input_tokens"
        ] = 0

        _state[
            "cached_input_tokens"
        ] = 0

        _state[
            "cache_write_tokens"
        ] = 0

        _state[
            "output_tokens"
        ] = 0

        _state[
            "cost_usd"
        ] = 0.0
