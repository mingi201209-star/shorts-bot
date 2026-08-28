import copy
import importlib.util
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOTFIX_PATH = ROOT / "ci_script_v2_gunggeum_formal_ending_hotfix.py"
TARGET_TOPIC = "비행기 착륙할 때 날개 위 판이 갑자기 올라오는 이유"


def load_hotfix():
    spec = importlib.util.spec_from_file_location("spoiler_payoff_hotfix", HOTFIX_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RUNNER_FIXTURE = '''import os
from copy import deepcopy
from typing import Any, Dict


def _normalize_script_contracts_without_api(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    result["scenes"] = scenes
    return result


def _normalize_writer_envelope(response: Dict[str, Any]) -> Dict[str, Any]:
    return response
'''


def execute_runner(path: Path):
    namespace = {}
    exec(path.read_text(encoding="utf-8"), namespace)
    return namespace


def make_fixture():
    scenes = []
    for index in range(1, 13):
        scenes.append({
            "text": f"scene {index}",
            "visual_goal": f"goal {index}",
            "keyword": f"aircraft wing stage {index}",
            "fact_fingerprint": f"fact-{index}",
        })
    scenes[11] = {
        "text": "결국 이 메커니즘 덕분에 비행기는 더 부드럽고 안전하게 착륙할 수 있습니다.",
        "visual_goal": "비행기 착륙 시 날개 위 판이 올라오는 모습",
        "keyword": "aircraft wing flap up stage 12",
        "fact_fingerprint": "spoiler-lift-wheel-braking-grounding",
    }
    return {"scenes": scenes}


def main():
    hotfix = load_hotfix()
    with tempfile.TemporaryDirectory() as tmpdir:
        runner_path = Path(tmpdir) / "script_engine_v2_runner.py"
        runner_path.write_text(RUNNER_FIXTURE, encoding="utf-8")
        hotfix.RUNNER_PATH = runner_path

        original = make_fixture()
        before_ns = execute_runner(runner_path)
        before = before_ns["_normalize_script_contracts_without_api"](
            original, {"topic": TARGET_TOPIC}
        )
        assert before["scenes"][11]["keyword"] == "aircraft wing flap up stage 12"
        assert before["scenes"][11]["visual_goal"] == "비행기 착륙 시 날개 위 판이 올라오는 모습"

        assert hotfix._patch_spoiler_payoff_visual_contract() is True
        assert hotfix._patch_spoiler_payoff_visual_contract() is False

        after_ns = execute_runner(runner_path)
        os.environ["SHORTS_TOPIC"] = TARGET_TOPIC
        try:
            after = after_ns["_normalize_script_contracts_without_api"](
                original, {"topic": TARGET_TOPIC}
            )
        finally:
            os.environ.pop("SHORTS_TOPIC", None)

        assert after["scenes"][11]["keyword"] == "aircraft wing spoilers deployed after landing"
        assert after["scenes"][11]["visual_goal"] == "착륙 직후 비행기 날개 위 스포일러가 실제로 펼쳐진 모습"
        assert after["scenes"][11]["text"] == before["scenes"][11]["text"]
        assert after["scenes"][11]["fact_fingerprint"] == before["scenes"][11]["fact_fingerprint"]
        assert after["scenes"][:11] == before["scenes"][:11]

        other = make_fixture()
        os.environ["SHORTS_TOPIC"] = "비행기 날개 끝 윙렛은 왜 위로 꺾여 있을까"
        try:
            untouched = after_ns["_normalize_script_contracts_without_api"](
                other, {"topic": "비행기 날개 끝 윙렛은 왜 위로 꺾여 있을까"}
            )
        finally:
            os.environ.pop("SHORTS_TOPIC", None)
        assert untouched == other

    print("SPOILER_PAYOFF_VISUAL_CONTRACT_REGRESSION_PASS")


if __name__ == "__main__":
    main()
