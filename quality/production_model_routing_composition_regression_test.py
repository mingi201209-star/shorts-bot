"""Prove the production premium-writer route survives the exact production
hotfix composition, end to end.

`quality/production_model_routing_regression_test.py` proves config.py's
env-gate and Script Engine V2's writer/repair separation are each correct in
isolation. It does not prove that the real production entrypoint (main.py)
ever reaches that code path: main.py's checked-in import targets the legacy,
un-patched `content.script_generator` (no writer/repair model separation,
never reads V3_SCRIPT_WRITER_MODEL) and is rewired to
`content.script_generator_router` only by
`ci_aviation_context_signature_compat_hotfix.py` during the production
hotfix chain (see `.github/workflows/main.yml` "Apply production
hotfixes" and `.github/workflows/production_hotfix_composition_gate.yml`).

This test must run AFTER that exact hotfix chain has been applied (it is
wired into `production_hotfix_composition_gate.yml`, not into
`production_model_routing_regression.yml`, which intentionally runs
without hotfixes). It fails closed if a future hotfix or router change
silently detaches main.py from Script Engine V2, which would make the
premium writer route dead code without any other regression catching it.
"""
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
        "GITHUB_EVENT_NAME",
        "GITHUB_REF_NAME",
        "OPENAI_KEY",
        "V3_SCRIPT_MODEL",
        "V3_SCRIPT_WRITER_MODEL",
        "V3_SCRIPT_REPAIR_MODEL",
        "V3_HOOK_MODEL",
        "SCRIPT_ENGINE_MODE",
    ):
        env.pop(key, None)
    env.update(extra_env)

    code = (
        "import json\n"
        "import config\n"
        "from content.script_engine_v2_runner import WRITER_MODEL, REPAIR_MODEL\n"
        "print(json.dumps({'writer': WRITER_MODEL, 'repair': REPAIR_MODEL}))\n"
    )
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


def test_main_entrypoint_is_wired_to_script_engine_v2_router():
    """The exact failure this guards: a hotfix reverting main.py to the
    legacy per-attempt Script Generator would leave config.py's routing
    fully correct and fully unreachable, with zero test failures anywhere
    else in the suite."""
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from content.script_generator_router import" in source, (
        "main.py is not wired to the Script Engine V2 router after the "
        "production hotfix chain; V3_SCRIPT_WRITER_MODEL routing would "
        "never reach a real production call."
    )
    assert "from content.script_generator import" not in source, (
        "main.py still imports the legacy per-attempt Script Generator "
        "directly; the premium writer route only exists on the Script "
        "Engine V2 path reached through content.script_generator_router."
    )


def test_router_default_mode_resolves_to_script_engine_v2_runner():
    source = (ROOT / "content" / "script_generator_router.py").read_text(encoding="utf-8")
    assert 'mode = os.environ.get("SCRIPT_ENGINE_MODE", "v2")' in source
    assert "from content.script_engine_v2_runner import generate_script_v2" in source


def test_production_dispatch_reaches_premium_writer_end_to_end():
    observed = _probe(_production_env())
    assert observed == {"writer": "gpt-5.6-sol", "repair": "gpt-4o-mini"}, observed


def test_non_production_dispatch_never_reaches_premium_writer_end_to_end():
    observed = _probe({
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "Production Hotfix Composition Gate",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF_NAME": "fix/some-branch",
        "OPENAI_KEY": "test-key-never-used",
    })
    assert observed == {"writer": "gpt-4o-mini", "repair": "gpt-4o-mini"}, observed


def test_feature_branch_dispatch_never_reaches_premium_writer_end_to_end():
    observed = _probe(_production_env(GITHUB_REF_NAME="feat/not-main"))
    assert observed == {"writer": "gpt-4o-mini", "repair": "gpt-4o-mini"}, observed


def main():
    test_main_entrypoint_is_wired_to_script_engine_v2_router()
    test_router_default_mode_resolves_to_script_engine_v2_runner()
    test_production_dispatch_reaches_premium_writer_end_to_end()
    test_non_production_dispatch_never_reaches_premium_writer_end_to_end()
    test_feature_branch_dispatch_never_reaches_premium_writer_end_to_end()
    print(
        "PASS: exact production hotfix composition keeps the premium "
        "writer route wired end-to-end and isolated to production"
    )


if __name__ == "__main__":
    main()
