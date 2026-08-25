import ast
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_script_v2_gunggeum_formal_ending_hotfix as hotfix
from content.script_generator_router import _observable_hook_from_candidate


def _load_formalizer(source: str):
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "_FORMAL_ENDING_REPAIRS" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_formalize_common_ending":
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {}
    exec("import re\nfrom typing import Any", namespace)
    exec(compile(module, "<formalizer>", "exec"), namespace)
    return namespace["_formalize_common_ending"]


def main():
    production_candidate = {
        "topic": "비행기 바퀴는 착륙 전에 미리 돌지 않는다",
        "micro_narrative": {
            "hook": "왜 비행기 바퀴는 착륙 전에 미리 돌지 않을까?"
        },
    }
    normalized_candidate = _observable_hook_from_candidate(production_candidate)
    assert normalized_candidate["micro_narrative"]["hook"] == (
        "비행기 바퀴는 착륙 전에 미리 돌지 않습니다."
    )

    runner_source = Path("content/script_engine_v2_runner.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_runner = Path(tmpdir) / "script_engine_v2_runner.py"
        temp_runner.write_text(runner_source, encoding="utf-8")
        original_path = hotfix.RUNNER_PATH
        try:
            hotfix.RUNNER_PATH = temp_runner
            hotfix.main()
            hotfix.main()
        finally:
            hotfix.RUNNER_PATH = original_path

        patched = temp_runner.read_text(encoding="utf-8")
        assert patched.count(hotfix.MARKER) == 1, "hotfix must be idempotent"
        formalize = _load_formalizer(patched)

        first_counterexample = (
            "비행기 엔진이 날개 아래에 장착된 모습을 보면, 그 이유가 궁금해진다."
        )
        first_expected = (
            "비행기 엔진이 날개 아래에 장착된 모습을 보면, 그 이유가 궁금해집니다."
        )
        assert formalize(first_counterexample) == first_expected

        second_counterexample = (
            "이로 인해 비행기가 더 안전하게 비행할 수 있고, 엔진 고장 시에도 비행 제어가 용이해진다."
        )
        second_expected = (
            "이로 인해 비행기가 더 안전하게 비행할 수 있고, 엔진 고장 시에도 비행 제어가 용이해집니다."
        )
        assert formalize(second_counterexample) == second_expected

        fragment_counterexample = "비행 중 날개가 휘어지는 모습, 많은 사람들이 보지 못한 사실."
        fragment_expected = "비행 중 날개가 휘어지는 모습, 많은 사람들이 보지 못한 사실입니다."
        assert formalize(fragment_counterexample) == fragment_expected

        latest_production_counterexample = (
            "그 결과, 비행기의 연료 효율이 향상되고, 비행 중 안정성이 증가하여 안전한 비행이 가능해진다."
        )
        latest_expected = (
            "그 결과, 비행기의 연료 효율이 향상되고, 비행 중 안정성이 증가하여 안전한 비행이 가능해집니다."
        )
        assert formalize(latest_production_counterexample) == latest_expected

        wing_production_counterexample = (
            "날개가 휘어지면 공기 흐름이 최적화되고, 그로 인해 항력 감소가 이루어진다."
        )
        wing_expected = (
            "날개가 휘어지면 공기 흐름이 최적화되고, 그로 인해 항력 감소가 이루어집니다."
        )
        assert formalize(wing_production_counterexample) == wing_expected

        question_counterexample = (
            "비행기 날개가 휘어질 때, 공기 흐름에 미치는 영향은 무엇인지 설명해 주실 수 있나요?"
        )
        question_expected = (
            "비행기 날개가 휘어질 때, 공기 흐름에 미치는 영향은 무엇인지 설명해 주실 수 있습니까?"
        )
        assert formalize(question_counterexample) == question_expected
        assert formalize("유도항력이 줄어든다.") == "유도항력이 줄어듭니다."
        assert formalize("그 이유가 궁금해집니다.") == "그 이유가 궁금해집니다."

    print("SCRIPT V2 OBSERVED FORMAL ENDING REGRESSION: PASS")


if __name__ == "__main__":
    main()
