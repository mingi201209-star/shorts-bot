from pathlib import Path


CONSENSUS_PATH = Path("quality/consensus.py")
MAIN_PATH = Path("main.py")
MARKER = "# RUN_34847558126_FIXED_TOPIC_NOVELTY_WEAK_DOMAIN_VISIBILITY_V1"
HARD_FAILURE_MARKER = "# RUN_34847558126_NOVELTY_HARD_FAILURE_BOUNDARY_V1"
HARD_FAILURE_ANCHOR = (
    "    if (\n"
    "        score\n"
    "        < NOVELTY_HARD_REGENERATE_SCORE\n"
    "    ):\n"
)
HARD_FAILURE_REPLACEMENT = (
    "    " + HARD_FAILURE_MARKER + "\n"
    "    # ci_hotfix.py lowers NOVELTY_HARD_REGENERATE_SCORE to 4.0, and Run\n"
    "    # 34847558126 / 34813429408 both show the Novelty Judge (gpt-4o-mini)\n"
    "    # landing on that exact round score. A strict `<` never catches a\n"
    "    # score sitting precisely on the threshold it was set to catch, so\n"
    "    # this systematically (not just occasionally) missed the one class\n"
    "    # of scores the check exists for. No threshold VALUE changes.\n"
    "    if (\n"
    "        score\n"
    "        <= NOVELTY_HARD_REGENERATE_SCORE\n"
    "    ):\n"
)
FIXED_TOPIC_ANCHOR = (
    'fixed_topic = __import__("os").environ.get("SHORTS_TOPIC", "").strip()'
)
RETURN_ANCHOR = (
    "    return {\n"
    '        "decision": decision,\n'
    '        "pass_tier": pass_tier,\n'
    '        "weighted_score": weighted_score,\n'
    '        "domain_summaries": summaries,\n'
    '        "disagreements": disagreements,\n'
    '        "low_confidence": low_confidence,\n'
    '        "critical_risks": critical_risks,\n'
    '        "low_reliability": low_reliability,\n'
    '        "weak_domains": weak_domains,\n'
    '        "reasons": reasons,\n'
    "    }\n"
)


def _replacement_block():
    return MARKER + r'''
    # Root Cause #2 (Content Quality Recovery round, Run 34847558126 /
    # 34813429408): both fixed-topic aviation canaries scored Novelty
    # 4.0/10 -- below the existing DOMAIN_REWRITE_FLOORS["novelty"] floor
    # of 5.0 -- across every rewrite/regenerate round, yet main.py's
    # has_hard_novelty_failure()/has_persistent_novelty_failure() (the
    # pre-existing "a very low Novelty score is a Candidate-selection
    # problem, not a wording problem -- return to Candidate Explorer before
    # spending a Rewrite" regeneration path) never fired for either run.
    #
    # Root cause: _apply_fixed_topic_soft_judges (ci_script_v2_visual_goal_
    # hotfix.py) intentionally builds weak_domains above from
    # decision_summaries, which is fact-only for an explicitly pinned
    # production topic so Hook/Novelty/Visual cannot flip the PASS/REWRITE
    # decision or silently swap the requested subject. A side effect: since
    # weak_domains can then never contain a "novelty" entry, the Novelty
    # regeneration path -- which reads consensus["weak_domains"] via
    # get_weak_domain(), not decision_summaries -- can never see that
    # Novelty is failing, no matter how low it scores.
    #
    # This block does NOT change weighted_score, pass_tier, decision, or
    # any floor/threshold value: those were already finalized above purely
    # from decision_summaries, unchanged. It only restores the Novelty
    # entry in the RETURNED weak_domains (using the SAME
    # DOMAIN_REWRITE_FLOORS["novelty"] value already authoritative in
    # free-topic mode -- no new number), so the pre-existing, already-
    # bounded Novelty regeneration path (one Candidate Explorer re-pass on
    # the SAME fixed topic, governed by the existing MAX_TOPIC_REGENERATIONS
    # ceiling -- no topic swap, no new API-call ceiling, no cost increase)
    # can see it, exactly as it already does for every non-fixed-topic
    # production.
    if fixed_topic and not any(
        item.get("judge_type") == "novelty" for item in weak_domains
    ):
        novelty_summary = summaries.get("novelty")
        if isinstance(novelty_summary, dict):
            novelty_score = safe_float(novelty_summary.get("score", 0.0))
            novelty_floor = DOMAIN_REWRITE_FLOORS.get(
                "novelty", DOMAIN_REWRITE_FLOOR
            )
            if novelty_score < novelty_floor:
                weak_domains = weak_domains + [{
                    "judge_type": "novelty",
                    "score": round(novelty_score, 3),
                    "minimum": novelty_floor,
                }]

'''


def _apply_consensus_patch():
    text = CONSENSUS_PATH.read_text(encoding="utf-8")

    if MARKER in text:
        print("✅ fixed-topic Novelty weak-domain visibility already installed")
        return

    if FIXED_TOPIC_ANCHOR not in text:
        raise RuntimeError(
            "fixed-topic Novelty weak-domain visibility: fixed_topic anchor "
            "not found (ci_script_v2_visual_goal_hotfix.py must run first)"
        )

    count = text.count(RETURN_ANCHOR)
    if count != 1:
        raise RuntimeError(
            "fixed-topic Novelty weak-domain visibility: build_consensus "
            f"return-block anchor count mismatch: {count}"
        )

    text = text.replace(RETURN_ANCHOR, _replacement_block() + RETURN_ANCHOR, 1)
    CONSENSUS_PATH.write_text(text, encoding="utf-8")
    print(
        "✅ fixed-topic Novelty weak-domain visibility restored "
        "(existing floor, existing regeneration path)"
    )


def _apply_hard_failure_boundary_patch():
    text = MAIN_PATH.read_text(encoding="utf-8")

    if HARD_FAILURE_MARKER in text:
        print("✅ Novelty hard-failure boundary fix already installed")
        return

    count = text.count(HARD_FAILURE_ANCHOR)
    if count != 1:
        raise RuntimeError(
            "Novelty hard-failure boundary fix: has_hard_novelty_failure "
            f"comparison anchor count mismatch: {count}"
        )

    text = text.replace(HARD_FAILURE_ANCHOR, HARD_FAILURE_REPLACEMENT, 1)
    MAIN_PATH.write_text(text, encoding="utf-8")
    print("✅ Novelty hard-failure boundary fix applied (score <= threshold)")


def main():
    _apply_consensus_patch()
    _apply_hard_failure_boundary_patch()


if __name__ == "__main__":
    main()
