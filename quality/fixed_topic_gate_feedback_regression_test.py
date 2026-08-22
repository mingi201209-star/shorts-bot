from pathlib import Path
import hashlib
import py_compile
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    (work / "content").mkdir()
    shutil.copy2(ROOT / "main.py", work / "main.py")
    shutil.copy2(
        ROOT / "content" / "candidate_explorer.py",
        work / "content" / "candidate_explorer.py",
    )
    shutil.copy2(
        ROOT / "ci_topic_input_hotfix.py",
        work / "ci_topic_input_hotfix.py",
    )

    gate_path = ROOT / "content" / "candidate_gate.py"
    gate_before = hashlib.sha256(gate_path.read_bytes()).hexdigest()

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

    assert 'fixed_topic_gate_feedback = ""' in main_text
    assert "fixed_topic_gate_feedback = str(" in main_text
    assert "winner_gate.get(" in main_text
    assert "fixed_topic_gate_feedback=(" in main_text
    assert "if forced_topic" in main_text

    assert "[PREVIOUS CANDIDATE GATE FEEDBACK]" in explorer_text
    assert "{fixed_topic_gate_feedback}" in explorer_text
    assert "같은 Core Question" in explorer_text
    assert "Candidate Gate와 기존 품질 규칙은 그대로 적용한다." in explorer_text
    assert 'fixed_topic_gate_feedback=""' in explorer_text

    # Existing retry and quality contracts stay intact.
    assert "MAX_TOPIC_REGENERATIONS = 1" in main_text
    assert "evaluate_candidate(" in main_text

    py_compile.compile(str(work / "main.py"), doraise=True)
    py_compile.compile(
        str(work / "content" / "candidate_explorer.py"),
        doraise=True,
    )

print("fixed-topic gate feedback regression: PASS")
