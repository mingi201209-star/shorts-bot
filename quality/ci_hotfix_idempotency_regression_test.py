"""Regression: `ci_hotfix.py` (chain step 1/47) must survive being applied
twice to the same checkout without raising.

Authority: this session's investigation (2026-09-19) found that applying
the full production hotfix chain to a clean checkout, then applying it a
SECOND time, dies immediately on `ci_hotfix.py` with
`RuntimeError: main.py Review limit fallback 패치 대상이 정확히 1개가 아닙니다.
(count=0)`. Two of this file's patches (the "Review limit fallback"
regex-substitution and the "Script Generator fallback" marker-replace) had
no "already applied" guard, unlike this same file's other patches -- so a
second run's regex/literal search against already-patched text finds
count=0 and raises, instead of recognizing the target state is already in
place.

This matters beyond an artificial "run it twice" scenario: Publish Engine
Stabilization V1's Phase 3 plan is to absorb hotfixes into checked-in
source. The moment a hotfix's target text already lives in `main.py`
(because a previous PR merged the absorption) but the hotfix script itself
still runs, the effect is identical to running it a second time -- so
without this guard, the FIRST Phase-3 absorption that touches `main.py`'s
review-fallback or script-fallback blocks aborts the entire 47-step chain
at step 1, exactly the failure mode already hit once before with
`main.py`'s Candidate Loop (see quality/production_hotfix_chain.py's
sibling investigation notes).

The full chain is NOT yet idempotent end-to-end -- several of the other 34
hotfixes with hard `count == 1` assertions have the same missing-guard
shape, and some of THOSE guards are further complicated by a downstream
hotfix in the same run rewriting the exact region an earlier hotfix's own
"already applied" check depends on (confirmed with
`ci_speech_style_hotfix.py` vs `ci_output_quality_hotfix.py`). Fixing
those needs individual verification per file, not a blanket pass, so this
test intentionally scopes to `ci_hotfix.py` only -- the chain's first
entry, and the one already proven to break production the moment its
patch target is absorbed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "ci_hotfix.py"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def case_a_second_application_does_not_raise():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        # Only the files ci_hotfix.py actually touches, plus itself, so this
        # stays fast and has no dependency on the rest of the chain having
        # run first.
        needed = [
            "ci_hotfix.py",
            "main.py",
            "config.py",
            "content/candidate_explorer.py",
            "content/script_generator.py",
            "quality/consensus.py",
            "quality/rewrite_engine.py",
        ]
        for rel in needed:
            src = ROOT / rel
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        first = _run(work)
        assert first.returncode == 0, (
            "ci_hotfix.py failed on a CLEAN checkout (should always succeed):\n"
            f"stdout:\n{first.stdout}\nstderr:\n{first.stderr}"
        )

        second = _run(work)
        assert second.returncode == 0, (
            "ci_hotfix.py raised on a SECOND application against its own "
            "already-patched output -- this is the exact failure mode that "
            "would abort the whole 47-step chain the moment any of this "
            "file's patch targets are absorbed into checked-in source:\n"
            f"stdout:\n{second.stdout}\nstderr:\n{second.stderr}"
        )
    print("CASE A ci_hotfix.py applied twice in a row does not raise: PASS")


def main():
    case_a_second_application_does_not_raise()
    print("ci_hotfix.py idempotency regression: PASS")


if __name__ == "__main__":
    main()
