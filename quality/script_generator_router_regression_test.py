import os
import sys
import types

import content.script_generator_router as router


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾인 이유",
        "angle": "윙렛과 유도항력",
        "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
        "micro_narrative": {"hook": "비행기 날개 끝이 위로 꺾여 있습니다."},
        "fact_check_focus": ["압력 차이"],
        "visual_proof": ["winglet"],
        "selection_reason": "aviation continuity",
    }


def main():
    original = os.environ.get("SCRIPT_ENGINE_MODE")
    old_legacy = sys.modules.get("content.script_generator")
    old_v2 = sys.modules.get("content.script_engine_v2_runner")
    try:
        legacy_module = types.ModuleType("content.script_generator")
        legacy_module.generate_script = lambda topic_info, item: {"engine": "legacy"}
        v2_module = types.ModuleType("content.script_engine_v2_runner")
        v2_module.generate_script_v2 = lambda item: {
            "engine": "v2",
            "title": "윙렛의 이유",
            "scenes": [{
                "text": "비행기 날개 끝이 위로 꺾여 있습니다.",
                "visual_goal": "show winglet",
                "keyword": "airplane winglet closeup",
            }],
        }
        sys.modules["content.script_generator"] = legacy_module
        sys.modules["content.script_engine_v2_runner"] = v2_module

        os.environ.pop("SCRIPT_ENGINE_MODE", None)
        result = router.generate_script({"topic": "aviation", "category": "항공"}, candidate())
        assert result["engine"] == "v2"
        assert result["topic"] == candidate()["topic"]
        assert result["category"] == "항공"
        assert result["angle"] == candidate()["angle"]
        assert result["core_question"] == candidate()["core_question"]
        assert result["micro_narrative"] == candidate()["micro_narrative"]
        assert result["fact_check_focus"] == ["압력 차이"]
        assert result["visual_proof"] == ["winglet"]
        assert result["candidate_selection_reason"] == "aviation continuity"
        assert result["scenes"][0]["visual_type"] == "real_world_broll"

        os.environ["SCRIPT_ENGINE_MODE"] = "legacy"
        assert router.generate_script({"topic": "direction"}, candidate())["engine"] == "legacy"

        os.environ["SCRIPT_ENGINE_MODE"] = "unknown"
        try:
            router.generate_script({}, {})
        except ValueError as exc:
            assert "Unsupported SCRIPT_ENGINE_MODE" in str(exc)
        else:
            raise AssertionError("unsupported mode must fail closed")
    finally:
        if old_legacy is not None:
            sys.modules["content.script_generator"] = old_legacy
        else:
            sys.modules.pop("content.script_generator", None)
        if old_v2 is not None:
            sys.modules["content.script_engine_v2_runner"] = old_v2
        else:
            sys.modules.pop("content.script_engine_v2_runner", None)
        if original is None:
            os.environ.pop("SCRIPT_ENGINE_MODE", None)
        else:
            os.environ["SCRIPT_ENGINE_MODE"] = original

    print("PASS: Script Generator router V2 default and legacy rollback")


if __name__ == "__main__":
    main()
