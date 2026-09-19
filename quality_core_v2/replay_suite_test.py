"""pytest entry point for the offline Replay/Shadow Harness.

    pytest quality_core_v2/replay_suite_test.py

Each fixture becomes its own parametrized test case (readable failure
output, one row per regression) instead of one big pass/fail blob.
Zero network access; safe to run in every CI job, unconditionally.
"""

import pytest

from quality_core_v2.replay import FIXTURES_DIR, _run_fixture, load_fixtures

_FIXTURES = load_fixtures(FIXTURES_DIR)


@pytest.mark.parametrize(
    "fixture",
    _FIXTURES,
    ids=[f'{fx.get("category", "?")}::{fx.get("name", "?")}' for fx in _FIXTURES],
)
def test_replay_fixture(fixture):
    result = _run_fixture(fixture)
    assert result.ok, result.detail


def test_at_least_one_fixture_per_required_category():
    """Guards against the fixture directory silently losing coverage."""
    required_substrings = [
        "wing flex", "window", "spoiler", "chevron", "static wick",
        "generic aircraft B-roll", "cross-domain", "phenomenon missing",
        "mechanism not visible", "duplicate claims", "adjacent scene",
        "broad/generic reveal", "malformed Candidate", "subject drift",
        "fallback semantic degradation", "provider miss", "stale",
    ]
    haystack = " | ".join(
        f'{fx.get("category", "")} {fx.get("name", "")} {fx.get("provenance", "")}'
        for fx in _FIXTURES
    ).lower()
    missing = [s for s in required_substrings if s.lower() not in haystack]
    assert not missing, f"no fixture covers required category/ies: {missing}"
