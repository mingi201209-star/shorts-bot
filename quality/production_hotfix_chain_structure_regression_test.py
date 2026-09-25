"""Structural regression for the production hotfix chain single source of
truth (Publish Engine Stabilization V1, Phase 0).

Authority: this repo previously had three mutually inconsistent copies of
"the production hotfix chain" -- .github/workflows/main.yml (the one that
actually runs in production), .github/workflows/production_hotfix_composition_gate.yml
(diverged from main.yml at index 46: it ran
ci_run_33977099845_verified_still_rescue_hotfix.py where main.yml ran
ci_grounded_deterministic_explanation_hotfix.py), and
quality/script_human_quality_v1_regression_test.py's own hard-coded list (4
hotfixes short of the real chain, dropping two different files than the
composition gate's divergence). quality/production_hotfix_chain.py is now
the single place the chain is defined; all three now read it instead of
each hard-coding their own copy.

This test asserts the chain's exact structural shape -- not a loose
"duplicates are allowed" allowlist, which would silently accept a *third*
accidental copy of some hotfix later -- and separately confirms both
workflow files actually invoke the shared runner rather than a
re-hard-coded list.

IMPORTANT: the "exactly 49 entries, exactly one intentional duplicate"
shape asserted here is a PRE-CONSOLIDATION invariant, not a permanent
production requirement. Publish Engine Stabilization V1's Phase 3 absorbs
these hotfixes into checked-in source, which shrinks this list by design.
When that happens, this test must be updated (or retired) in the same
cluster PR that does the absorbing -- see quality/production_hotfix_chain.py's
own docstring for the same note.
"""
from pathlib import Path

from quality.production_hotfix_chain import PRODUCTION_HOTFIX_CHAIN

ROOT = Path(__file__).resolve().parents[1]

_EXPECTED_LENGTH = 49
_EXPECTED_DUPLICATE = "ci_aviation_context_signature_compat_hotfix.py"
_EXPECTED_DUPLICATE_FIRST_INDEX = 13


def case_a_exact_length():
    assert len(PRODUCTION_HOTFIX_CHAIN) == _EXPECTED_LENGTH, (
        f"expected exactly {_EXPECTED_LENGTH} entries, got "
        f"{len(PRODUCTION_HOTFIX_CHAIN)}"
    )
    print(f"CASE A chain has exactly {_EXPECTED_LENGTH} entries: PASS")


def case_b_every_entry_exists_at_repo_root():
    missing = [entry for entry in PRODUCTION_HOTFIX_CHAIN if not (ROOT / entry).is_file()]
    assert not missing, f"missing hotfix files: {missing}"
    print("CASE B every listed hotfix file exists at the repo root: PASS")


def case_c_exactly_one_intentional_duplicate_at_exact_positions():
    counts = {}
    for entry in PRODUCTION_HOTFIX_CHAIN:
        counts[entry] = counts.get(entry, 0) + 1

    duplicated = {name: count for name, count in counts.items() if count > 1}
    assert duplicated == {_EXPECTED_DUPLICATE: 2}, (
        f"expected exactly one duplicate ({_EXPECTED_DUPLICATE!r}, count 2), "
        f"found: {duplicated}"
    )

    positions = [i for i, entry in enumerate(PRODUCTION_HOTFIX_CHAIN) if entry == _EXPECTED_DUPLICATE]
    assert positions == [_EXPECTED_DUPLICATE_FIRST_INDEX, len(PRODUCTION_HOTFIX_CHAIN) - 1], (
        f"expected {_EXPECTED_DUPLICATE!r} at indices "
        f"[{_EXPECTED_DUPLICATE_FIRST_INDEX}, {len(PRODUCTION_HOTFIX_CHAIN) - 1}], "
        f"found at {positions}"
    )
    print(
        "CASE C exactly one intentional duplicate "
        f"({_EXPECTED_DUPLICATE}) at documented first index "
        f"({_EXPECTED_DUPLICATE_FIRST_INDEX}) and the list's last index: PASS"
    )


def case_d_workflows_invoke_shared_runner_not_a_hardcoded_list():
    runner_call = "python quality/apply_production_hotfix_chain.py"
    main_yml = (ROOT / ".github" / "workflows" / "main.yml").read_text(encoding="utf-8")
    gate_yml = (ROOT / ".github" / "workflows" / "production_hotfix_composition_gate.yml").read_text(encoding="utf-8")

    assert runner_call in main_yml, "main.yml does not invoke the shared hotfix chain runner"
    assert runner_call in gate_yml, "production_hotfix_composition_gate.yml does not invoke the shared hotfix chain runner"

    # No individually hard-coded `python ci_*.py` chain-application lines
    # should remain in either workflow's hotfix-apply step -- only the
    # single runner call. (grep-style check does not distinguish comments,
    # but this repo's hotfix scripts are all invoked as `python ci_*.py`
    # with no other legitimate use of that exact pattern in these files.)
    for name, text in (("main.yml", main_yml), ("production_hotfix_composition_gate.yml", gate_yml)):
        hardcoded_calls = [
            line.strip() for line in text.splitlines()
            if line.strip().startswith("python ci_") and line.strip() != runner_call
        ]
        assert not hardcoded_calls, f"{name} still has hard-coded hotfix calls: {hardcoded_calls}"

    print("CASE D both workflows invoke the shared runner, not a re-hardcoded list: PASS")


def main():
    case_a_exact_length()
    case_b_every_entry_exists_at_repo_root()
    case_c_exactly_one_intentional_duplicate_at_exact_positions()
    case_d_workflows_invoke_shared_runner_not_a_hardcoded_list()
    print("PRODUCTION HOTFIX CHAIN STRUCTURE REGRESSION: PASS")


if __name__ == "__main__":
    main()
