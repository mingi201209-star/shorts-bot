"""Clean V2 Quality Core.

This package is a from-scratch, isolated implementation of the
Candidate -> Grounding -> ScriptPlan -> VisualPlan -> VisualQA pipeline.

It is not wired into the production hotfix chain and does not modify any
file outside this package. It runs only when explicitly enabled:

    ENABLE_QUALITY_CORE_V2=1

The default (unset / any other value) leaves the existing V1 path
(main.py's Candidate Loop + the ci_*_hotfix.py chain) completely untouched.

See quality_core_v2/replay.py for the offline, zero-network-call replay
harness that regresses this package's deterministic gates against fixture
data captured from real production failures.
"""

import os

QUALITY_CORE_V2_VERSION = 1


def is_enabled() -> bool:
    """Whether the V2 pipeline should run instead of the frozen V1 path.

    Pure env-var check, no side effects. Callers in main.py (a later,
    separate phase) are expected to branch on this before doing anything
    V2-specific, and to do nothing here otherwise.
    """
    return os.environ.get("ENABLE_QUALITY_CORE_V2") == "1"
