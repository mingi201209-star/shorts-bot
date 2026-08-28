import ast
import os
import re
import runpy
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.korean_speech_style import validate_korean_speech_text

COUNTEREXAMPLE = (
    "날개 끝이 위로 꺾여 있으면 날개 위아래의 압력 차가 소용돌이를 줄여주고, "
    "이로 인해 유도항력이 감소한다. 다음 단계에서는 효율이 높아집니다."
)
EXPECTED = (
    "날개 끝이 위로 꺾여 있으면 날개 위아래의 압력 차가 소용돌이를 줄여주고, "
    "이로 인해 유도항력이 감소합니다. 다음 단계에서는 효율이 높아집니다."
)


def _load_production_v2_formalizer():
    """Install the production V2 ending hotfix, then load the composed formalizer."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "content").mkdir()
        shutil.copy2(ROOT / "content/script_engine_v2_runner.py", tmp_path / "content/script_engine_v2_runner.py")
        shutil.copy2(ROOT / "content/script_engine_v2.py", tmp_path / "content/script_engine_v2.py")
        shutil.copy2(ROOT / "ci_script_v2_gunggeum_formal_ending_hotfix.py", tmp_path / "ci_script_v2_gunggeum_formal_ending_hotfix.py")

        previous = Path.cwd()
        try:
            os.chdir(tmp_path)
            runpy.run_path(str(tmp_path / "ci_script_v2_gunggeum_formal_ending_hotfix.py"), run_name="__main__")
        finally:
            os.chdir(previous)

        source = (tmp_path / "content/script_engine_v2_runner.py").read_text(encoding="utf-8")

    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "_FORMAL_ENDING_REPAIRS" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_formalize_common_ending":
            selected.append(node)

    namespace = {"re": re, "Any": object}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<production-v2-formalizer>", "exec"), namespace)
    return namespace["_formalize_common_ending"], source


def _semantic_fingerprint(text):
    value = str(text).strip()
    value = re.sub(r"감소(?:한다|합니다)", "감소", value)
    return value


def main():
    formalize, source = _load_production_v2_formalizer()

    # Production and strict validation disagree today: V2 formalizes only the
    # end of the whole scene, while the speech validator checks every sentence.
    assert "def _formalize_common_ending" in source
    assert '한다(?=[.!…]*$)' in source

    actual = formalize(COUNTEREXAMPLE)
    assert actual == EXPECTED, (actual, EXPECTED)
    valid, reason = validate_korean_speech_text(actual, allow_nominal=False)
    assert valid, reason

    # Exact production sentence also remains supported as a one-sentence scene.
    exact = "이로 인해 유도항력이 감소한다."
    assert formalize(exact) == "이로 인해 유도항력이 감소합니다."

    # Already-formal narration is idempotent.
    formal = "유도항력이 감소합니다. 다음 단계도 정상입니다."
    assert formalize(formal) == formal

    # Questions keep their existing contract and are never coerced to statements.
    question = "왜 유도항력이 감소할까요?"
    assert formalize(question) == question

    # Non-terminal lexical occurrence is untouched.
    middle_token = "이 설명은 한다는 표현을 예로 듭니다."
    assert formalize(middle_token) == middle_token

    assert _semantic_fingerprint(COUNTEREXAMPLE) == _semantic_fingerprint(EXPECTED)

    print("✅ Script V2 sentence-ending production composition regression PASS")


if __name__ == "__main__":
    main()
