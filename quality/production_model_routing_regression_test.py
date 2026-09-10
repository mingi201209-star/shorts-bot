import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def _probe(extra_env):
    env = os.environ.copy()
    for key in (
        "GITHUB_ACTIONS",
        "GITHUB_WORKFLOW",
        "GITHUB_EVENT_NAME",
        "GITHUB_REF_NAME",
        "OPENAI_KEY",
        "V3_SCRIPT_MODEL",
        "V3_SCRIPT_WRITER_MODEL",
        "V3_SCRIPT_REPAIR_MODEL",
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
    "writer": os.environ.get("V3_SCRIPT_WRITER_MODEL"),
    "repair": os.environ.get("V3_SCRIPT_REPAIR_MODEL"),
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


def _production_env(**overrides):
    env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "Shorts Generator",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF_NAME": "main",
        "OPENAI_KEY": "test-key-never-used",
    }
    env.update(overrides)
    return env


def _empty_route():
    return {
        "script": None,
        "writer": None,
        "repair": None,
        "hook": None,
    }


def test_non_production_keeps_existing_defaults():
    observed = _probe({
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "Production Model Routing Regression",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF_NAME": "feat/test",
        "OPENAI_KEY": "test-key-never-used",
    })
    assert observed == _empty_route(), observed


def test_feature_branch_dispatch_cannot_activate_premium_model():
    observed = _probe(_production_env(GITHUB_REF_NAME="feat/not-main"))
    assert observed == _empty_route(), observed


def test_hotfix_or_compile_stage_without_api_key_cannot_activate_premium_model():
    env = _production_env()
    env.pop("OPENAI_KEY")
    observed = _probe(env)
    assert observed == _empty_route(), observed


def test_authoritative_production_routes_initial_writer_only():
    observed = _probe(_production_env())
    assert observed == {
        "script": None,
        "writer": "gpt-5.6-sol",
        "repair": None,
        "hook": "gpt-4o-mini",
    }, observed


def test_explicit_operator_override_wins():
    observed = _probe(_production_env(
        V3_SCRIPT_MODEL="gpt-4o-mini",
        V3_SCRIPT_WRITER_MODEL="gpt-4o-mini",
        V3_SCRIPT_REPAIR_MODEL="gpt-4o-mini",
        V3_HOOK_MODEL="gpt-4o-mini",
    ))
    assert observed == {
        "script": "gpt-4o-mini",
        "writer": "gpt-4o-mini",
        "repair": "gpt-4o-mini",
        "hook": "gpt-4o-mini",
    }, observed


def test_script_v2_runner_keeps_writer_and_repair_models_separate():
    source = (ROOT / "content" / "script_engine_v2_runner.py").read_text(encoding="utf-8")
    required = (
        'WRITER_MODEL = os.environ.get("V3_SCRIPT_WRITER_MODEL", MODEL)',
        'REPAIR_MODEL = os.environ.get("V3_SCRIPT_REPAIR_MODEL", MODEL)',
        'if mode == "writer":\n        return WRITER_MODEL',
        'if mode == "local_repair":\n        return REPAIR_MODEL',
        'model = _model_for_mode(mode)',
        'record_usage(model, response)',
        'return {"reasoning_effort": "none"}',
    )
    for marker in required:
        assert marker in source, marker


def test_sol_price_and_cost_limit_are_registered_without_relaxation():
    from quality.budget_guard import get_limits, get_price

    price = get_price("gpt-5.6-sol")
    assert price["input"] == 4.00 / 1_000_000
    assert price["cached_input"] == 0.40 / 1_000_000
    assert price["cache_write"] == 5.00 / 1_000_000
    assert price["output"] == 20.00 / 1_000_000

    old = os.environ.pop("V3_MAX_COST_USD", None)
    try:
        assert get_limits()["max_cost_usd"] == 0.05
    finally:
        if old is not None:
            os.environ["V3_MAX_COST_USD"] = old


def test_authorize_call_logs_exact_resolved_model():
    from quality.budget_guard import authorize_call, reset_budget

    reset_budget()
    stdout = StringIO()
    with redirect_stdout(stdout):
        call_number = authorize_call("gpt-5.6-sol")

    assert call_number == 1
    assert stdout.getvalue().strip() == "[API_MODEL_ROUTE] call=1 model=gpt-5.6-sol"


def test_sol_cache_write_usage_is_billed_at_1_25x_input():
    from quality.budget_guard import record_usage, reset_budget

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=10,
            prompt_tokens_details=SimpleNamespace(
                cached_tokens=20,
                cache_write_tokens=30,
            ),
        )
    )

    reset_budget()
    usage = record_usage("gpt-5.6-sol", response)

    expected = (
        50 * (4.00 / 1_000_000)
        + 20 * (0.40 / 1_000_000)
        + 30 * (5.00 / 1_000_000)
        + 10 * (20.00 / 1_000_000)
    )
    assert abs(usage["cost_usd"] - expected) < 1e-12, usage
    assert usage["cache_write_tokens"] == 30, usage


def main():
    test_non_production_keeps_existing_defaults()
    test_feature_branch_dispatch_cannot_activate_premium_model()
    test_hotfix_or_compile_stage_without_api_key_cannot_activate_premium_model()
    test_authoritative_production_routes_initial_writer_only()
    test_explicit_operator_override_wins()
    test_script_v2_runner_keeps_writer_and_repair_models_separate()
    test_sol_price_and_cost_limit_are_registered_without_relaxation()
    test_authorize_call_logs_exact_resolved_model()
    test_sol_cache_write_usage_is_billed_at_1_25x_input()
    print("PASS: premium model is production-only, writer-only, observable, and budget accounting remains bounded")


if __name__ == "__main__":
    main()
