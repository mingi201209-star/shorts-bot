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


def topic_direction_from_environment() -> str:
    """Pure: the same SHORTS_TOPIC env var V1's ci_topic_input_hotfix.py
    reads for its `forced_topic`. main.py's V2 guard clause was calling
    run_v2_pipeline() with no topic at all, so the Explorer always received
    an empty topic_direction regardless of the workflow_dispatch `topic`
    input -- confirmed as the root cause of Golden E2E run 35430511093
    (Golden Topic "aircraft wing flex" dispatched, but Explorer produced an
    unrelated typhoon-domain Scene 1, which then failed subject-anchor
    enforcement with an empty keyword). Fixed by reading it here instead.
    """
    return os.environ.get("SHORTS_TOPIC", "").strip()
