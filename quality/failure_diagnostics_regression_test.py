import importlib
import json
import os
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quality.budget_guard import reset_budget


def _load_modules(root: Path):
    os.environ["SHORTS_DIAGNOSTICS_DIR"] = str(root)
    import diagnostics.failure_diagnostics as fd
    import diagnostics.runner as runner
    importlib.reload(fd)
    importlib.reload(runner)
    return fd, runner


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def case_scene_failure_preserves_original_and_state():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fd, runner = _load_modules(root)
        fd.get_budget_status = lambda: {
            "calls": 13,
            "max_calls": 60,
            "cost_usd": 0.010533,
            "max_cost_usd": 0.05,
        }

        secret = "diagnostic-secret-value-123"
        os.environ["OPENAI_KEY"] = secret

        fake = types.ModuleType("main")

        class SceneBoom(RuntimeError):
            pass

        def create_scene(idx, item, create_voice):
            print(f"provider token={secret}")
            raise SceneBoom(f"scene exploded {secret}")

        fake.create_scene = create_scene

        def main():
            fake.create_scene(
                8,
                {
                    "role": "result",
                    "text": "윙렛은 유도항력을 줄여 연료 효율을 높인다.",
                    "visual_goal": "winglet reducing wingtip vortex",
                    "source_type": "pexels",
                    "visual_explanation_template": "WINGLET_RESULT",
                },
                lambda *_: None,
            )

        fake.main = main
        sys.modules["main"] = fake

        caught = None
        try:
            runner.run()
        except Exception as exc:
            caught = exc

        assert isinstance(caught, SceneBoom), type(caught)
        assert "scene exploded" in str(caught)

        summary = _read_json(root / "failure_summary.json")
        progress = _read_json(root / "progress.json")
        trace = (root / "traceback.txt").read_text(encoding="utf-8")
        log = (root / "generator.log").read_text(encoding="utf-8")
        scene_lines = (root / "scene_trace.jsonl").read_text(encoding="utf-8").splitlines()

        assert summary["last_scene_index"] == 9, summary
        assert summary["last_scene_role"] == "result", summary
        assert summary["last_source_type"] == "pexels", summary
        assert summary["last_visual_explanation_template"] == "WINGLET_RESULT", summary
        assert summary["api_calls_used"] == 13, summary
        assert summary["api_calls_limit"] == 60, summary
        assert abs(summary["openai_cost_usd"] - 0.010533) < 1e-12, summary
        assert abs(summary["cost_limit_usd"] - 0.05) < 1e-12, summary
        assert summary["traceback_available"] is True, summary
        assert progress["current_scene_index"] == 9, progress
        assert progress["current_narration"].startswith("윙렛은"), progress
        assert "SceneBoom" in trace, trace
        assert secret not in trace, trace
        assert secret not in log, log
        assert secret not in json.dumps(summary, ensure_ascii=False), summary
        assert any('"completed": false' in line for line in scene_lines), scene_lines


def case_missing_scene_metadata_is_safe():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fd, runner = _load_modules(root)
        fake = types.ModuleType("main")
        fake.create_scene = lambda *args, **kwargs: None

        original = RuntimeError("failure before scenes")

        def main():
            raise original

        fake.main = main
        sys.modules["main"] = fake

        caught = None
        try:
            runner.run()
        except Exception as exc:
            caught = exc

        assert caught is original
        summary = _read_json(root / "failure_summary.json")
        assert summary["last_scene_index"] is None, summary
        assert summary["last_scene_narration"] is None, summary
        assert (root / "traceback.txt").exists()


def case_success_path_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fd, runner = _load_modules(root)
        fake = types.ModuleType("main")
        marker = {"calls": 0}

        def create_scene(idx, item, create_voice):
            marker["calls"] += 1
            return "scene-result"

        fake.create_scene = create_scene

        def main():
            result = fake.create_scene(
                0,
                {"text": "정상 장면", "visual_goal": "aircraft wing"},
                lambda *_: None,
            )
            assert result == "scene-result"

        fake.main = main
        sys.modules["main"] = fake
        runner.run()

        assert marker["calls"] == 1
        assert not (root / "failure_summary.json").exists()
        assert not (root / "traceback.txt").exists()
        progress = _read_json(root / "progress.json")
        assert progress["current_stage"] == "completed", progress
        assert progress["last_completed_stage"] == "generator", progress


def case_log_is_bounded():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fd, _ = _load_modules(root)
        log = fd.BoundedArtifactLog(max_bytes=64)
        log.write("x" * 1024)
        log.close()
        text = (root / "generator.log").read_text(encoding="utf-8")
        assert "[DIAGNOSTICS LOG TRUNCATED]" in text
        assert len(text.encode("utf-8")) < 256


def main():
    reset_budget()
    case_scene_failure_preserves_original_and_state()
    case_missing_scene_metadata_is_safe()
    case_success_path_unchanged()
    case_log_is_bounded()
    print("Failure Diagnostics V1 regression: PASS")


if __name__ == "__main__":
    main()
