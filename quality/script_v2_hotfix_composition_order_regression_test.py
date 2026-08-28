import ast
import os
import re
import runpy
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COUNTEREXAMPLE = (
    "날개 끝 소용돌이가 줄어들면서 이로 인해 유도항력이 감소한다. "
    "다음 단계에서는 효율이 높아집니다."
)
EXPECTED = (
    "날개 끝 소용돌이가 줄어들면서 이로 인해 유도항력이 감소합니다. "
    "다음 단계에서는 효율이 높아집니다."
)


def _install_production_script_v2_chain():
    """Reproduce the production order that failed in Run 33164209358."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "content").mkdir()
        for relative in (
            "content/script_engine_v2_runner.py",
            "content/script_engine_v2.py",
            "ci_script_v2_visual_goal_hotfix.py",
            "ci_script_v2_gunggeum_formal_ending_hotfix.py",
        ):
            source = ROOT / relative
            target = tmp_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        previous = Path.cwd()
        try:
            os.chdir(tmp_path)
            visual = runpy.run_path(str(tmp_path / "ci_script_v2_visual_goal_hotfix.py"), run_name="visual_goal_hotfix")
            visual["_apply_script_v2_formal_ending_repair"]()
            ending = runpy.run_path(str(tmp_path / "ci_script_v2_gunggeum_formal_ending_hotfix.py"), run_name="ending_hotfix")
            ending["_patch_runner"]()
        finally:
            os.chdir(previous)

        runner_source = (tmp_path / "content/script_engine_v2_runner.py").read_text(encoding="utf-8")

    return runner_source


def _load_formalizer(source):
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
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<composed-runner>", "exec"), namespace)
    return namespace["_formalize_common_ending"]


def main():
    source = _install_production_script_v2_chain()
    assert "SCRIPT_V2_SENTENCE_GRANULAR_FORMAL_ENDING_V1" in source
    formalize = _load_formalizer(source)
    assert formalize(COUNTEREXAMPLE) == EXPECTED
    assert formalize("왜 유도항력이 감소할까요?") == "왜 유도항력이 감소할까요?"
    assert formalize("유도항력이 감소합니다.") == "유도항력이 감소합니다."
    print("✅ Script V2 production hotfix composition order regression PASS")


if __name__ == "__main__":
    main()
