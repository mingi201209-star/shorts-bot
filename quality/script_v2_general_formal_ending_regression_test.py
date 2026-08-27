import ast
import re
import tempfile
from pathlib import Path

import ci_script_v2_gunggeum_formal_ending_hotfix as hotfix
from quality.korean_speech_style import validate_korean_speech_text


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
    namespace = {"re": re, "Any": object}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<formalizer>", "exec"), namespace)
    return namespace["_formalize_common_ending"]


def _semantic_fingerprint(text: str) -> str:
    value = str(text).strip()
    value = re.sub(r"합니다(?=[.!…]*$)", "한다", value)
    return value


def main():
    runner_source = Path("content/script_engine_v2_runner.py").read_text(encoding="utf-8")
    engine_source = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_runner = Path(tmpdir) / "script_engine_v2_runner.py"
        temp_engine = Path(tmpdir) / "script_engine_v2.py"
        temp_runner.write_text(runner_source, encoding="utf-8")
        temp_engine.write_text(engine_source, encoding="utf-8")
        old_runner, old_engine = hotfix.RUNNER_PATH, hotfix.ENGINE_PATH
        try:
            hotfix.RUNNER_PATH, hotfix.ENGINE_PATH = temp_runner, temp_engine
            hotfix.main()
            hotfix.main()
        finally:
            hotfix.RUNNER_PATH, hotfix.ENGINE_PATH = old_runner, old_engine

        patched = temp_runner.read_text(encoding="utf-8")
        assert patched.count(hotfix.GENERAL_DECLARATIVE_MARKER) == 1
        formalize = _load_formalizer(patched)

        actual = "윙렛은 날개 끝에서 발생하는 강한 소용돌이를 줄여주고, 이로 인해 항력이 감소한다."
        expected = "윙렛은 날개 끝에서 발생하는 강한 소용돌이를 줄여주고, 이로 인해 항력이 감소합니다."
        assert formalize(actual) == expected
        assert validate_korean_speech_text(expected)[0]
        assert _semantic_fingerprint(actual) == _semantic_fingerprint(expected)

        cases = {
            "효율이 증가한다.": "효율이 증가합니다.",
            "소용돌이가 발생한다.": "소용돌이가 발생합니다.",
            "이 구조를 사용한다.": "이 구조를 사용합니다.",
            "효율이 증가합니다.": "효율이 증가합니다.",
            "효율이 증가하지 않습니다.": "효율이 증가하지 않습니다.",
            "왜 효율이 증가할까요?": "왜 효율이 증가할까요?",
            "한다는 표현이 문장 중간에 있지만 종결은 정상입니다.": "한다는 표현이 문장 중간에 있지만 종결은 정상입니다.",
            "왜냐하면 항력이 감소하기 때문입니다.": "왜냐하면 항력이 감소하기 때문입니다.",
            "항력이 감소하지 않습니다.": "항력이 감소하지 않습니다.",
            "항력을 감소시키는 구조입니다.": "항력을 감소시키는 구조입니다.",
            "항력이 감소할 수 있습니다.": "항력이 감소할 수 있습니다.",
        }
        for before, after in cases.items():
            assert formalize(before) == after, (before, formalize(before), after)

        for before in ("효율이 증가한다.", "소용돌이가 발생한다.", "이 구조를 사용한다."):
            repaired = formalize(before)
            assert validate_korean_speech_text(repaired)[0], repaired
            assert _semantic_fingerprint(before) == _semantic_fingerprint(repaired)

    print("SCRIPT V2 GENERAL FORMAL ENDING REGRESSION: PASS")


if __name__ == "__main__":
    main()
