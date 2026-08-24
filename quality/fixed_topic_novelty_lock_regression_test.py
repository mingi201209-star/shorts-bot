from pathlib import Path
import py_compile
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def committed_text(path):
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def novelty_threshold(text):
    match = re.search(
        r"^NOVELTY_HARD_REGENERATE_SCORE\s*=\s*([0-9.]+)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "NOVELTY_HARD_REGENERATE_SCORE assignment missing"
    return float(match.group(1))


with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    (work / "content").mkdir()

    main_before = committed_text("main.py")
    threshold_before = novelty_threshold(main_before)

    (work / "main.py").write_text(main_before, encoding="utf-8")
    (work / "content" / "candidate_explorer.py").write_text(
        committed_text("content/candidate_explorer.py"),
        encoding="utf-8",
    )
    (work / "ci_topic_input_hotfix.py").write_text(
        committed_text("ci_topic_input_hotfix.py"),
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, "ci_topic_input_hotfix.py"],
        cwd=work,
        check=True,
    )

    main_after = (work / "main.py").read_text(encoding="utf-8")

    # Run 32698901759 contract: a pinned topic must not rediscover the same topic
    # indefinitely when REGENERATE_TOPIC is caused by Novelty alone.
    lock_marker = "🔒 FIXED TOPIC NOVELTY LOCK"
    assert lock_marker in main_after
    assert "forced_topic" in main_after
    assert 'status == "REGENERATE_TOPIC"' in main_after
    assert '"Novelty" in str(' in main_after
    assert '!= "FACT_CRITICAL"' in main_after
    assert "final_script = fixed_topic_script" in main_after

    # The lock must run before the ordinary regeneration branch can continue.
    lock_pos = main_after.index(lock_marker)
    ordinary_regen_pos = main_after.index(
        "♻️ CANDIDATE REGENERATION",
        lock_pos,
    )
    assert lock_pos < ordinary_regen_pos

    # Automatic discovery behavior and the global novelty floor are unchanged.
    assert novelty_threshold(main_after) == threshold_before
    assert "Candidate Explorer 재탐색" in main_after
    assert "has_hard_novelty_failure" in main_after

    # Fixed-topic identity remains fail-close: the locked script must match the
    # exact requested production topic before it can be accepted.
    assert "fixed_script_topic != forced_topic" in main_after
    assert "production 주제와 다릅니다" in main_after

    py_compile.compile(str(work / "main.py"), doraise=True)
    py_compile.compile(
        str(work / "content" / "candidate_explorer.py"),
        doraise=True,
    )

print("fixed-topic novelty lock regression: PASS")
