import ast
import tempfile
from pathlib import Path

import ci_script_v2_gunggeum_formal_ending_hotfix as hotfix


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

        production_counterexample = (
            "비행기 엔진이 날개 아래에 장착된 모습을 보면, 그 이유가 궁금해진다."
        )
        expected = (
            "비행기 엔진이 날개 아래에 장착된 모습을 보면, 그 이유가 궁금해집니다."
        )
        assert formalize(production_counterexample) == expected
        assert formalize("유도항력이 줄어든다.") == "유도항력이 줄어듭니다."
        assert formalize("그 이유가 궁금해집니다.") == "그 이유가 궁금해집니다."

    print("SCRIPT V2 궁금해진다 FORMAL ENDING REGRESSION: PASS")


if __name__ == "__main__":
    main()
