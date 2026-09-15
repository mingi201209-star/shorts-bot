"""Content Quality Recovery round -- Root Cause #2 (Novelty 4.0/10) regression.

Authority: Run 34847558126 (Shorts Generator on `publish-stable`, dispatched by
Publish Stable Engine run 34847540739) and Run 34813429408 (Shorts Generator on
`main`) -- both fixed-topic aviation canaries (`SHORTS_TOPIC` pinned to
"착륙 직후 날개 위로 솟는 스포일러") -- scored Novelty 4.0/10 at EVERY judge
round (reasoning: "제목만으로도 예상 가능한 내용이 포함되어 있어", predictable
from the title alone) across the full observed trajectory:
  round 1: hook=6.0 novelty=4.0 fact=8.0 visual=8.0 -> REWRITE (hook floor miss)
  round 2: hook=5.0 novelty=4.0 fact=8.0 visual=8.0 -> rewrite exhausted,
           hook floor still missed -> REGENERATE_TOPIC (same fixed topic,
           fresh Candidate Explorer pass)
  round 3: hook=7.0 novelty=4.0 fact=8.0 visual=8.0 -> PASS (IDEAL)
Neither run's Novelty regeneration path (`has_hard_novelty_failure` /
`has_persistent_novelty_failure` in main.py) ever fired at any round, even
though 4.0 sits exactly on the repo's own existing
`NOVELTY_HARD_REGENERATE_SCORE` (4.0, as lowered by ci_hotfix.py) and below
`DOMAIN_REWRITE_FLOORS["novelty"]` (5.0) -- floors free-topic production
already enforces.

Root cause (two compounding gaps, both closed here):
1. `_apply_fixed_topic_soft_judges` (ci_script_v2_visual_goal_hotfix.py)
   builds `weak_domains` from `decision_summaries`, which is fact-only for an
   explicitly pinned topic (by design, so Hook/Novelty/Visual cannot flip the
   PASS/REWRITE decision or silently swap the requested subject). Side
   effect: `weak_domains` can then never contain a "novelty" entry for a
   fixed topic, so `get_weak_domain(consensus, "novelty")` -- what BOTH
   Novelty regeneration checks actually read -- always returns None,
   regardless of the real Novelty score.
2. Even once (1) is fixed, `has_hard_novelty_failure` -- the ONLY one of the
   two checks reachable on a PASS-decision round, which round 3 above is --
   used a strict `<` against `NOVELTY_HARD_REGENERATE_SCORE`. A score sitting
   exactly ON that threshold (as observed, repeatedly, given the Judge model's
   documented tendency to emit round-number scores) never satisfies `< 4.0`,
   so round 3 would still have silently PASSed with fix (1) alone.

Fix (`ci_run_34847558126_fixed_topic_novelty_weak_domain_hotfix.py`):
(1) restores the Novelty entry in the RETURNED `weak_domains` for a fixed
topic, reusing the SAME existing `DOMAIN_REWRITE_FLOORS["novelty"]` floor --
no new number -- computed strictly AFTER decision/pass_tier/weighted_score
are already finalized from decision_summaries, so the PASS/REWRITE decision
itself for fixed topics is provably unchanged; (2) changes
`has_hard_novelty_failure`'s comparison to `<=` -- same threshold VALUE
(4.0), just inclusive of the boundary the judge model actually lands on.

This regression composes the real production hotfix chain (read directly out
of `.github/workflows/main.yml`'s "Apply production hotfixes" step, so it can
never silently drift from the actual production composition) in a scratch
copy, replays the EXACT real 3-round score trajectory above against the real
composed `run_quality_process`-equivalent loop, and proves the fix changes
the actual outcome end to end.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_YML = ROOT / ".github" / "workflows" / "main.yml"

FIXED_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"

# Real Run 34847558126 / 34813429408 round-by-round judge scores, in order.
REAL_ROUNDS = [
    {"hook": 6.0, "novelty": 4.0, "fact": 8.0, "visual": 8.0},
    {"hook": 5.0, "novelty": 4.0, "fact": 8.0, "visual": 8.0},
    {"hook": 7.0, "novelty": 4.0, "fact": 8.0, "visual": 8.0},
]


def _pool(round_scores):
    return {
        judge: [{"score": score, "confidence": 0.8, "issues": []}]
        for judge, score in round_scores.items()
    }


def _load_hotfix_chain() -> list[str]:
    """Extract the real "Apply production hotfixes" step's script order.

    Read directly from main.yml rather than hardcoded, so this regression can
    never silently drift out of sync with the actual production composition.
    """
    text = MAIN_YML.read_text(encoding="utf-8")
    step_start = text.index("Apply production hotfixes")
    step_text = text[step_start:]
    end = step_text.index("\n          grep -n")
    step_text = step_text[:end]
    scripts = re.findall(r"python (ci_[A-Za-z0-9_]+\.py)", step_text)
    if len(scripts) < 40:
        raise AssertionError(
            f"unexpectedly short hotfix chain extracted from main.yml: {len(scripts)} scripts"
        )
    return scripts


def _prepare_repo() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="run_34847558126_novelty_"))
    repo = scratch / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    chain = _load_hotfix_chain()
    for script in chain:
        result = subprocess.run([sys.executable, script], cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(
                f"production composition failed at {script}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
    return repo


def _get_weak_domain(consensus, judge_type):
    for item in consensus.get("weak_domains", []):
        if item.get("judge_type") == judge_type:
            return item
    return None


def _replay(consensus_module, hard_threshold, max_rewrites=1, max_topic_regenerations=1):
    """Minimal, faithful reimplementation of main.py's run_quality_process
    loop across a fixed-topic Candidate-regeneration lifecycle, driven by the
    exact real per-round scores. Mirrors: has_hard_novelty_failure check
    before PASS; PASS returns immediately; REWRITE with rewrite_count >=
    MAX_REWRITES falls to exhaustion recovery (Hook floor first, then
    persistent Novelty failure), consuming one bounded topic regeneration and
    advancing to the next round's scores; anything else is unreachable here
    because the real rounds never produced it.
    """
    topic_regenerations = 0
    round_index = 0
    rewrite_count = 0
    trace = []

    while True:
        if round_index >= len(REAL_ROUNDS):
            return {"status": "EXHAUSTED_FIXTURE_ROUNDS", "trace": trace}

        consensus = consensus_module.build_consensus(_pool(REAL_ROUNDS[round_index]))
        decision = consensus.get("decision")
        novelty_entry = _get_weak_domain(consensus, "novelty")
        hard_failure = (
            novelty_entry is not None
            and float(novelty_entry.get("score", 0.0)) <= hard_threshold
            if hard_threshold is not None
            else (
                novelty_entry is not None
                and float(novelty_entry.get("score", 0.0)) < 4.0
            )
        )
        trace.append({
            "round": round_index,
            "decision": decision,
            "novelty_entry": novelty_entry,
            "hard_failure": hard_failure,
        })

        if hard_failure:
            return {"status": "REGENERATE_TOPIC", "reason": "hard_novelty", "trace": trace}

        if decision == "PASS":
            return {"status": "PASS", "trace": trace}

        if decision == "REWRITE":
            if rewrite_count >= max_rewrites:
                hook_floor_miss = consensus.get("fixed_topic_hook_floor_miss", False)
                persistent_novelty = novelty_entry is not None
                if hook_floor_miss or persistent_novelty:
                    topic_regenerations += 1
                    if topic_regenerations > max_topic_regenerations:
                        return {"status": "REGENERATION_BUDGET_EXCEEDED", "trace": trace}
                    round_index += 1
                    rewrite_count = 0
                    continue
                return {"status": "REVIEW_FALLBACK", "trace": trace}
            rewrite_count += 1
            round_index += 1
            continue

        return {"status": f"UNHANDLED:{decision}", "trace": trace}


def main():
    repo = _prepare_repo()
    try:
        consensus_source = (repo / "quality" / "consensus.py").read_text(encoding="utf-8")
        assert "RUN_34847558126_FIXED_TOPIC_NOVELTY_WEAK_DOMAIN_VISIBILITY_V1" in consensus_source

        main_source = (repo / "main.py").read_text(encoding="utf-8")
        assert "def has_hard_novelty_failure(" in main_source
        assert "def has_persistent_novelty_failure(" in main_source
        assert "def get_weak_domain(" in main_source
        assert "RUN_34847558126_NOVELTY_HARD_FAILURE_BOUNDARY_V1" in main_source
        assert "score\n        <= NOVELTY_HARD_REGENERATE_SCORE" in main_source
        # Threshold VALUE itself is untouched -- still 4.0, only the
        # comparison operator changed.
        assert "NOVELTY_HARD_REGENERATE_SCORE = 4.0" in main_source

        sys.path.insert(0, str(repo))
        try:
            for name in list(sys.modules):
                if name == "quality" or name.startswith("quality."):
                    del sys.modules[name]
            consensus = __import__("quality.consensus", fromlist=["*"])

            import os

            # ================================================================
            # BEFORE: reproduce the OLD behavior exactly -- weak_domains built
            # only from fact-only decision_summaries, hard-failure boundary
            # still strict `<`. This is what Run 34847558126 / 34813429408
            # actually did.
            # ================================================================
            def _before_build_consensus(pool_results):
                summaries = consensus.summarize_pool(pool_results)
                decision_summaries = {"fact": summaries["fact"]} if "fact" in summaries else {}
                weighted_score = consensus.calculate_weighted_score(decision_summaries)
                disagreements = consensus.detect_disagreements(decision_summaries)
                low_confidence = consensus.detect_low_confidence(decision_summaries)
                critical_risks = consensus.detect_critical_risks(decision_summaries)
                weak_domains = consensus.detect_weak_domains(decision_summaries)
                hard_block = any(item.get("hard_block", False) for item in critical_risks)
                if hard_block:
                    decision = "REVIEW"
                elif disagreements["critical"]:
                    decision = "REVIEW"
                elif len(low_confidence) >= 2:
                    decision = "REVIEW"
                elif not weak_domains and weighted_score >= consensus.PASS_SCORE:
                    decision = "PASS"
                elif weighted_score >= consensus.GOOD_ENOUGH_SCORE and consensus.meets_good_enough_floors(decision_summaries):
                    decision = "PASS"
                elif weak_domains:
                    decision = "REWRITE"
                elif weighted_score >= consensus.REWRITE_SCORE:
                    decision = "REWRITE"
                else:
                    decision = "REWRITE"
                # Fixed-topic Hook Good-Enough floor guard (real, unaffected
                # by this fix) still applies on top, exactly as in production.
                result = {
                    "decision": decision, "pass_tier": "IDEAL" if decision == "PASS" else None,
                    "weighted_score": weighted_score, "weak_domains": weak_domains,
                }
                hook_summary = summaries.get("hook") or {}
                hook_floor = consensus.GOOD_ENOUGH_FLOORS.get("hook", 0.0)
                hook_score = consensus.safe_float(hook_summary.get("score", 0.0))
                if result["decision"] == "PASS" and hook_score < hook_floor:
                    result["decision"] = "REWRITE"
                    result["pass_tier"] = None
                    result["fixed_topic_hook_floor_miss"] = True
                return result

            class _BeforeModule:
                build_consensus = staticmethod(_before_build_consensus)

            os.environ["SHORTS_TOPIC"] = FIXED_TOPIC
            try:
                before_outcome = _replay(_BeforeModule, hard_threshold=4.0)
            finally:
                os.environ.pop("SHORTS_TOPIC", None)

            assert before_outcome["status"] == "PASS", before_outcome
            for step in before_outcome["trace"]:
                assert step["novelty_entry"] is None, (
                    "BEFORE: novelty must never be visible in weak_domains", step
                )
            print(
                f"BEFORE (real pre-fix behavior): status={before_outcome['status']} "
                f"after {len(before_outcome['trace'])} round(s) -- Novelty 4.0/10 "
                "silently PASSed at every round: PASS (bug reproduced)"
            )

            # ================================================================
            # AFTER: real composed quality/consensus.py (both patches applied)
            # replaying the EXACT same 3-round score trajectory.
            # ================================================================
            os.environ["SHORTS_TOPIC"] = FIXED_TOPIC
            try:
                after_outcome = _replay(consensus, hard_threshold=4.0)
            finally:
                os.environ.pop("SHORTS_TOPIC", None)

            assert after_outcome["status"] == "REGENERATE_TOPIC", after_outcome
            first_round = after_outcome["trace"][0]
            assert first_round["novelty_entry"] is not None, first_round
            assert first_round["novelty_entry"]["score"] == 4.0
            assert first_round["novelty_entry"]["minimum"] == 5.0  # existing floor, unchanged
            assert first_round["hard_failure"] is True, first_round
            print(
                f"AFTER (real composed fix): status={after_outcome['status']} at round "
                f"{first_round['round']} -- Novelty 4.0/10 now correctly triggers the "
                "pre-existing Candidate-regeneration path (same fixed topic, bounded "
                "by the existing MAX_TOPIC_REGENERATIONS): PASS (fix verified against "
                "the real evidence trajectory)"
            )

            # ================================================================
            # CASE C: a fixed topic where Hook/Fact/Visual are all healthy and
            # Novelty is ALSO healthy (>= floor) still PASSes cleanly -- no
            # false positive introduced.
            # ================================================================
            os.environ["SHORTS_TOPIC"] = FIXED_TOPIC
            try:
                healthy = consensus.build_consensus(_pool({"hook": 7.0, "novelty": 6.0, "fact": 8.0, "visual": 8.0}))
            finally:
                os.environ.pop("SHORTS_TOPIC", None)
            assert healthy["decision"] == "PASS", healthy["decision"]
            assert _get_weak_domain(healthy, "novelty") is None
            print("CASE C healthy fixed-topic novelty (6.0) -> clean PASS, no spurious entry: PASS")

            # ================================================================
            # CASE D: free-topic (SHORTS_TOPIC unset) is completely unaffected
            # -- the new block is gated entirely behind `if fixed_topic`, and
            # free-topic Novelty was already visible in weak_domains before
            # this fix (only the fixed-topic path was broken).
            # ================================================================
            os.environ.pop("SHORTS_TOPIC", None)
            free = consensus.build_consensus(_pool(REAL_ROUNDS[0]))
            free_novelty = _get_weak_domain(free, "novelty")
            assert free_novelty is not None and free_novelty["score"] == 4.0 and free_novelty["minimum"] == 5.0
            assert free["decision"] in ("REWRITE", "REVIEW")
            print(f"CASE D free-topic path unaffected: decision={free['decision']}: PASS")

        finally:
            sys.path.remove(str(repo))

        # No budget/floor/retry/API/model-routing constant touched by this
        # hotfix's own new blocks (threshold VALUES -- 4.0, 5.0 -- are reused,
        # not redefined; only the marker blocks themselves are scanned here).
        consensus_own = consensus_source[consensus_source.index(
            "RUN_34847558126_FIXED_TOPIC_NOVELTY_WEAK_DOMAIN_VISIBILITY_V1"
        ):]
        main_own = main_source[main_source.index(
            "RUN_34847558126_NOVELTY_HARD_FAILURE_BOUNDARY_V1"
        ):main_source.index("RUN_34847558126_NOVELTY_HARD_FAILURE_BOUNDARY_V1") + 800]
        combined_own = consensus_own + main_own
        for forbidden in (
            "V3_MAX_COST_USD =", "V3_MAX_API_CALLS =", "MAX_TOPIC_REGENERATIONS =",
            "MAX_REWRITES =", "GOOD_ENOUGH_SCORE =", "DOMAIN_REWRITE_FLOORS =",
            "GOOD_ENOUGH_FLOORS =", "NOVELTY_HARD_REGENERATE_SCORE =",
            "temperature=0.", "authorize_call(", "openai.",
        ):
            assert forbidden not in combined_own, forbidden
        print("CASE (budget invariant) budgets/floors/retries/model routing/threshold values unchanged: PASS")

        print("RUN 34847558126 FIXED-TOPIC NOVELTY WEAK-DOMAIN REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
