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
from quality.production_execution_trace import (  # noqa: E402
    changed_symbols,
    record_event,
    snapshot_tree,
)


def _source_texts(snapshot: dict[str, dict[str, object]]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for rel, info in snapshot.items():
        if not rel.endswith(".py") or not info.get("exists"):
            continue
        try:
            texts[rel] = (ROOT / rel).read_text(encoding="utf-8")
        except Exception:
            texts[rel] = ""
    return texts


def _changed_files(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
    before_texts: dict[str, str],
) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel, {})
        new = after.get(rel, {})
        if old.get("sha256") == new.get("sha256") and old.get("exists") == new.get("exists"):
            continue
        symbols: list[str] = []
        if rel.endswith(".py"):
            try:
                after_text = (ROOT / rel).read_text(encoding="utf-8") if new.get("exists") else ""
                symbols = changed_symbols(before_texts.get(rel, ""), after_text)
            except Exception:
                symbols = []
        changes.append(
            {
                "path": rel,
                "before_sha256": old.get("sha256"),
                "after_sha256": new.get("sha256"),
                "before_size": old.get("size"),
                "after_size": new.get("size"),
                "changed_symbols": symbols,
            }
        )
    return changes


def apply_chain() -> None:
    applied: list[str] = []
    record_event(
        "hotfix_chain_start",
        total=len(PRODUCTION_HOTFIX_CHAIN),
        order=list(PRODUCTION_HOTFIX_CHAIN),
    )
    for hotfix in PRODUCTION_HOTFIX_CHAIN:
        before = snapshot_tree(ROOT)
        before_texts = _source_texts(before)
        record_event(
            "hotfix_start",
            index=len(applied),
            total=len(PRODUCTION_HOTFIX_CHAIN),
            hotfix=hotfix,
            input_fingerprint=before.get(hotfix, {}),
        )
        result = subprocess.run(
            [sys.executable, hotfix],
            cwd=ROOT,
        )
        after = snapshot_tree(ROOT)
        changes = _changed_files(before, after, before_texts)
        record_event(
            "hotfix_end",
            index=len(applied),
            total=len(PRODUCTION_HOTFIX_CHAIN),
            hotfix=hotfix,
            returncode=result.returncode,
            changed_files=changes,
            changed_file_count=len(changes),
            fallback_detected=False,
            retry_detected=False,
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
            record_event(
                "hotfix_chain_failed",
                failed_index=len(applied),
                failed_hotfix=hotfix,
                applied=list(applied),
                returncode=result.returncode,
            )
            sys.exit(result.returncode)
        applied.append(hotfix)

    print(
        f"[PRODUCTION_HOTFIX_CHAIN] applied all {len(applied)} hotfixes "
        "in order:"
    )
    for index, hotfix in enumerate(applied):
        print(f"  {index}: {hotfix}")
    record_event("hotfix_chain_complete", applied=list(applied))


if __name__ == "__main__":
    apply_chain()
