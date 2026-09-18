"""Counterexample regression for the Phase 0 stable-engine gate breakage.

Authority: `main` HEAD `08f7c180b45e41a1e558862efda73fe7d0f1b01a`. Running the
eight literal assertions of `promote_publish_stable.yml` /
`publish_engine.yml` against that commit's own `.github/workflows/main.yml`
fails on exactly one:

    python ci_final_visual_semantic_qa_hotfix.py

Phase 0 (PR #420) removed that literal when it replaced the inline hotfix chain
with `python quality/apply_production_hotfix_chain.py`. Consequences observed at
that SHA: `main` cannot be promoted to `publish-stable`, and the publish engine
would refuse any promoted post-Phase-0 commit.

CASE A is that exact counterexample. CASE B pins the backward compatibility the
fix must not break, because the live `publish-stable` pointer is still a
pre-Phase-0 commit. CASES C-E pin that the gate did not simply get weaker.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.verify_stable_engine_contract import (  # noqa: E402
    CHAIN_RUNNER,
    REQUIRED_HOTFIX,
    chain_applies_hotfix,
    verify,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The literals publish_engine.yml asserts, minus the hotfix one this module
# now decides structurally.
PUBLISH_ENGINE_LITERALS = [
    "inputs.expected_sha || github.sha",
    "python -m diagnostics.runner",
    "final_visual_semantic_qa.json",
    "final_director_qa.json",
    "youtube_upload:",
    "youtube_privacy:",
]

PRE_PHASE0_WORKFLOW = """
      - name: Apply production hotfixes
        run: |
          python ci_hotfix.py
          python ci_final_visual_semantic_qa_hotfix.py
"""

POST_PHASE0_WORKFLOW = """
      - name: Apply production hotfixes
        run: |
          python quality/apply_production_hotfix_chain.py
"""

CHAIN_WITH_HOTFIX = (
    'PRODUCTION_HOTFIX_CHAIN = [\n'
    '    "ci_hotfix.py",\n'
    f'    "{REQUIRED_HOTFIX}",\n'
    ']\n'
)

CHAIN_WITHOUT_HOTFIX = (
    'PRODUCTION_HOTFIX_CHAIN = [\n'
    '    "ci_hotfix.py",\n'
    ']\n'
)

STRIPPED_WORKFLOW = """
      - name: Apply production hotfixes
        run: |
          echo "skipped"
"""


def _read(relative_path):
    with open(os.path.join(ROOT, relative_path), encoding="utf-8") as handle:
        return handle.read()


def case_a_current_main_is_promotable():
    """The exact counterexample: current main.yml + current chain must pass."""
    workflow = _read(".github/workflows/main.yml")
    chain = _read("quality/production_hotfix_chain.py")

    # Pin the breakage itself, so this test fails loudly if someone "fixes" the
    # gate by reintroducing the literal instead of reading the SSOT chain.
    assert f"python {REQUIRED_HOTFIX}" not in workflow, (
        "current main.yml unexpectedly contains the pre-Phase-0 literal; "
        "this regression's premise no longer holds"
    )
    assert CHAIN_RUNNER in workflow, "current main.yml must run the SSOT chain runner"

    failures = verify(workflow, chain, PUBLISH_ENGINE_LITERALS)
    assert not failures, f"current main is not promotable: {failures}"
    print("CASE A current main.yml is promotable via the SSOT chain: PASS")


def case_b_pre_phase0_stable_still_publishes():
    """The live publish-stable pointer predates Phase 0 and must still pass."""
    assert chain_applies_hotfix(PRE_PHASE0_WORKFLOW, None), (
        "a pre-Phase-0 stable commit must still satisfy the gate; "
        "publishing would otherwise stop immediately"
    )
    print("CASE B pre-Phase-0 stable commit still satisfies the gate: PASS")


def case_c_ssot_without_chain_file_is_rejected():
    """Delegating to the runner proves nothing without the chain module."""
    assert not chain_applies_hotfix(POST_PHASE0_WORKFLOW, None), (
        "a workflow that delegates to the chain runner must not pass when the "
        "chain module is unreadable at that commit"
    )
    print("CASE C SSOT delegation without a chain module is rejected: PASS")


def case_d_chain_missing_the_hotfix_is_rejected():
    """The guarantee is unchanged: the named hotfix must actually be listed."""
    assert chain_applies_hotfix(POST_PHASE0_WORKFLOW, CHAIN_WITH_HOTFIX)
    assert not chain_applies_hotfix(POST_PHASE0_WORKFLOW, CHAIN_WITHOUT_HOTFIX), (
        f"a chain that does not list {REQUIRED_HOTFIX} must be rejected"
    )
    print("CASE D chain omitting the required hotfix is rejected: PASS")


def case_e_stripped_workflow_is_rejected():
    """A workflow that applies no chain at all is still refused."""
    assert not chain_applies_hotfix(STRIPPED_WORKFLOW, CHAIN_WITH_HOTFIX)
    failures = verify(STRIPPED_WORKFLOW, CHAIN_WITH_HOTFIX, PUBLISH_ENGINE_LITERALS)
    assert failures, "a stripped workflow must fail the contract"
    print("CASE E stripped workflow is rejected: PASS")


def case_f_gates_delegate_to_this_module():
    """Both gates must call the shared verifier, so they cannot drift apart."""
    for workflow_name in ("promote_publish_stable.yml", "publish_engine.yml"):
        text = _read(os.path.join(".github/workflows", workflow_name))
        assert "quality/verify_stable_engine_contract.py" in text, (
            f"{workflow_name} must delegate to the shared stable-engine verifier"
        )
        assert f"grep -F 'python {REQUIRED_HOTFIX}'" not in text, (
            f"{workflow_name} still carries the stale Phase 0 literal grep"
        )
    print("CASE F both gates delegate to the shared verifier: PASS")


if __name__ == "__main__":
    case_a_current_main_is_promotable()
    case_b_pre_phase0_stable_still_publishes()
    case_c_ssot_without_chain_file_is_rejected()
    case_d_chain_missing_the_hotfix_is_rejected()
    case_e_stripped_workflow_is_rejected()
    case_f_gates_delegate_to_this_module()
    print("stable engine contract regression: PASS")
