import os
import sys
import types

import content.script_generator_router as router


def main():
    original = os.environ.get("SCRIPT_ENGINE_MODE")
    try:
        legacy_module = types.ModuleType("content.script_generator")
        legacy_module.generate_script = lambda topic_info, candidate: {
            "engine": "legacy",
            "topic_info": topic_info,
            "candidate": candidate,
        }
        v2_module = types.ModuleType("content.script_engine_v2_runner")
        v2_module.generate_script_v2 = lambda candidate: {
            "engine": "v2",
            "candidate": candidate,
        }
        old_legacy = sys.modules.get("content.script_generator")
        old_v2 = sys.modules.get("content.script_engine_v2_runner")
        sys.modules["content.script_generator"] = legacy_module
        sys.modules["content.script_engine_v2_runner"] = v2_module

        os.environ.pop("SCRIPT_ENGINE_MODE", None)
        result = router.generate_script({"topic": "direction"}, {"topic": "candidate"})
        assert result["engine"] == "legacy"

        os.environ["SCRIPT_ENGINE_MODE"] = "v2"
        result = router.generate_script({"topic": "ignored"}, {"topic": "candidate"})
        assert result["engine"] == "v2"

        os.environ["SCRIPT_ENGINE_MODE"] = "unknown"
        try:
            router.generate_script({}, {})
        except ValueError as exc:
            assert "Unsupported SCRIPT_ENGINE_MODE" in str(exc)
        else:
            raise AssertionError("unsupported mode must fail closed")

        if old_legacy is not None:
            sys.modules["content.script_generator"] = old_legacy
        else:
            sys.modules.pop("content.script_generator", None)
        if old_v2 is not None:
            sys.modules["content.script_engine_v2_runner"] = old_v2
        else:
            sys.modules.pop("content.script_engine_v2_runner", None)
    finally:
        if original is None:
            os.environ.pop("SCRIPT_ENGINE_MODE", None)
        else:
            os.environ["SCRIPT_ENGINE_MODE"] = original

    print("PASS: Script Generator router legacy-default and v2 opt-in")


if __name__ == "__main__":
    main()
