import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _summary(score):
    return {
        "score": float(score),
        "adjusted_score": float(score),
        "confidence": 0.9,
        "disagreement": 0.0,
        "critical_risk": False,
        "review_count": 1,
        "issues": [],
        "reliability": 1.0,
    }


def _reload_consensus():
    sys.modules.pop("quality.consensus", None)
    return importlib.import_module("quality.consensus")


def test_before_fix_reproduces_unrun_explanation_as_zero():
    consensus = _reload_consensus()
    source = (ROOT / "quality/consensus.py").read_text(encoding="utf-8")
    if "# GOOD_ENOUGH_PRESENT_DOMAINS_V1" in source:
        return
    summaries = {
        "hook": _summary(7.0),
        "novelty": _summary(5.0),
        "fact": _summary(7.0),
        "visual": _summary(7.0),
    }
    assert consensus.meets_good_enough_floors(summaries) is False


def test_four_domain_production_committee_can_meet_good_enough():
    from ci_good_enough_present_domains_hotfix import main as install

    install()
    consensus = _reload_consensus()
    summaries = {
        "hook": _summary(7.0),
        "novelty": _summary(5.0),
        "fact": _summary(7.0),
        "visual": _summary(7.0),
    }
    assert consensus.meets_good_enough_floors(summaries) is True


def test_present_optional_domain_keeps_existing_floor():
    consensus = _reload_consensus()
    passing = {
        "hook": _summary(7.0),
        "novelty": _summary(5.0),
        "fact": _summary(7.0),
        "visual": _summary(7.0),
        "explanation": _summary(6.5),
    }
    failing = dict(passing)
    failing["explanation"] = _summary(6.49)
    assert consensus.meets_good_enough_floors(passing) is True
    assert consensus.meets_good_enough_floors(failing) is False


def test_present_production_domain_floor_is_not_weakened():
    consensus = _reload_consensus()
    summaries = {
        "hook": _summary(6.99),
        "novelty": _summary(10.0),
        "fact": _summary(10.0),
        "visual": _summary(10.0),
    }
    assert consensus.meets_good_enough_floors(summaries) is False


def test_current_production_committee_is_four_domains():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index("JUDGE_TYPES = [")
    end = source.index("]", start)
    block = source[start:end]
    for domain in ("hook", "novelty", "fact", "visual"):
        assert f'"{domain}"' in block
    assert '"explanation"' not in block


def test_final_hotfix_chain_wires_consensus_fix():
    source = (ROOT / "ci_run_34672661458_hook_floor_feedback_hotfix.py").read_text(
        encoding="utf-8"
    )
    assert "def _install_good_enough_present_domains()" in source
    assert "_install_good_enough_present_domains()" in source


def test_thresholds_and_budgets_unchanged():
    consensus = _reload_consensus()
    assert consensus.GOOD_ENOUGH_SCORE == 6.8
    assert consensus.GOOD_ENOUGH_FLOORS == {
        "hook": 7.0,
        "novelty": 5.0,
        "fact": 7.0,
        "visual": 7.0,
        "explanation": 6.5,
    }
    installer = (ROOT / "ci_good_enough_present_domains_hotfix.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "GOOD_ENOUGH_SCORE =",
        "GOOD_ENOUGH_FLOORS =",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
        "MAX_REWRITES =",
        "MAX_REVIEW_ROUNDS =",
    ):
        assert forbidden not in installer


if __name__ == "__main__":
    tests = [
        test_before_fix_reproduces_unrun_explanation_as_zero,
        test_four_domain_production_committee_can_meet_good_enough,
        test_present_optional_domain_keeps_existing_floor,
        test_present_production_domain_floor_is_not_weakened,
        test_current_production_committee_is_four_domains,
        test_final_hotfix_chain_wires_consensus_fix,
        test_thresholds_and_budgets_unchanged,
    ]
    for test in tests:
        test()
    print("GOOD_ENOUGH_PRESENT_DOMAINS_REGRESSION: PASS")
