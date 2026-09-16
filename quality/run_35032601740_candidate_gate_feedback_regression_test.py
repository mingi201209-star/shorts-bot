import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = ROOT / "ci_aviation_context_signature_compat_hotfix.py"


RUNTIME_GATE_FIXTURE = '''                print(
                    "이유:",
                    winner_gate.get(
                        "reason",
                        "",
                    ),
                )

                if forced_topic:
                    fixed_topic_gate_feedback = str(
                        winner_gate.get(
                            "reason",
                            "",
                        )
                    ).strip()

                print_budget_status()
'''


def _load_apply_function():
    source = INSTALLER_PATH.read_text(encoding="utf-8")
    module = ast.parse(source)
    functions = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "apply_automatic_gate_feedback"
    ]
    assert len(functions) == 1
    namespace = {}
    isolated = ast.Module(body=functions, type_ignores=[])
    exec(compile(isolated, str(INSTALLER_PATH), "exec"), namespace)
    return namespace["apply_automatic_gate_feedback"], source


def test_run_35032601740_default_automatic_scope_receives_gate_feedback():
    apply, _ = _load_apply_function()
    patched = apply(RUNTIME_GATE_FIXTURE)

    assert "# RUN_35032601740_AUTOMATIC_GATE_FEEDBACK_V1" in patched
    assert "elif gate_reject_reason:" in patched
    assert "SHORTS_CANDIDATE_SCOPE" not in patched
    assert "[AUTOMATIC CANDIDATE GATE FEEDBACK]" in patched
    assert "rejected_topics.append(automatic_feedback)" in patched
    assert "choose a materially different, concrete" in patched
    assert "directly resolve this Gate reason" in patched
    assert "do not relax the Gate or invent a causal claim" in patched


def test_fixed_topic_feedback_path_is_preserved():
    apply, _ = _load_apply_function()
    patched = apply(RUNTIME_GATE_FIXTURE)

    assert "if forced_topic:" in patched
    assert "fixed_topic_gate_feedback = gate_reject_reason" in patched
    assert patched.index("if forced_topic:") < patched.index("elif gate_reject_reason:")


def test_feedback_reason_is_bounded_and_normalized():
    apply, _ = _load_apply_function()
    patched = apply(RUNTIME_GATE_FIXTURE)

    assert ".split()" in patched
    assert ")[:900]" in patched
    assert "reason={gate_reject_reason}" in patched
    assert "rejected_topic={current_topic}" in patched


def test_patch_is_idempotent():
    apply, _ = _load_apply_function()
    once = apply(RUNTIME_GATE_FIXTURE)
    twice = apply(once)
    assert twice == once
    assert once.count("RUN_35032601740_AUTOMATIC_GATE_FEEDBACK_V1") == 1


def test_quality_retry_and_cost_invariants_are_unchanged():
    _, source = _load_apply_function()
    forbidden_assignments = (
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
        "MAX_TOPIC_REGENERATIONS =",
        "HOOK_THRESHOLD =",
        "HOOK_ACTION_MATCH_MIN =",
        "HOOK_SUBJECT_DOMINANCE_MIN =",
        "HOOK_MAX_COMPETING_SUBJECT_RISK =",
    )
    for forbidden in forbidden_assignments:
        assert forbidden not in source

    assert "authorize_call(" not in source
    assert "openai.chat.completions.create(" not in source
    assert "total_topic_attempts +" not in source


if __name__ == "__main__":
    tests = [
        test_run_35032601740_default_automatic_scope_receives_gate_feedback,
        test_fixed_topic_feedback_path_is_preserved,
        test_feedback_reason_is_bounded_and_normalized,
        test_patch_is_idempotent,
        test_quality_retry_and_cost_invariants_are_unchanged,
    ]
    for test in tests:
        test()
    print("RUN_35032601740_CANDIDATE_GATE_FEEDBACK: PASS")
