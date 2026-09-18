"""Dedicated runner for the production hotfix chain (Publish Engine
Stabilization V1, Phase 0).

Chain *definition* (`quality/production_hotfix_chain.py`) and chain
*execution* (this file) are deliberately separate from a shell pipeline.
A `python -c "..." | while read -r f; do python "$f"; done` construction
risks swallowing a mid-chain failure through pipeline/subshell exit-code
semantics; this runner instead applies each entry via a real subprocess
call and stops immediately, with a non-zero exit and a clear message
naming the failing hotfix, the moment one fails.

Used by `.github/workflows/main.yml` and
`.github/workflows/production_hotfix_composition_gate.yml` (both simply run
`python quality/apply_production_hotfix_chain.py`), so those two workflows
are structurally identical by construction rather than by manual sync.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Running this file directly (`python quality/apply_production_hotfix_chain.py`,
# as both main.yml and production_hotfix_composition_gate.yml do) puts only
# this file's own directory on sys.path, not the repo root -- so the package
# import below needs the repo root added explicitly first.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.production_hotfix_chain import PRODUCTION_HOTFIX_CHAIN  # noqa: E402


def apply_chain() -> None:
    applied: list[str] = []
    for hotfix in PRODUCTION_HOTFIX_CHAIN:
        result = subprocess.run(
            [sys.executable, hotfix],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print(
                f"[PRODUCTION_HOTFIX_CHAIN] FAILED at step {len(applied) + 1}/"
                f"{len(PRODUCTION_HOTFIX_CHAIN)}: {hotfix} "
                f"(exit code {result.returncode})",
                file=sys.stderr,
            )
            print(
                "[PRODUCTION_HOTFIX_CHAIN] applied before failure: "
                + ", ".join(applied) if applied else
                "[PRODUCTION_HOTFIX_CHAIN] failed on the first entry",
                file=sys.stderr,
            )
            sys.exit(result.returncode)
        applied.append(hotfix)

    print(
        f"[PRODUCTION_HOTFIX_CHAIN] applied all {len(applied)} hotfixes "
        "in order:"
    )
    for index, hotfix in enumerate(applied):
        print(f"  {index}: {hotfix}")


if __name__ == "__main__":
    apply_chain()
