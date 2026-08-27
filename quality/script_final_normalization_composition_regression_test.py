import ast
import os
import re
import runpy
import shutil
import tempfile
from pathlib import Path

from quality.korean_speech_style import validate_scenes_speech_style


ROOT = Path(__file__).resolve().parents[1]
COUNTEREXAMPLE = (
    "윙렛은 날개 끝에서 발생하는 강한 소용돌이를 줄여주고, "
    "이로 인해 항력이 감소한다."
)
EXPECTED = (
    "윙렛은 날개 끝에서 발생하는 강한 소용돌이를 줄여주고, "
    "이로 인해 항력이 감소합니다."
)


def _load_production_final_boundary():
    """Apply the real production recovery hotfix, then load its final-boundary helpers."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "content").mkdir()
        shutil.copy2(ROOT / "content/script_generator.py", tmp_path / "content/script_generator.py")
        shutil.copy2(ROOT / "ci_script_validation_recovery_hotfix.py", tmp_path / "ci_script_validation_recovery_hotfix.py")

        previous = Path.cwd()
        try:
            os.chdir(tmp_path)
            runpy.run_path(str(tmp_path / "ci_script_validation_recovery_hotfix.py"), run_name="__main__")
        finally:
            os.chdir(previous)

        source = (tmp_path / "content/script_generator.py").read_text(encoding="utf-8")

    tree = ast.parse(source)
    wanted_assignments = {"_SAFE_FORMAL_ENDING_REPAIRS"}
    wanted_functions = {
        "_script_safe_formal_ending_repair",
        "_script_opening_lock_apply",
        "_script_closing_lock_apply",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected.append(node)

    namespace = {"re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<production-final-boundary>", "exec"), namespace)
    return namespace, source


def _candidate():
    return {
        "micro_narrative": {
            "hook": "비행기 날개 끝은 위로 꺾여 있습니다.",
            "core_question": "왜 이런 모양일까요?",
            "reveal": "이 구조는 날개 끝 소용돌이를 줄입니다.",
            "payoff": "그래서 비행 효율을 높이는 데 도움을 줍니다.",
        }
    }


def _payload(middle_text):
    return {
        "scenes": [
            {"text": "비행기 날개 끝은 위로 꺾여 있습니다."},
            {"text": "왜 이런 모양일까요?"},
            {"text": middle_text},
            {"text": "이 구조는 날개 끝 소용돌이를 줄입니다."},
            {"text": "그래서 비행 효율을 높이는 데 도움을 줍니다."},
        ]
    }


def _apply_final_boundary(namespace, middle_text):
    payload = _payload(middle_text)
    payload = namespace["_script_opening_lock_apply"](payload, _candidate())
    payload = namespace["_script_closing_lock_apply"](payload, _candidate())
    return payload


def _semantic_fingerprint(text):
    value = str(text).strip()
    value = re.sub(r"(감소)(?:한다|합니다)([.!…]*)$", r"\1\2", value)
    return value


def main():
    namespace, source = _load_production_final_boundary()

    # Composition guard: this test intentionally exercises the production-injected
    # generator boundary rather than #215's Script V2 runner helper directly.
    assert "generated = _script_opening_lock_apply(" in source
    assert "valid, reason = validate_script(" in source

    # CASE 1: exact production counterexample must be formalized at final boundary.
    result = _apply_final_boundary(namespace, COUNTEREXAMPLE)
    actual = result["scenes"][2]["text"]
    assert actual == EXPECTED, (actual, EXPECTED)
    valid, reason = validate_scenes_speech_style(result["scenes"])
    assert valid, reason

    # CASE 2: a later rewrite may reintroduce plain declarative style; final boundary repairs again.
    rewritten = _apply_final_boundary(namespace, "항력이 감소한다.")
    assert rewritten["scenes"][2]["text"] == "항력이 감소합니다."
    valid, reason = validate_scenes_speech_style(rewritten["scenes"])
    assert valid, reason

    # CASE 3: already-formal text is idempotent.
    formal = _apply_final_boundary(namespace, "항력이 감소합니다.")
    assert formal["scenes"][2]["text"] == "항력이 감소합니다."

    # CASE 4: question contract remains untouched.
    repair = namespace["_script_safe_formal_ending_repair"]
    assert repair("왜 감소할까요?") == "왜 감소할까요?"

    # CASE 5: non-terminal occurrence must not be rewritten.
    middle = "이 장치는 한다는 표현을 설명합니다."
    assert repair(middle) == middle

    # CASE 6: semantic payload is unchanged apart from formal ending.
    assert _semantic_fingerprint(COUNTEREXAMPLE) == _semantic_fingerprint(EXPECTED)

    # CASE 7: representative existing repairs remain intact.
    expected = {
        "효율이 줄어든다.": "효율이 줄어듭니다.",
        "효율이 늘어난다.": "효율이 늘어납니다.",
        "형태가 달라진다.": "형태가 달라집니다.",
        "상태가 좋아진다.": "상태가 좋아집니다.",
        "과정이 이루어진다.": "과정이 이루어집니다.",
        "사실이 알려진다.": "사실이 알려집니다.",
        "이 구조가 도와준다.": "이 구조가 도와줍니다.",
        "이 구조는 작동하지 않는다.": "이 구조는 작동하지 않습니다.",
    }
    for before, after in expected.items():
        repaired = repair(before)
        assert repaired == after, (before, repaired, after)

    print("✅ Script final-normalization production composition regression PASS")


if __name__ == "__main__":
    main()
