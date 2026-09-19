"""Deterministic fuzz-discovered regression: Candidate Explorer malformed
response must not crash the production run.

RED authority (Production Stability Cleanup v3, deterministic malformed-input
fuzzing -- no real API calls):
- content/candidate_explorer.py::explore_candidates() parses raw model JSON
  via extract_json()/validate_explorer_output(), which deliberately raise
  ValueError for a known, bounded set of failure modes: invalid/truncated
  JSON, or a syntactically valid object that fails schema validation
  (missing/empty required field, wrong type, unrecognized status, ...).
- Nothing between that call and main.py's "CANDIDATE ATTEMPT N/total" retry
  loop catches that ValueError, so a single malformed-but-plausible model
  response (e.g. an otherwise well-formed SELECTED candidate with an empty
  visual_proof list) crashed the entire production run on whatever attempt
  hit it, instead of using the remaining bounded retries -- the same failure
  class as the CANDIDATE_POOL-outside-scope crash fixed for Run 34459538824.

RED authority (Production Stability Cleanup v4, retry-loop reachability
audit): explore_candidates() also raises RuntimeError("Candidate Explorer
응답이 비어 있습니다.") directly when the model response content is
empty/falsy -- the same deliberate empty-content guard used identically in
content/candidate_gate.py and quality/judge.py, confirming it is a known,
anticipated OpenAI response shape (e.g. content-filter/safety-refusal empty
completions), not a hypothetical. This is the only RuntimeError
content/candidate_explorer.py ever raises (verified), and it escaped the v3
fix's narrower `except ValueError`, crashing the run the same way.

Fix location: content/candidate_explorer/__init__.py (the package wrapper
main.py actually imports explore_candidates from), NOT
content/candidate_explorer.py. Several production hotfixes
(ci_topic_input_hotfix.py, ci_aviation_specificity_output_repair_hotfix.py,
...) match exact-text anchors inside content/candidate_explorer.py's
explore_candidates() body; editing that function's indentation there breaks
those hotfixes' anchor matching (verified: touching it made the full
production hotfix composition fail with
"explorer validation insertion marker mismatch" / "result guard marker
count mismatch"). The wrapper package is never touched by any hotfix, so
fixing it there is composition-safe by construction.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import content.candidate_explorer as ce_pkg


def _fake_response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0, cache_write_tokens=0),
        ),
    )


def _good_micro():
    return {"hook": "h", "core_question": "q?", "reveal": "r", "payoff": "p"}


def _good_candidate(**overrides):
    candidate = {
        "topic": "t",
        "angle": "a",
        "core_question": "q?",
        "micro_narrative": _good_micro(),
        "fact_check_focus": ["x"],
        "visual_proof": ["v"],
        "selection_reason": "s",
    }
    candidate.update(overrides)
    return candidate


def _run(content_payload, *, calls_seen):
    def fake_create(**kwargs):
        calls_seen.append(1)
        return _fake_response(content_payload)

    original_create = ce_pkg._LEGACY.openai.chat.completions.create
    original_authorize = ce_pkg._LEGACY.authorize_call
    original_record = ce_pkg._LEGACY.record_usage
    original_print = ce_pkg._LEGACY.print_budget_status
    try:
        ce_pkg._LEGACY.openai.chat.completions.create = fake_create
        ce_pkg._LEGACY.authorize_call = lambda model: len(calls_seen)
        ce_pkg._LEGACY.record_usage = lambda model, response: {"cost_usd": 0.0001, "over_budget": False}
        ce_pkg._LEGACY.print_budget_status = lambda: None
        return ce_pkg.explore_candidates(
            {"category": "x", "topic": "y"},
            recent_topics=[],
            rejected_topics=[],
        )
    finally:
        ce_pkg._LEGACY.openai.chat.completions.create = original_create
        ce_pkg._LEGACY.authorize_call = original_authorize
        ce_pkg._LEGACY.record_usage = original_record
        ce_pkg._LEGACY.print_budget_status = original_print


def test_malformed_selected_response_regenerates_instead_of_crashing():
    """RED -> GREEN: empty visual_proof (schema-valid JSON, invalid schema)."""
    malformed = {"status": "SELECTED", "winner": _good_candidate(visual_proof=[])}
    calls = []
    result = _run(json.dumps(malformed), calls_seen=calls)
    assert isinstance(result, dict), result
    assert result["status"] == "REGENERATE", result
    assert "malformed Candidate Explorer response" in result["reason"], result
    assert len(calls) == 1, "must not spend a second API call recovering from this"


def test_invalid_json_regenerates_instead_of_crashing():
    calls = []
    result = _run('{"status": "SELECTED", "winner": {', calls_seen=calls)
    assert result["status"] == "REGENERATE", result
    assert "malformed Candidate Explorer response" in result["reason"], result


def test_json_array_instead_of_object_regenerates_instead_of_crashing():
    calls = []
    result = _run("[1, 2, 3]", calls_seen=calls)
    assert result["status"] == "REGENERATE", result


def test_unrecognized_status_regenerates_instead_of_crashing():
    calls = []
    result = _run(json.dumps({"status": "CANDIDATE_POOL", "candidates": []}), calls_seen=calls)
    # Outside any aviation-scope hotfix composition, CANDIDATE_POOL is exactly
    # as unrecognized to the raw base validator as any other malformed status.
    assert result["status"] == "REGENERATE", result


def test_valid_selected_response_is_unaffected():
    """Negative control: a well-formed SELECTED response must pass through unchanged."""
    valid = {"status": "SELECTED", "winner": _good_candidate()}
    calls = []
    result = _run(json.dumps(valid), calls_seen=calls)
    assert result["status"] == "SELECTED", result
    assert result["winner"]["topic"] == "t", result
    assert "runner_up" not in result or result["runner_up"] is None


def test_valid_regenerate_response_is_unaffected():
    """Negative control: an explicit REGENERATE keeps its own reason verbatim."""
    valid = {"status": "REGENERATE", "reason": "no strong candidate this round"}
    calls = []
    result = _run(json.dumps(valid), calls_seen=calls)
    assert result["status"] == "REGENERATE", result
    assert result["reason"] == "no strong candidate this round", result


def test_empty_content_regenerates_instead_of_crashing():
    """RED (v4) -> GREEN: empty/falsy model content raises
    explore_candidates()'s own RuntimeError guard directly (not via
    extract_json()/validate_explorer_output()'s ValueError path). v3's fix
    only caught ValueError, so this RuntimeError still escaped uncaught;
    v4 extends the same wrapper to catch it too.
    """
    calls = []
    result = _run("", calls_seen=calls)
    assert isinstance(result, dict), result
    assert result["status"] == "REGENERATE", result
    assert "malformed Candidate Explorer response" in result["reason"], result
    assert "비어 있습니다" in result["reason"], result
    assert len(calls) == 1, "must not spend a second API call recovering from this"


def test_exact_fixed_topic_malformed_hook_recovers_from_repo_seed():
    """Run 35419510021: a malformed generated Hook/Core Question must not burn
    the whole fixed-topic attempt budget when one exact repo-owned seed exists.
    The trusted seed still has to pass the real validator and real narrowness
    gate; only the failed generative prose is replaced.
    """

    fixed_topic = "비행기 날개는 하중을 받으면 왜 휘고 비틀릴까?"
    original_explore = ce_pkg._LEGACY.explore_candidates
    original_critique = ce_pkg._LEGACY._self_critique_narrowness
    critique_calls = []

    def malformed_explore(*args, **kwargs):
        raise ValueError(
            "winner.micro_narrative hook이 Core Question과 같은 내용을 반복합니다."
        )

    def narrow_enough(winner, *, model):
        critique_calls.append((winner, model))
        return {
            "verdict": "NARROW_ENOUGH",
            "reason": "trusted seed exposes a concrete load path and deformation modes",
        }

    try:
        ce_pkg._LEGACY.explore_candidates = malformed_explore
        ce_pkg._LEGACY._self_critique_narrowness = narrow_enough
        result = ce_pkg.explore_candidates(
            {"category": "항공", "topic": fixed_topic},
            recent_topics=[],
            rejected_topics=[],
            fixed_topic=fixed_topic,
        )
    finally:
        ce_pkg._LEGACY.explore_candidates = original_explore
        ce_pkg._LEGACY._self_critique_narrowness = original_critique

    assert result["status"] == "SELECTED", result
    assert result["winner"]["topic"] == fixed_topic, result
    assert "flapwise/chordwise bending" in result["winner"]["micro_narrative"]["reveal"], result
    assert "torsion" in result["winner"]["micro_narrative"]["reveal"], result
    assert "리브와 스파" in result["winner"]["micro_narrative"]["reveal"], result
    assert "휨" in result["winner"]["core_question"], result
    assert "비틀림" in result["winner"]["core_question"], result
    assert len(critique_calls) == 1, critique_calls
    recovery = result.get("_exact_fixed_topic_seed_recovery") or {}
    assert recovery.get("status") == "USED", recovery
    assert recovery.get("api_calls_added") == 1, recovery


def test_exact_fixed_topic_seed_failure_is_diagnostic_not_silent():
    """Run 35422235885: if the exact seed still fails the unchanged
    narrowness gate, the wrapper must log the concrete critique reason instead
    of making the next production attempt look like another unexplained
    malformed Explorer loop.
    """

    import contextlib
    import io

    fixed_topic = "비행기 날개는 하중을 받으면 왜 휘고 비틀릴까?"
    original_explore = ce_pkg._LEGACY.explore_candidates
    original_critique = ce_pkg._LEGACY._self_critique_narrowness

    def malformed_explore(*args, **kwargs):
        raise ValueError(
            "winner.micro_narrative hook이 Core Question과 같은 내용을 반복합니다."
        )

    def still_too_broad(winner, *, model):
        return {
            "verdict": "TOO_BROAD",
            "reason": "fixture narrowness rejection",
        }

    captured = io.StringIO()
    try:
        ce_pkg._LEGACY.explore_candidates = malformed_explore
        ce_pkg._LEGACY._self_critique_narrowness = still_too_broad
        with contextlib.redirect_stdout(captured):
            result = ce_pkg.explore_candidates(
                {"category": "항공", "topic": fixed_topic},
                recent_topics=[],
                rejected_topics=[],
                fixed_topic=fixed_topic,
            )
    finally:
        ce_pkg._LEGACY.explore_candidates = original_explore
        ce_pkg._LEGACY._self_critique_narrowness = original_critique

    assert result["status"] == "REGENERATE", result
    assert "malformed Candidate Explorer response" in result["reason"], result
    log = captured.getvalue()
    assert "EXACT FIXED-TOPIC SEED RECOVERY SKIPPED" in log, log
    assert "fixture narrowness rejection" in log, log


def test_no_hotfix_anchor_text_touched():
    """Guard against regressing the composition-safety fix itself: the exact
    text several production hotfixes match against in
    content/candidate_explorer.py must remain untouched by this file.
    """
    from pathlib import Path

    source = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
    anchor = (
        '    result = (\n'
        '        validate_explorer_output(\n'
        '            parsed\n'
        '        )\n'
        '    )\n'
        '\n'
        '    status = result[\n'
        '        "status"\n'
        '    ]\n'
    )
    assert source.count(anchor) == 1, (
        "content/candidate_explorer.py's explore_candidates() result/status "
        "block must stay byte-for-byte unchanged; several production "
        "hotfixes anchor exact-text replacements on it"
    )


def main():
    test_malformed_selected_response_regenerates_instead_of_crashing()
    test_invalid_json_regenerates_instead_of_crashing()
    test_json_array_instead_of_object_regenerates_instead_of_crashing()
    test_unrecognized_status_regenerates_instead_of_crashing()
    test_valid_selected_response_is_unaffected()
    test_valid_regenerate_response_is_unaffected()
    test_empty_content_regenerates_instead_of_crashing()
    test_exact_fixed_topic_malformed_hook_recovers_from_repo_seed()
    test_exact_fixed_topic_seed_failure_is_diagnostic_not_silent()
    test_no_hotfix_anchor_text_touched()
    print(
        "PASS: Candidate Explorer malformed-response regenerate-not-crash "
        "regression (composition-safe wrapper fix)"
    )


if __name__ == "__main__":
    main()
