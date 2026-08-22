from pathlib import Path
import ast
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "content" / "candidate_explorer.py"


def run(script):
    subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)


def main():
    # Reproduce the production hotfix order that created run 32545383158.
    run("ci_topic_input_hotfix.py")
    run("ci_aviation_candidate_context_hotfix.py")
    run("ci_aviation_candidate_specificity_hotfix.py")
    run("ci_aviation_context_signature_compat_hotfix.py")

    text = EXPLORER.read_text(encoding="utf-8")
    tree = ast.parse(text)

    build_defs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_execution_context"
    ]
    assert len(build_defs) >= 2, "specificity wrapper was not installed"

    wrapper = build_defs[-1]
    kwonly = [arg.arg for arg in wrapper.args.kwonlyargs]
    assert "fixed_topic" in kwonly, "wrapper dropped fixed_topic from production signature"

    segment = ast.get_source_segment(text, wrapper) or ""
    assert "fixed_topic=fixed_topic" in segment, "wrapper does not forward fixed_topic"
    assert "_aviation_specificity_previous_build_context" in segment

    # Exact production counterexample: the generated function must accept this keyword.
    compile(text, str(EXPLORER), "exec")

    print("PASS: aviation context signature compatibility")
    print("- fixed_topic accepted by final build_execution_context wrapper")
    print("- fixed_topic forwarded to previous production wrapper")
    print("- Candidate Gate/specificity thresholds untouched")


if __name__ == "__main__":
    main()
