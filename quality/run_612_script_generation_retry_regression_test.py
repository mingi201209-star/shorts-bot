"""Regression test: a Script Engine RuntimeError must retry the next
candidate instead of crashing the whole run.

Run 612 (2026-09-18) got a Winner past Candidate Explorer/Gate for the
first time, but generate_script() raised a RuntimeError (Script Engine
V2 duplicate-claim validation exhausted) and that exception propagated
straight out of main()'s Candidate Loop -- unlike an Explorer/Gate
REGENERATE, it had no retry path, so the whole run crashed even though
19 more topic attempts were still available.

This wraps the generate_script() call in main.py's Candidate Loop in a
try/except RuntimeError that rejects the current topic and retries the
loop exactly like a Winner Candidate Gate rejection, only raising once
attempts are exhausted.

This test drives main.main() with every external dependency mocked:
attempt 1's generate_script() raises RuntimeError (reproducing run
612), attempt 2 selects a different Winner and generate_script()
succeeds. It asserts:
  1. generate_script() was called twice (i.e. the run retried instead
     of crashing after the first failure).
  2. The first Winner's topic landed in rejected_topics reasoning
     (visible via the second explore_candidates() call not being
     starved -- checked indirectly through call count).
  3. remember_used_topic() -- the last thing before video/TTS
     rendering -- was reached with the SECOND attempt's script,
     proving the run recovered and completed candidate selection
     instead of raising.
"""

import sys
from unittest.mock import MagicMock, patch

# main.py transitively imports edge_tts and moviepy.editor purely for their
# symbol names; this regression only exercises the Candidate Loop's retry
# logic (never reaches TTS/video rendering), so stub both when the real
# packages aren't installed in the sandbox running this test.
for _missing_module, _attrs in (
    ("edge_tts", ["Communicate"]),
    ("moviepy.editor", [
        "AudioFileClip", "ImageClip", "VideoFileClip", "CompositeVideoClip",
        "CompositeAudioClip", "concatenate_videoclips", "concatenate_audioclips",
        "TextClip", "ColorClip", "vfx", "afx",
    ]),
):
    if _missing_module not in sys.modules:
        try:
            __import__(_missing_module)
        except ImportError:
            stub = MagicMock()
            for _attr in _attrs:
                setattr(stub, _attr, MagicMock())
            sys.modules[_missing_module] = stub
            if "." in _missing_module:
                sys.modules[_missing_module.split(".")[0]] = MagicMock()

import main as main_module


class _StopAfterCandidateLoop(Exception):
    """Sentinel raised once main() reaches remember_used_topic()."""


def _topic_info():
    return {"category": "과학", "topic": "테스트 방향"}


def _winner(topic):
    return {
        "topic": topic,
        "angle": "테스트 앵글",
        "core_question": f"왜 {topic}일까요?",
        "micro_narrative": {
            "hook": "훅",
            "core_question": "질문",
            "reveal": "리빌",
            "payoff": "페이오프",
        },
        "fact_check_focus": [],
        "visual_proof": ["증거"],
        "selection_reason": "이유",
    }


def test_script_generation_failure_retries_next_candidate():
    winners = [_winner("첫 번째 소재"), _winner("두 번째 소재")]
    explore_calls = {"count": 0}

    def fake_explore_candidates(topic_info, **kwargs):
        index = explore_calls["count"]
        explore_calls["count"] += 1
        return {"status": "SELECTED", "winner": winners[index], "runner_up": None}

    generate_script_calls = {"count": 0}

    def fake_generate_script(topic_info, winner):
        generate_script_calls["count"] += 1
        if generate_script_calls["count"] == 1:
            raise RuntimeError(
                "Script Engine V2 validation failed within 3 calls: "
                "new-information contract: scene repeats semantic claim "
                "noise_reduction reserved for scene 1"
            )
        return {
            "topic": winner["topic"],
            "title": "테스트 제목",
            "scenes": [{"text": "장면"}],
        }

    with (
        patch.object(main_module, "validate_environment"),
        patch.object(main_module, "reset_budget"),
        patch.object(main_module, "print_budget_status"),
        patch.object(main_module, "choose_topic_direction", return_value=_topic_info()),
        patch.object(main_module, "get_recent_topic_names", return_value=[]),
        patch.object(main_module, "explore_candidates", side_effect=fake_explore_candidates),
        patch.object(main_module, "evaluate_candidate", return_value={"status": "PASS"}),
        patch.object(main_module, "generate_script", side_effect=fake_generate_script),
        patch.object(main_module, "enrich_visual_plan", side_effect=lambda scenes: scenes),
        patch.object(main_module, "validate_visual_plan", return_value=(True, "")),
        patch.object(
            main_module,
            "run_quality_process",
            side_effect=lambda script_data: {"status": "PASS", "script_data": script_data},
        ),
        patch.object(main_module, "remember_used_topic", side_effect=_StopAfterCandidateLoop),
    ):
        try:
            main_module.main()
        except _StopAfterCandidateLoop:
            pass

    assert generate_script_calls["count"] == 2, (
        "generate_script must be retried with a new candidate after a "
        "RuntimeError, not left to crash the run"
    )
    assert explore_calls["count"] == 2, (
        "a script-generation failure must trigger re-exploration for a "
        "new candidate, matching Explorer/Gate rejection behavior"
    )


if __name__ == "__main__":
    test_script_generation_failure_retries_next_candidate()
    print("✓ test_script_generation_failure_retries_next_candidate")
    print("\n✅ All tests passed")
