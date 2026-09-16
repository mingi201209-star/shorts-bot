from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOTFIX = ROOT / "ci_candidate_supply_recovery_hotfix.py"


def main():
    text = HOTFIX.read_text(encoding="utf-8")

    assert "silently explore at least 6 materially distinct" in text
    assert "A weak first idea" in text
    assert "SAME hard gates" in text
    assert "Return REGENERATE only after the silent breadth search" in text

    # Reliability improvement must reuse the existing single bounded recovery
    # opportunity rather than growing retry/API spend or relaxing validation.
    # Run 35063499913 composes a final wrapper for scope-correct prompting, so
    # static function-body string counts are no longer a valid proxy for runtime
    # call count. The actual one-call behavior is asserted dynamically by
    # candidate_grounded_recovery_regression_test CASE J.
    assert text.count("_candidate_supply_recovery_used = True") == 1
    assert "RUN_35063499913_SUPPLY_GROUNDING_V1" in text
    assert "_candidate_supply_recovery_system_prompt()" in text
    assert "return validate_explorer_output(parsed)" in text
    assert 'temperature=0.55' in text

    print("CANDIDATE SUPPLY RECOVERY SEARCH REGRESSION: PASS")


if __name__ == "__main__":
    main()
