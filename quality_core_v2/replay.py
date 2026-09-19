"""Offline Replay / Shadow Harness.

Runs every fixture in quality_core_v2/fixtures/*.json through the matching
deterministic V2 gate and checks the result against the fixture's expected
outcome. Zero LLM calls, zero video/image provider calls, zero MP4
rendering, zero network dependency -- every fixture is a static JSON file
and every gate here is a pure function over already-decided data.

This is what "a failure discovered once becomes a permanent local
regression" (execution order section 1) means concretely: add a fixture,
never re-discover the same bug by re-running production.

Usage:
    python -m quality_core_v2.replay
    (also driven by quality_core_v2/replay_suite_test.py under pytest)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from quality_core_v2.candidate import evaluate_candidate_v2
from quality_core_v2.grounding import evaluate_grounding_v2
from quality_core_v2.schemas import (
    CandidateV2,
    CandidateVisualV2,
    GroundingV2,
    SceneV2,
    Verdict,
    VisualPlanV2,
)
from quality_core_v2.script_plan import evaluate_script_plan_v2
from quality_core_v2.visual_plan import evaluate_visual_plan_v2, match_visual_to_plan
from quality_core_v2.visual_qa import evaluate_scene_visual_qa

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@dataclass
class FixtureResult:
    name: str
    category: str
    stage: str
    ok: bool
    detail: str


def _run_retrieval_adapter(fixture_input: Dict[str, Any]) -> Verdict:
    """Deterministic stand-in retrieval adapter for provider-miss /
    stale-cache fixtures. `attempts` is an ordered list of
    {"provider": str, "status": "miss"|"error"|"hit"|"stale_cache_hit",
    "visual": {...} | null}. The adapter must (a) skip miss/error entries
    and try the next provider, (b) never accept a stale_cache_hit as a
    fresh result, and (c) report which provider (if any) actually served
    the accepted visual.
    """
    attempts = fixture_input.get("attempts", [])
    for attempt in attempts:
        status = attempt.get("status")
        if status == "hit":
            return Verdict(
                True,
                f"served by provider={attempt.get('provider')!r}",
                "retrieval",
            )
        if status == "stale_cache_hit":
            return Verdict(
                False,
                f"provider={attempt.get('provider')!r} returned a stale cache "
                "hit; treated as a miss, must not be accepted as fresh",
                "retrieval",
            )
        # "miss" / "error" -> fall through to next attempt
    return Verdict(
        False,
        "all providers missed or errored; no visual available "
        "(caller must fall back to grounded_explanatory/generated, "
        "never silently substitute stale data)",
        "retrieval",
    )


def _run_fixture(fixture: Dict[str, Any]) -> FixtureResult:
    name = fixture.get("name", "<unnamed>")
    category = fixture.get("category", "")
    stage = fixture["stage"]
    fx_input = fixture["input"]
    expected_pass = bool(fixture["expected_pass"])
    expected_reason_contains = fixture.get("expected_reason_contains", "")

    try:
        if stage == "candidate":
            verdict = evaluate_candidate_v2(CandidateV2.from_dict(fx_input))
        elif stage == "grounding":
            verdict = evaluate_grounding_v2(GroundingV2.from_dict(fx_input))
        elif stage == "script_plan":
            scenes = [SceneV2.from_dict(s) for s in fx_input["scenes"]]
            verdict = evaluate_script_plan_v2(scenes)
        elif stage == "visual_plan":
            plan = VisualPlanV2.from_dict(fx_input["plan"])
            candidate_raw = fx_input.get("candidate")
            candidate = (
                CandidateV2.from_dict(candidate_raw)
                if isinstance(candidate_raw, dict)
                else None
            )
            verdict = evaluate_visual_plan_v2(plan, candidate=candidate)
        elif stage == "visual_match":
            plan = VisualPlanV2.from_dict(fx_input["plan"])
            visual = CandidateVisualV2.from_dict(fx_input["visual"])
            verdict = match_visual_to_plan(plan, visual)
        elif stage == "visual_qa":
            scene = SceneV2.from_dict(fx_input["scene"])
            plan = VisualPlanV2.from_dict(fx_input["plan"])
            visual = CandidateVisualV2.from_dict(fx_input["visual"])
            verdict = evaluate_scene_visual_qa(scene, plan, visual)
        elif stage == "retrieval":
            verdict = _run_retrieval_adapter(fx_input)
        else:
            return FixtureResult(name, category, stage, False, f"unknown stage {stage!r}")
    except Exception as exc:  # noqa: BLE001 - a fixture-shape error is a result, not a crash
        if not expected_pass and expected_reason_contains and expected_reason_contains in str(exc):
            return FixtureResult(name, category, stage, True, f"raised as expected: {exc}")
        return FixtureResult(
            name, category, stage, False, f"raised {type(exc).__name__}: {exc}"
        )

    if verdict.passed != expected_pass:
        return FixtureResult(
            name,
            category,
            stage,
            False,
            f"expected passed={expected_pass}, got passed={verdict.passed} "
            f"(reason={verdict.reason!r})",
        )
    if expected_reason_contains and expected_reason_contains not in verdict.reason:
        return FixtureResult(
            name,
            category,
            stage,
            False,
            f"expected reason to contain {expected_reason_contains!r}, "
            f"got {verdict.reason!r}",
        )
    return FixtureResult(name, category, stage, True, verdict.reason)


def load_fixtures(fixtures_dir: Path = FIXTURES_DIR) -> List[Dict[str, Any]]:
    fixtures = []
    for path in sorted(fixtures_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            fixture = json.load(f)
        fixture["_path"] = str(path)
        fixtures.append(fixture)
    return fixtures


def run_all(fixtures_dir: Path = FIXTURES_DIR) -> List[FixtureResult]:
    return [_run_fixture(fx) for fx in load_fixtures(fixtures_dir)]


def main() -> int:
    results = run_all()
    failed = [r for r in results if not r.ok]
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"[{mark}] {r.category:40s} {r.name:50s} {r.detail}")
    print(f"\n{len(results) - len(failed)}/{len(results)} fixtures passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
