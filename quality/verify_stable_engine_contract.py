"""Decide whether a candidate stable-engine commit's `main.yml` is self-contained.

Publish Engine Stabilization V1 Phase 0 (PR #420) replaced `main.yml`'s inline
`python ci_<name>_hotfix.py` chain with a single
`python quality/apply_production_hotfix_chain.py` call. Both
`promote_publish_stable.yml` and `publish_engine.yml` asserted the chain was
actually applied by grepping the candidate `main.yml` for the literal
`python ci_final_visual_semantic_qa_hotfix.py` -- a literal Phase 0 removed.

That literal is absent from every commit at or after PR #420, so both gates now
fail closed against current `main`: `main` can no longer be promoted to
`publish-stable`, and no post-Phase-0 commit can be published. Verified against
`main` HEAD `08f7c180b45e41a1e558862efda73fe7d0f1b01a`, where that one grep is
the only failing assertion of the eight.

This module is the single place that decides whether a candidate `main.yml`
applies the production hotfix chain. It accepts BOTH shapes on purpose:

- pre-Phase-0 (inline): `main.yml` itself runs `python <hotfix>`.
- post-Phase-0 (SSOT): `main.yml` runs
  `python quality/apply_production_hotfix_chain.py`, and
  `quality/production_hotfix_chain.py` AT THAT SAME COMMIT lists `<hotfix>`.

Accepting both is required rather than lenient. The current `publish-stable`
pointer is a pre-Phase-0 commit, so a gate demanding only the new shape would
stop publishing immediately; a gate demanding only the old shape -- today's
behaviour -- can never accept a promotion again. The guarantee is unchanged:
the named hotfix must still be applied by the promoted commit. What changes is
that the gate now reads the SSOT chain list when the chain is applied through
it, instead of reading a literal that no longer exists.

Both workflows call this module so the two gates cannot drift apart, which is
the same failure mode Phase 0 found among the three hand-maintained copies of
the chain itself.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

#: The hotfix whose application the stable-engine gates have always asserted.
REQUIRED_HOTFIX = "ci_final_visual_semantic_qa_hotfix.py"

#: main.yml runs the chain through this script at and after Phase 0.
CHAIN_RUNNER = "python quality/apply_production_hotfix_chain.py"


def chain_applies_hotfix(
    workflow_text: str,
    chain_text: Optional[str] = None,
    hotfix: str = REQUIRED_HOTFIX,
) -> bool:
    """True when `workflow_text` provably applies `hotfix`.

    `chain_text` is `quality/production_hotfix_chain.py` read at the same
    commit as `workflow_text`, or None when that commit has no such file
    (every pre-Phase-0 commit).
    """
    # Pre-Phase-0: the workflow runs the hotfix directly.
    if f"python {hotfix}" in workflow_text:
        return True

    # Post-Phase-0: the workflow delegates to the SSOT runner, so the proof
    # lives in the chain module at that same commit. A missing chain module is
    # not a pass -- without it nothing shows the hotfix is in the chain.
    if CHAIN_RUNNER in workflow_text and chain_text:
        return hotfix in chain_text

    return False


def verify(
    workflow_text: str,
    chain_text: Optional[str],
    required_literals: List[str],
    hotfix: str = REQUIRED_HOTFIX,
) -> List[str]:
    """Return a list of human-readable failures; empty means the contract holds."""
    failures = [
        f"missing required literal: {literal}"
        for literal in required_literals
        if literal not in workflow_text
    ]

    if not chain_applies_hotfix(workflow_text, chain_text, hotfix):
        failures.append(
            f"candidate does not apply {hotfix}: the workflow neither runs it "
            f"directly nor delegates to '{CHAIN_RUNNER}' with {hotfix} listed "
            "in quality/production_hotfix_chain.py at the same commit"
        )

    return failures


def _read(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a candidate stable-engine main.yml contract.",
    )
    parser.add_argument("--workflow", required=True, help="candidate main.yml path")
    parser.add_argument(
        "--chain",
        default=None,
        help="candidate quality/production_hotfix_chain.py path (absent pre-Phase-0)",
    )
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        dest="required",
        metavar="LITERAL",
        help="literal that must appear in the candidate main.yml (repeatable)",
    )
    parser.add_argument("--hotfix", default=REQUIRED_HOTFIX)
    args = parser.parse_args(argv)

    workflow_text = _read(args.workflow)
    if workflow_text is None:
        print(
            f"[STABLE_ENGINE_CONTRACT] FAIL: candidate workflow not readable: "
            f"{args.workflow}",
            file=sys.stderr,
        )
        return 1

    failures = verify(workflow_text, _read(args.chain), args.required, args.hotfix)
    if failures:
        for failure in failures:
            print(f"[STABLE_ENGINE_CONTRACT] FAIL: {failure}", file=sys.stderr)
        return 1

    shape = "inline" if f"python {args.hotfix}" in workflow_text else "ssot-chain"
    print(f"[STABLE_ENGINE_CONTRACT] PASS shape={shape} hotfix={args.hotfix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
