"""Deterministic fuzz-discovered regression: a malformed Script Engine V2
local-repair response must not crash the production run.

RED authority (Production Stability Cleanup v4, deterministic malformed-
input fuzzing -- no real API calls):
- content/script_engine_v2_runner.py::_apply_local_repairs() (as installed
  by the real production hotfix ci_script_v2_visual_goal_hotfix.py) resolves
  a bounded, known set of envelope/alias shapes for a local-repair model
  response (top-level "repairs"; nested under "result"/"output"/"data"/
  "response"/"repair_result"; or aliased as "scene_repairs"/"changes"/
  "fixed_scenes"/"items") and deliberately raises
  ValueError("local repair response repairs must be a list") only when none
  of those resolve to a list -- e.g. the model echoed a single repair object
  directly instead of wrapping it in a list.
- Nothing in generate_script_v2's MAX_LOCAL_REPAIR_CALLS loop catches that
  ValueError (verified: content/script_engine_v2_runner.py:
  "script = _apply_local_repairs(script, response, allowed,
  locked_text_indexes)" has no surrounding try/except), so a single
  malformed-but-plausible local-repair response crashed the entire
  production run, aborting the remaining bounded repair budget and the
  intended graceful "validation failed within 3 calls" bounded failure --
  the same failure class as the Candidate Explorer malformed-response crash
  (Production Stability Cleanup v3).

Fix location: content/script_generator_router.py's new
_sanitize_local_repair_response()/_resilient_v2_call(), NOT
content/script_engine_v2_runner.py. That runner file is patched in place by
ci_script_v2_visual_goal_hotfix.py and several sibling hotfixes using
exact-text anchors; editing generate_script_v2()/_apply_local_repairs()
directly risks breaking those anchors (the same class of mistake already
caught and fixed once during this cleanup, for
content/candidate_explorer.py in v3). content/script_generator_router.py is
touched by only one hotfix (ci_live_script_blockers_hotfix.py), which is
strictly append-only and marker-guarded and never touches generate_script(),
so wiring a response sanitizer through generate_script_v2's existing
call_fn parameter here is composition-safe by construction and spends no
additional API call.
"""

from __future__ import annotations

from content.script_generator_router import (
    _resilient_v2_call,
    _sanitize_local_repair_response,
)


def test_valid_top_level_list_passes_through_unchanged():
    response = {"repairs": [{"scene_index": 1, "text": "ok"}]}
    assert _sanitize_local_repair_response(response) == response


def test_valid_nested_envelope_passes_through_unchanged():
    response = {"result": {"repairs": [{"scene_index": 1}]}}
    assert _sanitize_local_repair_response(response) == response


def test_valid_alias_list_passes_through_unchanged():
    for alias_key in ("scene_repairs", "changes", "fixed_scenes", "items"):
        response = {alias_key: [{"scene_index": 1}]}
        assert _sanitize_local_repair_response(response) == response, alias_key


def test_none_repairs_passes_through_unchanged():
    """None is already handled as an empty-list no-op downstream; the
    sanitizer must not touch it (matching _apply_local_repairs' own
    `if repairs is None: repairs = []` branch)."""
    response = {"repairs": None}
    assert _sanitize_local_repair_response(response) == response


def test_missing_repairs_key_passes_through_unchanged():
    response = {"other_field": "value"}
    assert _sanitize_local_repair_response(response) == response


def test_dict_repairs_sanitized_to_empty_list():
    """RED -> GREEN: the model echoed a single repair object directly
    instead of wrapping it in a list (fuzz-found minimal failing input)."""
    response = {"repairs": {"scene_index": 1, "text": "oops"}}
    sanitized = _sanitize_local_repair_response(response)
    assert sanitized["repairs"] == [], sanitized


def test_string_repairs_sanitized_to_empty_list():
    response = {"repairs": "no changes needed"}
    sanitized = _sanitize_local_repair_response(response)
    assert sanitized["repairs"] == [], sanitized


def test_int_repairs_sanitized_to_empty_list():
    response = {"repairs": 42}
    sanitized = _sanitize_local_repair_response(response)
    assert sanitized["repairs"] == [], sanitized


def test_non_dict_response_passes_through_unchanged():
    """Defense in depth: a non-dict response is a different, pre-existing
    failure mode ( _apply_local_repairs itself would fail earlier on
    response.get); the sanitizer must not mask or alter it."""
    assert _sanitize_local_repair_response([1, 2, 3]) == [1, 2, 3]
    assert _sanitize_local_repair_response(None) is None


def test_sanitized_output_never_raises_in_real_apply_local_repairs():
    """Cross-validation against the real, production-hotfix-composed
    _apply_local_repairs(): every malformed case the sanitizer rewrites
    must be accepted without raising, and must not change the script
    (an empty-repairs response is a correct no-op, not a silent success).
    """
    import subprocess
    import sys

    subprocess.run([sys.executable, "ci_script_v2_visual_goal_hotfix.py"], check=True)
    from content.script_engine_v2_runner import _apply_local_repairs

    base_script = {
        "scenes": [{"text": "x", "visual_goal": "show something clearly", "keyword": "aircraft wing detail"}]
    }
    malformed_cases = (
        {"repairs": {"scene_index": 1, "text": "oops"}},
        {"repairs": "no changes needed"},
        {"repairs": 42},
    )
    for response in malformed_cases:
        sanitized = _sanitize_local_repair_response(response)
        result = _apply_local_repairs(base_script, sanitized, {1}, set())
        assert result["scenes"] == base_script["scenes"], (response, result)

    # Negative control: a valid repair still applies normally after passing
    # through the sanitizer untouched.
    valid = {"repairs": [{"scene_index": 1, "text": "repaired text"}]}
    sanitized_valid = _sanitize_local_repair_response(valid)
    assert sanitized_valid == valid
    result = _apply_local_repairs(base_script, sanitized_valid, {1}, set())
    assert result["scenes"][0]["text"] == "repaired text", result


def test_resilient_v2_call_wraps_default_call_only_for_local_repair():
    """_resilient_v2_call must sanitize local_repair responses and leave
    writer responses completely untouched (writer mode has no 'repairs'
    field and must never be sanitized)."""
    from unittest.mock import patch

    with patch(
        "content.script_engine_v2_runner._default_call",
        return_value={"scenes": [{"text": "hook"}]},
    ) as mock_call:
        result = _resilient_v2_call({"payload": 1}, mode="writer")
        assert result == {"scenes": [{"text": "hook"}]}
        mock_call.assert_called_once_with({"payload": 1}, mode="writer")

    with patch(
        "content.script_engine_v2_runner._default_call",
        return_value={"repairs": {"scene_index": 1, "text": "oops"}},
    ):
        result = _resilient_v2_call({"payload": 1}, mode="local_repair")
        assert result["repairs"] == [], result


def main():
    test_valid_top_level_list_passes_through_unchanged()
    test_valid_nested_envelope_passes_through_unchanged()
    test_valid_alias_list_passes_through_unchanged()
    test_none_repairs_passes_through_unchanged()
    test_missing_repairs_key_passes_through_unchanged()
    test_dict_repairs_sanitized_to_empty_list()
    test_string_repairs_sanitized_to_empty_list()
    test_int_repairs_sanitized_to_empty_list()
    test_non_dict_response_passes_through_unchanged()
    test_sanitized_output_never_raises_in_real_apply_local_repairs()
    test_resilient_v2_call_wraps_default_call_only_for_local_repair()
    print(
        "PASS: Script Engine V2 local-repair malformed-response "
        "sanitize-not-crash regression (composition-safe router fix)"
    )


if __name__ == "__main__":
    main()
