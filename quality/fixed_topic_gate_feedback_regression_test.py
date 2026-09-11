from pathlib import Path
import hashlib
import py_compile
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def retry_policy(text):
    match = re.search(r"^MAX_TOPIC_REGENERATIONS\s*=\s*(\d+)\s*$", text, re.MULTILINE)
    assert match, "MAX_TOPIC_REGENERATIONS assignment missing"
    return int(match.group(1))


def committed_text(path):
    # This regression is also executed after the production hotfix chain has
    # already mutated the working tree. Always reconstruct the test fixture
    # from the checked-out commit instead of copying the mutated workspace.
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    (work / "content").mkdir()
    (work / "quality").mkdir()
    (work / "main.py").write_text(
        committed_text("main.py"),
        encoding="utf-8",
    )
    (work / "content" / "candidate_explorer.py").write_text(
        committed_text("content/candidate_explorer.py"),
        encoding="utf-8",
    )
    (work / "quality" / "consensus.py").write_text(
        committed_text("quality/consensus.py"),
        encoding="utf-8",
    )
    (work / "ci_topic_input_hotfix.py").write_text(
        committed_text("ci_topic_input_hotfix.py"),
        encoding="utf-8",
    )
    (work / "ci_fixed_topic_gate_advisory_hotfix.py").write_text(
        committed_text("ci_fixed_topic_gate_advisory_hotfix.py"),
        encoding="utf-8",
    )

    gate_path = ROOT / "content" / "candidate_gate.py"
    gate_before = hashlib.sha256(gate_path.read_bytes()).hexdigest()
    main_before = (work / "main.py").read_text(encoding="utf-8")
    retry_before = retry_policy(main_before)

    subprocess.run(
        [sys.executable, "ci_topic_input_hotfix.py"],
        cwd=work,
        check=True,
    )

    # Simulate a later production hotfix wrapping the explorer source. The topic
    # installer must still recognize its durable markers and remain idempotent.
    explorer_path = work / "content" / "candidate_explorer.py"
    explorer_path.write_text(
        explorer_path.read_text(encoding="utf-8")
        + "\n# DOWNSTREAM_RUNTIME_WRAPPER_SIMULATION\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "ci_topic_input_hotfix.py"],
        cwd=work,
        check=True,
    )

    gate_after = hashlib.sha256(gate_path.read_bytes()).hexdigest()
    assert gate_before == gate_after, "Candidate Gate implementation changed"

    main_text = (work / "main.py").read_text(encoding="utf-8")
    explorer_text = (
        work / "content" / "candidate_explorer.py"
    ).read_text(encoding="utf-8")
    consensus_text = (
        work / "quality" / "consensus.py"
    ).read_text(encoding="utf-8")

    assert 'fixed_topic_gate_feedback = ""' in main_text
    assert "fixed_topic_gate_feedback = str(" in main_text
    assert "winner_gate.get(" in main_text
    assert "fixed_topic_gate_feedback=(" in main_text
    assert "if forced_topic" in main_text
    assert "# FIXED_TOPIC_HOOK_QUALITY_GUARD_V1" in consensus_text

    # Run 34641471858: Hook remained 6.0 after the one allowed rewrite.
    # The fixed-topic path must preserve the same Hook floor and rewrite cap,
    # then reuse the already-bounded Candidate regeneration path.
    assert "# FIXED_TOPIC_HOOK_EXHAUSTION_RECOVERY_V1" in main_text
    assert 'consensus.get("fixed_topic_hook_floor_miss")' in main_text
    assert '"status": "REGENERATE_TOPIC"' in main_text
    assert 'rewritten["fixed_topic_hook_floor_miss"] = True' in consensus_text
    assert 'GOOD_ENOUGH_FLOORS.get("hook", 0.0)' in consensus_text
    assert "MAX_REWRITES = 1" in main_text
    assert "MAX_REWRITES = 2" not in main_text

    assert "[PREVIOUS CANDIDATE GATE FEEDBACK]" in explorer_text
    assert "{fixed_topic_gate_feedback}" in explorer_text
    assert "같은 Core Question" in explorer_text
    assert "Candidate Gate와 기존 품질 규칙은 그대로 적용한다." in explorer_text
    assert 'fixed_topic_gate_feedback=""' in explorer_text

    # The fixed-topic installer must preserve whatever retry policy the upstream
    # production hotfix stack selected. Do not pin this regression to a stale value.
    assert retry_policy(main_text) == retry_before
    assert "evaluate_candidate(" in main_text

    py_compile.compile(str(work / "main.py"), doraise=True)
    py_compile.compile(
        str(work / "content" / "candidate_explorer.py"),
        doraise=True,
    )
    py_compile.compile(str(work / "quality" / "consensus.py"), doraise=True)

print("fixed-topic gate feedback regression: PASS")
