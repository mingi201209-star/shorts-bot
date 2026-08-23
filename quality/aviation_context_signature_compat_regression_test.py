from pathlib import Path
import ast
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "content" / "candidate_explorer.py"
MAIN = ROOT / "main.py"


def run(script):
    subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)


def main():
    # Reproduce the production Explorer hotfix order before the generator starts.
    run("ci_topic_input_hotfix.py")
    run("ci_aviation_candidate_context_hotfix.py")
    run("ci_aviation_candidate_specificity_hotfix.py")
    run("ci_aviation_context_signature_compat_hotfix.py")
    run("ci_aviation_specificity_output_repair_hotfix.py")
    run("ci_aviation_specificity_projection_hotfix.py")

    text = EXPLORER.read_text(encoding="utf-8")
    tree = ast.parse(text)

    build_defs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_execution_context"
    ]
    assert len(build_defs) >= 2, "specificity wrapper was not installed"

    wrapper = build_defs[-1]
    build_kwonly = [arg.arg for arg in wrapper.args.kwonlyargs]
    assert "fixed_topic" in build_kwonly, "wrapper dropped fixed_topic"
    assert (
        "fixed_topic_gate_feedback" in build_kwonly
    ), "wrapper dropped fixed_topic_gate_feedback"

    build_segment = ast.get_source_segment(text, wrapper) or ""
    assert "fixed_topic=fixed_topic" in build_segment
    assert "fixed_topic_gate_feedback=fixed_topic_gate_feedback" in build_segment
    assert "_aviation_specificity_previous_build_context" in build_segment

    explorer_defs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "explore_candidates"
    ]
    assert explorer_defs, "explore_candidates missing"
    explorer = explorer_defs[-1]
    explorer_kwonly = [arg.arg for arg in explorer.args.kwonlyargs]
    assert "fixed_topic" in explorer_kwonly, "Explorer dropped fixed_topic"
    assert (
        "fixed_topic_gate_feedback" in explorer_kwonly
    ), "Explorer dropped fixed_topic_gate_feedback"

    explorer_segment = ast.get_source_segment(text, explorer) or ""
    assert "fixed_topic=fixed_topic" in explorer_segment
    assert "fixed_topic_gate_feedback" in explorer_segment

    # Automatic aviation rejection feedback is persisted through rejected_topics,
    # while the exact rejected topic remains separately present for repeat blocking.
    main_text = MAIN.read_text(encoding="utf-8")
    assert "[AUTOMATIC AVIATION GATE FEEDBACK]" in main_text
    assert "gate_reject_reason" in main_text
    assert "automatic_feedback not in rejected_topics" in main_text
    assert "rejected_topics.append(automatic_feedback)" in main_text
    assert 'SHORTS_CANDIDATE_SCOPE' in main_text
    assert '== "aviation"' in main_text
    assert "if forced_topic:" in main_text
    assert "fixed_topic_gate_feedback = gate_reject_reason" in main_text

    # The aviation specificity context already serializes rejected_topics into
    # DOWNSTREAM REJECTION FEEDBACK, so automatic Gate reason records reach the
    # next Explorer attempt without changing Candidate Gate thresholds.
    assert "[DOWNSTREAM REJECTION FEEDBACK]" in text
    assert "rejected_feedback" in text
    assert "같은 명사만 바꾸거나" in text

    # Exact production counterexample must compile after the full Explorer stack.
    compile(text, str(EXPLORER), "exec")
    compile(main_text, str(MAIN), "exec")

    print("PASS: aviation Gate-feedback compatibility")
    print("- fixed_topic + gate feedback accepted by final wrappers")
    print("- automatic aviation Gate rejection reason retained for next attempt")
    print("- exact rejected topic repeat protection remains separate")
    print("- Candidate Gate/recovery thresholds untouched")


if __name__ == "__main__":
    main()
