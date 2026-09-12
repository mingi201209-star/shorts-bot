import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ci_run_34671707523_opening_candidate_recovery_hotfix import (
    MARKER,
    apply_opening_candidate_recovery,
)


ANCHOR = '''            # =================================================
            # Winner Script
            # =================================================

            script_data = (
                generate_script(
                    topic_info,
                    winner,
                )
            )
'''


def _build_compilable_runtime():
    # Keep the exact production anchor indentation while constructing a tiny
    # executable loop around it. This avoids mocking main.py's unrelated
    # imports and still proves the inserted `continue` skips Writer.
    source = '''def run_case(forced_topic, winners, total_topic_attempts):
    fixed_topic_gate_feedback = ""
    writer_calls = []
    topic_info = {"topic": "fixed"}

    def print_budget_status():
        return None

    def generate_script(topic_info, winner):
        writer_calls.append(winner.get("name"))
        return {"winner": winner.get("name")}

    for topic_attempt in range(1, total_topic_attempts + 1):
        winner = winners[topic_attempt - 1]
'''
    # Production anchor is twelve-space indented; inside this test function's
    # for-loop we need eight spaces. Apply against exact production text first,
    # then shift only the synthetic harness indentation afterwards.
    production_shape = (
        'fixed_topic_gate_feedback = ""\n'
        'if forced_topic:\n'
        + ANCHOR
        + 'generate_script(\n'
    )
    patched_shape = apply_opening_candidate_recovery(production_shape)
    assert MARKER in patched_shape
    block = patched_shape.split('if forced_topic:\n', 1)[1].rsplit('generate_script(\n', 1)[0]
    shifted = []
    for line in block.splitlines():
        shifted.append(line[4:] if line.startswith("    ") else line)
    source += "\n".join(shifted) + "\n"
    source += '''        return {
            "script_data": script_data,
            "writer_calls": writer_calls,
            "feedback": fixed_topic_gate_feedback,
            "attempt": topic_attempt,
        }

    return {
        "script_data": None,
        "writer_calls": writer_calls,
        "feedback": fixed_topic_gate_feedback,
        "attempt": total_topic_attempts,
    }
'''
    compile(source, "<run34671707523-runtime>", "exec")
    return source


def _install_fake_final_validator():
    content_pkg = sys.modules.setdefault("content", types.ModuleType("content"))
    module = types.ModuleType("content.script_engine_v2_validation")

    def opening_human_contract_violation_reason(scene1, scene2):
        if str(scene1).startswith("BAD:"):
            return "opening scene 1 restates the same proposition scene 2 asks as a question"
        return ""

    module.opening_human_contract_violation_reason = (
        opening_human_contract_violation_reason
    )
    sys.modules["content.script_engine_v2_validation"] = module
    setattr(content_pkg, "script_engine_v2_validation", module)


def _winner(name, hook):
    return {
        "name": name,
        "core_question": "왜 그런가요?",
        "micro_narrative": {
            "hook": hook,
            "core_question": "왜 그런가요?",
        },
    }


def main():
    # Installer contracts.
    production_shape = (
        'fixed_topic_gate_feedback = ""\n'
        'if forced_topic:\n'
        + ANCHOR
        + 'generate_script(\n'
    )
    patched = apply_opening_candidate_recovery(production_shape)
    assert MARKER in patched
    assert apply_opening_candidate_recovery(patched) == patched
    assert apply_opening_candidate_recovery("def unrelated():\n    pass\n") == "def unrelated():\n    pass\n"

    # No quality or retry limit is introduced/changed by this installer.
    for forbidden in (
        "MAX_TOPIC_REGENERATIONS =",
        "MAX_SCRIPT_ATTEMPTS =",
        "V3_MAX_COST_USD",
        "V3_MAX_API_CALLS",
    ):
        assert forbidden not in patched

    source = _build_compilable_runtime()
    namespace = {}
    _install_fake_final_validator()
    exec(source, namespace)
    run_case = namespace["run_case"]

    # Authority behavior from Run 34671707523: a locked bad opening must never
    # spend Writer retries. It routes to the next *existing* Candidate attempt.
    result = run_case(
        True,
        [
            _winner("bad-first", "BAD: same proposition"),
            _winner("good-second", "응력이 모서리에 집중됩니다."),
        ],
        2,
    )
    assert result["attempt"] == 2
    assert result["writer_calls"] == ["good-second"]
    assert "Final opening human contract rejected" in result["feedback"]
    assert "Do not invent new facts" in result["feedback"]

    # Non-fixed-topic flow is intentionally untouched by this recovery layer.
    result = run_case(
        False,
        [_winner("non-fixed", "BAD: same proposition")],
        1,
    )
    assert result["writer_calls"] == ["non-fixed"]

    # At the last existing Candidate attempt, fail closed before Writer.
    try:
        run_case(
            True,
            [_winner("bad-last", "BAD: same proposition")],
            1,
        )
    except RuntimeError as exc:
        assert "exhausted bounded attempts" in str(exc)
    else:
        raise AssertionError("bad final Candidate must fail closed")

    print("Run 34671707523 opening Candidate recovery regression PASS")


if __name__ == "__main__":
    main()
