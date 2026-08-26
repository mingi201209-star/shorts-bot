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


def _load_question_hook_converter(source: str):
    tree = ast.parse(source)
    selected = []
    wanted_assignments = {"_QUESTION_HOOK_REPAIRS", "_TOPIC_OBSERVATION_REPAIRS"}
    wanted_functions = {"_text", "_topic_to_observation", "_question_hook_to_observation"}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {}
    exec("import re\nfrom typing import Any", namespace)
    exec(compile(module, "<question-hook-converter>", "exec"), namespace)
    return namespace["_question_hook_to_observation"]


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

    winglet_candidate = {
        "topic": "비행기 날개 끝의 윙렛은 소용돌이를 줄여 연료를 아낀다",
        "micro_narrative": {
            "hook": "왜 비행기 날개 끝의 윙렛은 소용돌이를 줄여 연료를 아낄까?"
        },
    }
    normalized_winglet = _observable_hook_from_candidate(winglet_candidate)
    assert normalized_winglet["micro_narrative"]["hook"] == (
        "비행기 날개 끝의 윙렛은 소용돌이를 줄여 연료를 아낍니다."
    )

    runner_source = Path("content/script_engine_v2_runner.py").read_text(encoding="utf-8")
    engine_source = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_runner = Path(tmpdir) / "script_engine_v2_runner.py"
        temp_engine = Path(tmpdir) / "script_engine_v2.py"
        temp_runner.write_text(runner_source, encoding="utf-8")
        temp_engine.write_text(engine_source, encoding="utf-8")
        original_runner_path = hotfix.RUNNER_PATH
        original_engine_path = hotfix.ENGINE_PATH
        try:
            hotfix.RUNNER_PATH = temp_runner
            hotfix.ENGINE_PATH = temp_engine
            hotfix.main()
            hotfix.main()
        finally:
            hotfix.RUNNER_PATH = original_runner_path
            hotfix.ENGINE_PATH = original_engine_path

        patched = temp_runner.read_text(encoding="utf-8")
        patched_engine = temp_engine.read_text(encoding="utf-8")
        assert patched.count(hotfix.MARKER) == 1, "runner hotfix must be idempotent"
        assert patched_engine.count(hotfix.HOOK_MARKER) == 1, "engine hotfix must be idempotent"
        assert patched_engine.count(hotfix.FINAL_HOOK_MARKER) == 1, "final hook normalization must be idempotent"
        assert patched_engine.count(hotfix.PLAIN_QUESTION_MARKER) == 1, "plain-question boundary must be idempotent"
        formalize = _load_formalizer(patched)
        convert_hook = _load_question_hook_converter(patched_engine)

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
        assert formalize(
            "카멜레온은 색을 바꾸는 능력으로 유명하지만, 그 이유는 의외로 복잡하다."
        ) == (
            "카멜레온은 색을 바꾸는 능력으로 유명하지만, 그 이유는 의외로 복잡합니다."
        )
        assert formalize("그 이유가 궁금해집니다.") == "그 이유가 궁금해집니다."

        recovered_question = (
            "왜 조종사와 승무원은 특정한 수신 신호를 사용하여 의사소통을 할까?"
        )
        assert convert_hook(recovered_question, "비행기 조종석과 객실 간의 커뮤니케이션 시스템") == (
            "조종사와 승무원은 특정한 수신 신호를 사용하여 의사소통을 합니다."
        )

        rounded_window_question = "왜 비행기 창문은 네모가 아니라 둥근가?"
        assert convert_hook(rounded_window_question, "비행기 창문 모서리가 둥근 이유") == (
            "비행기 창문은 네모가 아니라 둥급니다."
        )

        rounded_design_question = "왜 비행기 창문 모서리는 둥글게 설계되었을까?"
        assert convert_hook(rounded_design_question, "비행기 창문 모서리가 둥근 이유") == (
            "비행기 창문 모서리는 둥글게 설계되었습니다."
        )

        flap_question = "왜 비행기 날개 뒤쪽 플랩은 이착륙 때 펼쳐질까?"
        assert convert_hook(flap_question, flap_question) == (
            "비행기 날개 뒤쪽 플랩은 이착륙 때 펼쳐집니다."
        )

        rounded_state_question = "왜 비행기 창문 모서리가 이런 모양인가요?"
        assert convert_hook(rounded_state_question, "비행기 창문 모서리가 둥근 이유") == (
            "비행기 창문 모서리가 둥급니다."
        )

        embedded_why_hook = "비행기 날개에 있는 작은 갈고리는 왜 달려 있을까?"
        assert convert_hook(embedded_why_hook, embedded_why_hook) == (
            "비행기 날개에 있는 작은 갈고리는 달려 있습니다."
        )
        embedded_why_need_hook = "작은 갈고리는 비행기 날개에 왜 필요할까?"
        assert convert_hook(embedded_why_need_hook, embedded_why_hook) == (
            "작은 갈고리는 비행기 날개에 필요합니다."
        )

        # Exact production failure from run 32961763350. Do not claim an
        # unverified performance effect; retain only the visible, grounded fact.
        performance_question = "이 작은 갈고리는 비행기의 비행 성능에 어떤 영향을 미칠까?"
        assert convert_hook(performance_question, "명사형 주제") == (
            "비행기 날개에는 작은 갈고리가 있습니다."
        )
        assert 'hook.endswith(("까", "까요", "나요", "어요", "예요"))' in patched_engine

        assert convert_hook("왜 이 장치가 움직이나요?", "명사형 주제") == ""

    print("SCRIPT V2 OBSERVED FORMAL ENDING REGRESSION: PASS")


if __name__ == "__main__":
    main()
