from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    supply = (ROOT / "ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
    assert "fixed_topic=None" in supply
    assert "fixed_topic_gate_feedback=\"\"" in supply
    assert "fixed_topic=fixed_topic" in supply
    assert "fixed_topic_gate_feedback=fixed_topic_gate_feedback" in supply

    compat = (ROOT / "ci_aviation_context_signature_compat_hotfix.py").read_text(encoding="utf-8")
    assert "# CANDIDATE_SUPPLY_RECOVERY_V1" in compat
    assert "direct re-forward skipped" in compat

    print("CANDIDATE SUPPLY PRODUCTION ORDER REGRESSION: PASS")


if __name__ == "__main__":
    main()
