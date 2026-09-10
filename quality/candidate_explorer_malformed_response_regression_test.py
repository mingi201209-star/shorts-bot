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


def test_empty_content_still_raises_uncaught():
    """Negative control: empty-content is a distinct, pre-existing signal
    (RuntimeError from extract_json's own empty-input guard is raised before
    reaching the wrapper's try/except at all via a different path in some
    callers); this fix's scope is deliberately limited to the ValueError
    class raised by extract_json()/validate_explorer_output() for non-empty
    but malformed content, so behavior for a genuinely empty response is
    unchanged.
    """
    calls = []
    try:
        _run("", calls_seen=calls)
    except RuntimeError as exc:
        assert "비어 있습니다" in str(exc), exc
    else:
        raise AssertionError("expected RuntimeError for empty content")


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
    test_empty_content_still_raises_uncaught()
    test_no_hotfix_anchor_text_touched()
    print(
        "PASS: Candidate Explorer malformed-response regenerate-not-crash "
        "regression (composition-safe wrapper fix)"
    )


if __name__ == "__main__":
    main()
