"""Run 34685288234 fixed-topic Candidate opening recovery regression.

Authority Run #527 failed before Writer/render because all seven fixed-topic
Candidate attempts produced a Hook that restated the Core Question.  The fix
must preserve the existing validator and bounded attempts, spend zero model/API
calls, and use only Candidate-owned text.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


# Running this file as `python quality/...py` makes `quality/` sys.path[0].
# Add the repository root explicitly before importing the existing Run #526
# scratch-composition helper; this changes only the test harness, not runtime.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.run_34682392892_human_visual_progression_regression_test import (
    _prepare_repo,
)


FIXED_TOPIC = "비행기 창문 모서리는 왜 둥글까"


def _fresh_import(repo: Path, module_name: str):
    """Load the exact scratch-composed .py file, never the checkout copy."""
    for name in list(sys.modules):
        if name == module_name or name.startswith(module_name + "."):
            del sys.modules[name]
        if module_name.startswith("content.") and (name == "content" or name.startswith("content.")):
            del sys.modules[name]

    module_path = repo.joinpath(*module_name.split(".")).with_suffix(".py")
    assert module_path.exists(), module_path
    sys.path.insert(0, str(repo))
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(repo))


def _candidate():
    return {
        "topic": FIXED_TOPIC,
        "angle": "둥근 창문 모서리가 응력 집중을 줄이는 구조",
        "core_question": "비행기 창문 모서리는 왜 둥글게 설계될까요?",
        "micro_narrative": {
            "hook": "비행기 창문 모서리는 둥글게 설계됩니다.",
            "core_question": "비행기 창문 모서리는 왜 둥글게 설계될까요?",
            "reveal": "둥근 모서리는 응력 집중을 줄입니다.",
            "payoff": "각진 창문 모서리의 응력 집중은 재료 피로와 파열 위험을 키웠습니다.",
        },
        "fact_check_focus": ["각진 창문 모서리의 응력 집중과 피로 위험"],
        "visual_proof": ["각진 모서리와 둥근 모서리의 응력 분포 비교"],
        "selection_reason": "익숙한 창문 모양을 구조적 원인으로 다시 보게 합니다.",
    }


def main():
    repo = _prepare_repo()
    old_topic = os.environ.get("SHORTS_TOPIC")
    try:
        result = subprocess.run(
            [sys.executable, "ci_run_34685288234_fixed_topic_candidate_opening_hotfix.py"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr

        explorer_source = (repo / "content/candidate_explorer.py").read_text(encoding="utf-8")
        assert "RUN_34685288234_FIXED_TOPIC_CANDIDATE_OPENING_RECOVERY_V1" in explorer_source
        assert "def _hook_restates_question(" in explorer_source

        explorer = _fresh_import(repo, "content.candidate_explorer")
        validation = _fresh_import(repo, "content.script_engine_v2_validation")
        recovery = _fresh_import(repo, "content.fixed_topic_candidate_opening_recovery")

        original = _candidate()
        old_hook = original["micro_narrative"]["hook"]
        question = original["core_question"]
        assert explorer._hook_restates_question(old_hook, question) is True

        recovered, changed, source = recovery.recover_fixed_topic_candidate_hook(
            original,
            fixed_topic=FIXED_TOPIC,
            prefix="winner",
            restates_question=explorer._hook_restates_question,
            opening_violation_reason=validation.opening_human_contract_violation_reason,
        )
        assert changed is True
        assert source == "payoff"
        new_hook = recovered["micro_narrative"]["hook"]
        assert new_hook == original["micro_narrative"]["payoff"]
        assert explorer._hook_restates_question(new_hook, question) is False
        assert validation.opening_human_contract_violation_reason(new_hook, question) == ""
        print("CASE A Run #527 Hook/Core Question repetition recovered from Candidate-owned payoff: PASS")

        # Only Hook may change.  All authority-bearing Candidate fields/body
        # remain byte-for-byte/deep-equal to the generated Candidate.
        expected = _candidate()
        expected["micro_narrative"]["hook"] = new_hook
        assert recovered == expected
        print("CASE B recovery mutates only Winner micro_narrative.hook: PASS")

        untouched, changed, reason = recovery.recover_fixed_topic_candidate_hook(
            original,
            fixed_topic="",
            prefix="winner",
            restates_question=explorer._hook_restates_question,
            opening_violation_reason=validation.opening_human_contract_violation_reason,
        )
        assert changed is False and untouched == original
        assert reason == "not_fixed_topic_winner"

        runner, changed, _ = recovery.recover_fixed_topic_candidate_hook(
            original,
            fixed_topic=FIXED_TOPIC,
            prefix="runner_up",
            restates_question=explorer._hook_restates_question,
            opening_violation_reason=validation.opening_human_contract_violation_reason,
        )
        assert changed is False and runner == original
        print("CASE C automatic/general + runner-up behavior unchanged: PASS")

        unsafe = _candidate()
        unsafe["micro_narrative"]["payoff"] = unsafe["core_question"]
        unsafe["micro_narrative"]["reveal"] = unsafe["core_question"]
        blocked, changed, reason = recovery.recover_fixed_topic_candidate_hook(
            unsafe,
            fixed_topic=FIXED_TOPIC,
            prefix="winner",
            restates_question=explorer._hook_restates_question,
            opening_violation_reason=validation.opening_human_contract_violation_reason,
        )
        assert changed is False and blocked == unsafe
        assert reason == "no_safe_candidate_owned_progression"
        print("CASE D no safe Candidate-owned beat => fail closed under original validator: PASS")

        helper_source = (repo / "content/fixed_topic_candidate_opening_recovery.py").read_text(encoding="utf-8")
        installer_source = (repo / "ci_run_34685288234_fixed_topic_candidate_opening_hotfix.py").read_text(encoding="utf-8")
        combined = helper_source + installer_source
        for forbidden in (
            "V3_MAX_COST_USD =",
            "V3_MAX_API_CALLS =",
            "MAX_TOPIC_REGENERATIONS =",
            "MAX_SCRIPT_ATTEMPTS =",
            "HOOK_MIN_SCORE =",
            "chat.completions.create(",
            "responses.create(",
            "generate_script(",
            "authorize_call(",
        ):
            assert forbidden not in combined, forbidden
        print("CASE E budgets/floors/retries/models/API calls unchanged: PASS")

        print("RUN 34685288234 FIXED TOPIC CANDIDATE OPENING REGRESSION: PASS")
    finally:
        if old_topic is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = old_topic
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
