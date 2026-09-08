"""Regression for child Run 34234565536 pre-Writer grounding loss.

A fixed-topic retry may produce a new Candidate after the Explorer validation
wrapper already supplied trusted identity. The production chain must re-apply
repo-owned trusted grounding before the existing pre-Writer gate, without
weakening that gate or adding calls/retries.
"""

from pathlib import Path
import subprocess
import sys


def run():
    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)

    main_source = Path("main.py").read_text(encoding="utf-8")
    assert main_source.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1
    assert "supply_trusted_subject_grounding(" in main_source
    assert "candidate.clear()" in main_source
    assert "candidate.update(supplied)" in main_source
    assert main_source.index("# CANONICAL_SUBJECT_GROUNDING_GATE_V1") < main_source.index(
        "# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1"
    )

    supply_source = Path("quality/canonical_subject_grounding_supply.py").read_text(
        encoding="utf-8"
    )
    assert supply_source.count("# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1") == 1

    # Idempotence: the production installer chain may be exercised repeatedly
    # by composition/regression jobs and must not stack wrappers.
    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)
    main_source_2 = Path("main.py").read_text(encoding="utf-8")
    assert main_source_2.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1

    # Safety invariants: this fix does not alter the canonical gate itself and
    # introduces no model/API call, retry, threshold, or budget override.
    hotfix_source = Path("ci_prewriter_grounding_resupply_hotfix.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "openai.chat",
        "authorize_call(",
        "MAX_TOPIC_REGENERATIONS",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
    )
    for token in forbidden:
        assert token not in hotfix_source, token

    print("PREWRITER TRUSTED GROUNDING RESUPPLY REGRESSION: PASS")


if __name__ == "__main__":
    run()
