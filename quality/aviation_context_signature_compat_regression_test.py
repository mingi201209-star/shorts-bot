from pathlib import Path
import ast
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "content" / "candidate_explorer.py"


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

    # Exact production counterexample from run 32561698004 must compile after the
    # full Explorer hotfix stack, without changing Candidate Gate thresholds.
    compile(text, str(EXPLORER), "exec")

    print("PASS: aviation fixed-topic signature compatibility")
    print("- fixed_topic + gate feedback accepted by final wrappers")
    print("- both values forwarded through execution context")
    print("- Candidate Gate/specificity thresholds untouched")


if __name__ == "__main__":
    main()
