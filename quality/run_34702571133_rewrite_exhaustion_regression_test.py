import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd):
    subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
    )


def value(source, name):
    match = re.search(
        rf"^\s*{re.escape(name)}\s*=\s*([^#\n]+)",
        source,
        flags=re.MULTILINE,
    )
    assert match, f"missing constant: {name}"
    return match.group(1).strip()


def load_helper(source):
    tree = ast.parse(source)
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_should_regenerate_after_rewrite_exhaustion"
    )
    module = ast.Module(body=[helper], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, "<rewrite-exhaustion-helper>", "exec"), namespace)
    return namespace[helper.name]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "repo"
        shutil.copytree(
            ROOT,
            scratch,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )

        # Match the relevant beginning of the production composition: ci_hotfix
        # establishes runtime defaults, then topic-input installs forced_topic.
        run([sys.executable, "ci_hotfix.py"], scratch)

        pre_topic_main = (scratch / "main.py").read_text(encoding="utf-8")
        pre_topic_consensus = (scratch / "quality/consensus.py").read_text(encoding="utf-8")
        pre_topic_config = (scratch / "config.py").read_text(encoding="utf-8")

        boundaries = {
            "MAX_TOPIC_REGENERATIONS": value(pre_topic_main, "MAX_TOPIC_REGENERATIONS"),
            "NOVELTY_HARD_REGENERATE_SCORE": value(pre_topic_main, "NOVELTY_HARD_REGENERATE_SCORE"),
            "MAX_REWRITES": value(pre_topic_main, "MAX_REWRITES"),
            "GOOD_ENOUGH_SCORE": value(pre_topic_consensus, "GOOD_ENOUGH_SCORE"),
            "MAX_SCRIPT_ATTEMPTS": value(pre_topic_config, "MAX_SCRIPT_ATTEMPTS"),
        }

        run([sys.executable, "ci_topic_input_hotfix.py"], scratch)
        # Installer must remain safe when a downstream composition test reapplies it.
        run([sys.executable, "ci_topic_input_hotfix.py"], scratch)

        patched = (scratch / "main.py").read_text(encoding="utf-8")
        patched_consensus = (scratch / "quality/consensus.py").read_text(encoding="utf-8")
        patched_config = (scratch / "config.py").read_text(encoding="utf-8")

        assert patched.count(
            "RUN_34702571133_REWRITE_EXHAUSTION_CANDIDATE_REGENERATION_V1"
        ) == 1
        assert '"failure_type":\n                        "REWRITE_EXHAUSTED"' in patched
        assert "♻️ REWRITE EXHAUSTED → CANDIDATE REGENERATION" in patched
        assert "➡️ 남은 Candidate attempt로 재탐색" in patched
        assert "rejected_topics.append(\n                        rejected_topic" in patched
        assert "topic_attempt\n                    < total_topic_attempts" in patched
        assert "continue" in patched

        helper = load_helper(patched)

        # Run 34702571133 authority case: automatic aviation Candidate, one
        # rewrite already spent, still HOLD => reject only this Candidate and
        # use a remaining topic attempt.
        assert helper("HOLD", "REWRITE_EXHAUSTED", "") is True
        assert helper("HOLD", "REWRITE_EXHAUSTED", None) is True

        # Fixed-topic production must never silently substitute another topic.
        assert helper(
            "HOLD",
            "REWRITE_EXHAUSTED",
            "비행기 창문 디자인의 둥근 모서리",
        ) is False

        # Unrelated HOLDs keep their existing terminal semantics.
        assert helper("HOLD", "FACT_CRITICAL", "") is False
        assert helper("REGENERATE_TOPIC", "REWRITE_EXHAUSTED", "") is False

        # Existing persistent-Novelty behavior must remain intact: this branch
        # already returns REGENERATE_TOPIC before REWRITE_EXHAUSTED is emitted.
        persistent_pos = patched.index("has_persistent_novelty_failure")
        exhausted_pos = patched.index('"REWRITE_EXHAUSTED"')
        assert persistent_pos < exhausted_pos

        # This fix is control-flow only. It must not change cost, quality,
        # rewrite, or Candidate-attempt ceilings/floors.
        assert value(patched, "MAX_TOPIC_REGENERATIONS") == boundaries["MAX_TOPIC_REGENERATIONS"]
        assert value(patched, "NOVELTY_HARD_REGENERATE_SCORE") == boundaries["NOVELTY_HARD_REGENERATE_SCORE"]
        assert value(patched, "MAX_REWRITES") == boundaries["MAX_REWRITES"]
        assert value(patched_consensus, "GOOD_ENOUGH_SCORE") == boundaries["GOOD_ENOUGH_SCORE"]
        assert value(patched_config, "MAX_SCRIPT_ATTEMPTS") == boundaries["MAX_SCRIPT_ATTEMPTS"]

        # Fixed-topic source guard must still exist after the new patch.
        assert "if forced_topic:" in patched
        assert "and current_topic != forced_topic" in patched

    print("PASS: Run 34702571133 rewrite exhaustion -> automatic Candidate regeneration")


if __name__ == "__main__":
    main()
