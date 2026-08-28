from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from pathlib import Path

from quality.korean_speech_style import validate_korean_speech_text

# Actual production/regression corpus only. Provenance stays beside each fixture.
CORPUS = [
    {
        "source": "Run 33185606044 / Job 98897699796",
        "input": "날개 끝에서 압력 차가 강한 소용돌이를 만들어내고, 위로 꺾인 형태가 그 소용돌이를 줄인다.",
        "expected": "날개 끝에서 압력 차가 강한 소용돌이를 만들어내고, 위로 꺾인 형태가 그 소용돌이를 줄입니다.",
    },
    {
        "source": "Run 33095657123 regression fixture",
        "input": "비행기 이착륙 시, 객실의 조명이 갑자기 어두워진다.",
        "expected": "비행기 이착륙 시, 객실의 조명이 갑자기 어두워집니다.",
    },
    {
        "source": "Run 33095657123 regression fixture",
        "input": "이런 조명은 비상 상황 발생 시 승객의 시각 적응을 돕고, 비상구를 더 잘 인식할 수 있도록 설계되었다.",
        "expected": "이런 조명은 비상 상황 발생 시 승객의 시각 적응을 돕고, 비상구를 더 잘 인식할 수 있도록 설계되었습니다.",
    },
    {
        "source": "Run 33023068374 regression fixture",
        "input": "비행기 이착륙 시 승객들은 창문 덮개를 올려야 한다고 알려진다.",
        "expected": "비행기 이착륙 시 승객들은 창문 덮개를 올려야 한다고 알려집니다.",
    },
    {
        "source": "Run 33023068374 regression fixture",
        "input": "비상 상황 발생 시 승무원과 승객이 빠르게 대처할 수 있도록 도와준다.",
        "expected": "비상 상황 발생 시 승무원과 승객이 빠르게 대처할 수 있도록 도와줍니다.",
    },
    {
        "source": "existing script_v2 formal-ending regression fixture",
        "input": "비행기 엔진이 날개 아래에 장착된 모습을 보면, 그 이유가 궁금해진다.",
        "expected": "비행기 엔진이 날개 아래에 장착된 모습을 보면, 그 이유가 궁금해집니다.",
    },
    {
        "source": "existing script_v2 formal-ending regression fixture",
        "input": "이로 인해 비행기가 더 안전하게 비행할 수 있고, 엔진 고장 시에도 비행 제어가 용이해진다.",
        "expected": "이로 인해 비행기가 더 안전하게 비행할 수 있고, 엔진 고장 시에도 비행 제어가 용이해집니다.",
    },
    {
        "source": "existing script_v2 formal-ending regression fixture",
        "input": "그 결과, 비행기의 연료 효율이 향상되고, 비행 중 안정성이 증가하여 안전한 비행이 가능해진다.",
        "expected": "그 결과, 비행기의 연료 효율이 향상되고, 비행 중 안정성이 증가하여 안전한 비행이 가능해집니다.",
    },
    {
        "source": "existing script_v2 formal-ending regression fixture",
        "input": "날개가 휘어지면 공기 흐름이 최적화되고, 그로 인해 항력 감소가 이루어진다.",
        "expected": "날개가 휘어지면 공기 흐름이 최적화되고, 그로 인해 항력 감소가 이루어집니다.",
    },
    {
        "source": "existing Script Engine V2 production ending contract",
        "input": "유도항력이 감소한다.",
        "expected": "유도항력이 감소합니다.",
    },
    {
        "source": "existing script_v2 formal-ending regression fixture",
        "input": "유도항력이 줄어든다.",
        "expected": "유도항력이 줄어듭니다.",
    },
    {
        "source": "quality/script_engine_v2_regression_test.py production contract",
        "input": "둥근 모서리는 압력이 창문 모서리에 고르게 분산되도록 돕는다.",
        "expected": "둥근 모서리는 압력이 창문 모서리에 고르게 분산되도록 돕습니다.",
    },
    {
        "source": "quality/script_engine_v2_regression_test.py production contract",
        "input": "응력이 분산되어 특정 지점에 집중되지 않는다.",
        "expected": "응력이 분산되어 특정 지점에 집중되지 않습니다.",
    },
    {
        "source": "quality/script_engine_v2_regression_test.py production contract",
        "input": "비행기 날개의 끝이 비행 중 위로 휘어지는 모습이 보인다.",
        "expected": "비행기 날개의 끝이 비행 중 위로 휘어지는 모습이 보입니다.",
    },
]

INTERNAL_SENTENCE = {
    "source": "#221 sentence-granular production composition counterexample class",
    "input": "유도항력이 감소한다. 다음 문장은 이미 정상입니다.",
    "expected": "유도항력이 감소합니다. 다음 문장은 이미 정상입니다.",
}

NEGATIVE = [
    "이미 하십시오체입니다.",
    "왜 날개 끝이 위로 꺾여 있을까요?",
    "그는 '유도항력이 감소한다.'라고 설명했습니다.",
    "코드 `reduce_drag()`를 호출합니다.",
    "감소한다는 표현 자체를 설명합니다.",
]


def _load_unpatched_formalizer():
    source = Path("content/script_engine_v2_runner.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "_FORMAL_ENDING_REPAIRS" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_formalize_common_ending":
            selected.append(node)
    namespace = {}
    module = ast.Module(body=selected, type_ignores=[])
    exec("import re\nfrom typing import Any", namespace)
    exec(compile(module, "<before-formalizer>", "exec"), namespace)
    return namespace["_formalize_common_ending"]


def run_before_probe():
    formalize = _load_unpatched_formalizer()
    current = CORPUS[0]
    output = formalize(current["input"])
    valid, reason = validate_korean_speech_text(output, allow_nominal=False)
    assert output != current["expected"], "BEFORE unexpectedly already normalizes current production failure"
    assert not valid, "BEFORE must reproduce strict speech-style failure"
    print("BEFORE CORPUS FAILURE: PASS")
    print(f"source={current['source']}")
    print(f"output={output}")
    print(f"validator={reason}")


def _compose_scene(text: str, *, locked: bool):
    from content.script_engine_v2 import apply_locked_scenes
    from content.script_engine_v2_runner import _normalize_script_contracts_without_api

    role = "payoff" if locked else "mechanism_1"
    contract = {
        "index": 1,
        "role": role,
        "locked": locked,
        "locked_text": text if locked else "",
        "required_concepts": [],
        "forbidden": [],
    }
    plan = {"contracts": [contract], "topic": "winglet", "angle": "", "runtime_bucket": "short"}
    script = {
        "scenes": [
            {
                "text": text,
                "visual_goal": "비행기 날개 끝 구조를 명확하게 보여주는 화면",
                "keyword": "aircraft wing detail",
            }
        ]
    }
    composed = apply_locked_scenes(deepcopy(script), plan)
    composed = _normalize_script_contracts_without_api(composed, plan)
    return composed["scenes"][0]["text"]


def run_after_corpus():
    from content.script_formal_endings import formalize_declarative_text

    for item in CORPUS:
        for locked in (False, True):
            output = _compose_scene(item["input"], locked=locked)
            assert output == item["expected"], (item["source"], locked, output)
            valid, reason = validate_korean_speech_text(output, allow_nominal=False)
            assert valid, (item["source"], locked, reason)

    for locked in (False, True):
        output = _compose_scene(INTERNAL_SENTENCE["input"], locked=locked)
        assert output == INTERNAL_SENTENCE["expected"], (locked, output)
        valid, reason = validate_korean_speech_text(output, allow_nominal=False)
        assert valid, (locked, reason)

    for value in NEGATIVE:
        assert formalize_declarative_text(value) == value, value

    assert formalize_declarative_text("왜 소용돌이가 줄어들까?") == "왜 소용돌이가 줄어들까?"

    current_before = CORPUS[0]["input"].rsplit("줄인다", 1)[0]
    current_after = CORPUS[0]["expected"].rsplit("줄입니다", 1)[0]
    assert current_before == current_after

    print(f"SCRIPT FORMAL-ENDING PRODUCTION CORPUS V1: PASS items={len(CORPUS)}")
    print("LOCKED/UNLOCKED PARITY: PASS")
    print("INTERNAL SENTENCE NORMALIZATION: PASS")
    print("NEGATIVE CORPUS: PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", action="store_true")
    args = parser.parse_args()
    if args.before:
        run_before_probe()
    else:
        run_after_corpus()


if __name__ == "__main__":
    main()
