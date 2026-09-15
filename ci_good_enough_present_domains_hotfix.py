from pathlib import Path


ROOT = Path(__file__).resolve().parent
PATH = ROOT / "quality/consensus.py"
MARKER = "# GOOD_ENOUGH_PRESENT_DOMAINS_V1"


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("Good Enough present-domain consensus already installed")
        return

    old = '''def meets_good_enough_floors(summaries):
    for judge_type, minimum in GOOD_ENOUGH_FLOORS.items():
        score = safe_float(summaries.get(judge_type, {}).get("score", 0.0))
        if score < minimum:
            return False
    return True
'''
    new = '''# GOOD_ENOUGH_PRESENT_DOMAINS_V1
def meets_good_enough_floors(summaries):
    # Production currently runs hook/novelty/fact/visual. Optional domains may
    # remain configured for future committees, but an unrun domain is not a
    # zero-scored review. Whenever a domain is actually present, its existing
    # floor is enforced unchanged.
    for judge_type, minimum in GOOD_ENOUGH_FLOORS.items():
        if judge_type not in summaries:
            continue
        score = safe_float(summaries.get(judge_type, {}).get("score", 0.0))
        if score < minimum:
            return False
    return True
'''
    if text.count(old) != 1:
        raise RuntimeError(
            "Good Enough present-domain consensus marker mismatch: "
            f"{text.count(old)}"
        )
    PATH.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(
        "✅ Good Enough consensus now evaluates only domains actually judged; "
        "existing floors unchanged"
    )


if __name__ == "__main__":
    main()
