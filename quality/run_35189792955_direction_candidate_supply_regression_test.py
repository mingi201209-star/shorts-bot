"""Standalone regression: compose production installers only in a temporary copy."""

import ast
import os
from pathlib import Path
import shutil
import tempfile

from candidate_recovery_production_chain_regression_test import (
    FINAL_CONTEXT_COMPAT,
    GROWTH_LINK,
    PRODUCTION_PREFIX,
    ROOT,
    TARGET,
    run,
)


# Exact terminal reason captured from authoritative production Run 35189792955.
DIRECTION_REASON = (
    "탐색 방향인 '유명한 역사적 대상의 잘 알려지지 않은 기능'에 적합한 구체적인 "
    "후보가 발견되지 않았습니다. 모든 후보가 예상 가능한 결론에 머물러 있거나, "
    "질문과 Reveal이 지나치게 넓거나 일반적이어서 시청자의 호기심을 충분히 "
    "자극하지 못했습니다."
)


def check_composed_runtime():
    from run_35065228877_bounded_supply_authority_regression_test import (
        _load_explorer,
        main as check_existing_contracts,
    )

    os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
    os.environ["SHORTS_TOPIC"] = ""
    explorer = _load_explorer()
    recognize = explorer._candidate_supply_reason_is_zero_usable
    result = {"status": "REGENERATE", "reason": DIRECTION_REASON}
    os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "0"
    assert recognize(result) is False
    os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
    assert recognize(result) is True
    editorial = {
        "status": "REGENERATE",
        "reason": "탐색 방향인 생활 기술의 구체적인 후보는 질문이 넓고 예상 가능합니다.",
    }
    assert recognize(editorial) is False
    for fragment in ("탐색 방향인", "구체적인 후보", "발견되지 않았"):
        assert recognize({**result, "reason": DIRECTION_REASON.replace(fragment, "")}) is False
    assert recognize({**result, "status": "SELECTED"}) is False

    # Scoped callers must retain the previous recognizer, even before the final
    # attempt; exercise both existing shortage and newly recognized wording.
    for scope, topic in (("aviation", ""), ("", "비행기 창문은 왜 둥글까")):
        os.environ["SHORTS_CANDIDATE_SCOPE"] = scope
        os.environ["SHORTS_TOPIC"] = topic
        for final in ("0", "1"):
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = final
            for reason in (DIRECTION_REASON, "구체적인 후보가 부족합니다."):
                scoped = {**result, "reason": reason}
                assert recognize(scoped) == explorer._run_35065228877_previous_zero_supply_reason(scoped)
    os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
    os.environ["SHORTS_TOPIC"] = ""

    # Execute the actual composed one-call guard with deterministic provider
    # stubs. Repeated terminal shortages must not add retries or recovery calls.
    source = (ROOT / "content/candidate_explorer.py").read_text(encoding="utf-8")
    guards = [
        node for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
        and node.name == "explore_candidates"
        and any(
            isinstance(child, ast.Global)
            and "_candidate_supply_recovery_used" in child.names
            for child in ast.walk(node)
        )
    ]
    assert len(guards) == 1
    calls = []

    def recovery(*args, **kwargs):
        calls.append(kwargs["original_reason"])
        return result

    namespace = {
        "MODEL": "offline-test",
        "_candidate_supply_recovery_used": False,
        "_candidate_supply_reason_is_zero_usable": recognize,
        "_original_explore_candidates_before_supply_recovery": lambda *a, **k: result,
        "_run_candidate_supply_recovery": recovery,
    }
    exec(compile(ast.Module(body=guards, type_ignores=[]), "<composed-guard>", "exec"), namespace)
    os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "0"
    namespace["explore_candidates"]({})
    assert calls == []
    os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = "1"
    for _ in range(3):
        assert namespace["explore_candidates"]({}) == result
    assert calls == [DIRECTION_REASON]

    # Existing coverage verifies scope/context behavior and unchanged
    # authorization, retry and cost boundaries against the composed checkout.
    check_existing_contracts()
    print("PASS: Run 35189792955 signal is final-only; scoped and bounded recovery preserved")


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        work = Path(temp_dir)
        shutil.copytree(ROOT, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        for script in (*PRODUCTION_PREFIX, TARGET, GROWTH_LINK,
                       "ci_run_35065228877_bounded_supply_authority_hotfix.py",
                       FINAL_CONTEXT_COMPAT):
            run(script, work)
        run(str(Path(__file__).relative_to(ROOT)), work)
    print("PASS: standalone Run 35189792955 regression in temporary production composition")


if __name__ == "__main__":
    # The temporary checkout has the installed marker; the clean checkout does
    # not. Subprocess imports therefore always resolve the composed runtime.
    if "# RUN_35065228877_BOUNDED_SUPPLY_AUTHORITY_V1" in (
        ROOT / "content/candidate_explorer.py"
    ).read_text(encoding="utf-8"):
        check_composed_runtime()
    else:
        main()
