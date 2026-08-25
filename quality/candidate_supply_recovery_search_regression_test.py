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
    # call rather than growing retry/API spend or relaxing validation.
    assert "_candidate_supply_recovery_used = True" in text
    assert text.count("Candidate supply recovery API call authorized") == 1
    assert "return validate_explorer_output(parsed)" in text
    assert 'temperature=0.55' in text

    print("CANDIDATE SUPPLY RECOVERY SEARCH REGRESSION: PASS")


if __name__ == "__main__":
    main()
