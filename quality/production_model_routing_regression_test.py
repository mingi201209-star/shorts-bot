import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _probe(extra_env):
    env = os.environ.copy()
    for key in (
        "GITHUB_ACTIONS",
        "GITHUB_WORKFLOW",
        "V3_SCRIPT_MODEL",
        "V3_HOOK_MODEL",
    ):
        env.pop(key, None)
    env.update(extra_env)

    code = r'''
import json
import os
import config
print(json.dumps({
    "script": os.environ.get("V3_SCRIPT_MODEL"),
    "hook": os.environ.get("V3_HOOK_MODEL"),
}))
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout.strip())


def test_non_production_keeps_existing_defaults():
    observed = _probe({
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "Production Model Routing Regression",
    })
    assert observed == {
        "script": None,
        "hook": None,
    }, observed


def test_authoritative_production_routes_writer_only():
    observed = _probe({
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "Shorts Generator",
    })
    assert observed == {
        "script": "gpt-5.6-sol",
        "hook": "gpt-4o-mini",
    }, observed


def test_explicit_operator_override_wins():
    observed = _probe({
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "Shorts Generator",
        "V3_SCRIPT_MODEL": "gpt-4o-mini",
        "V3_HOOK_MODEL": "gpt-4o-mini",
    })
    assert observed == {
        "script": "gpt-4o-mini",
        "hook": "gpt-4o-mini",
    }, observed


def test_sol_price_and_cost_limit_are_registered_without_relaxation():
    from quality.budget_guard import get_limits, get_price

    price = get_price("gpt-5.6-sol")
    assert price["input"] == 4.00 / 1_000_000
    assert price["cached_input"] == 0.40 / 1_000_000
    assert price["output"] == 20.00 / 1_000_000

    old = os.environ.pop("V3_MAX_COST_USD", None)
    try:
        assert get_limits()["max_cost_usd"] == 0.05
    finally:
        if old is not None:
            os.environ["V3_MAX_COST_USD"] = old


def main():
    test_non_production_keeps_existing_defaults()
    test_authoritative_production_routes_writer_only()
    test_explicit_operator_override_wins()
    test_sol_price_and_cost_limit_are_registered_without_relaxation()
    print("PASS: production premium writer routing is isolated and budget cap is unchanged")


if __name__ == "__main__":
    main()
