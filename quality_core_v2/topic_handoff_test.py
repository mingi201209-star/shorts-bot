"""Regression for Golden E2E run 35430511093: workflow_dispatch topic
"aircraft wing flex" reached main.py's V2 guard clause, but
run_v2_pipeline() was called with no topic_direction, so the Explorer
received "" and produced an unrelated (typhoon) Scene 1, which later
failed subject-anchor enforcement with an empty keyword.

This must never happen again: SHORTS_TOPIC must reach the Explorer call
unchanged.
"""

import os

from quality_core_v2 import topic_direction_from_environment


def test_topic_direction_from_environment_reads_shorts_topic(monkeypatch):
    monkeypatch.setenv("SHORTS_TOPIC", "aircraft wing flex")
    assert topic_direction_from_environment() == "aircraft wing flex"


def test_topic_direction_from_environment_blank_when_unset(monkeypatch):
    monkeypatch.delenv("SHORTS_TOPIC", raising=False)
    assert topic_direction_from_environment() == ""


def test_run_v2_pipeline_forwards_topic_to_explorer(monkeypatch):
    # Golden Topic must reach the Explorer call unchanged -- this is the
    # exact handoff that was broken (main.py called run_v2_pipeline() with
    # no argument at all).
    from quality_core_v2.runner import run_v2_pipeline

    seen = {}

    def fake_propose(topic_direction, recent_topics, *, call_fn=None):
        seen["topic_direction"] = topic_direction
        from quality_core_v2.schemas import CandidateV2, Verdict
        candidate = CandidateV2.from_dict({
            "topic": topic_direction, "concrete_subject": "aircraft main wing",
            "observable_phenomenon": "upward bending", "core_question": "왜 휘는가",
            "mechanism": "탄성 변형", "reveal": "일부러 휘도록 설계됨",
            "canonical_subject": "aircraft main wing",
        })
        return candidate, Verdict(True, "ok", "candidate")

    monkeypatch.setattr(
        "quality_core_v2.runner.propose_candidate_with_bounded_rewrite", fake_propose
    )

    def fake_call_writer(candidate):
        import json
        return json.dumps({"scenes": [
            {"scene_index": 1, "narration": "n", "causal_role": "phenomenon",
             "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v"},
        ]})

    def fake_call_visual_planner(scene):
        import json
        return json.dumps({
            "subject": "aircraft main wing", "required_visible_components": ["aircraft"],
            "required_observable_state": ["bending"], "search_queries": ["aircraft wing flex"],
        })

    monkeypatch.setattr("quality_core_v2.runner.call_writer", fake_call_writer)
    monkeypatch.setattr("quality_core_v2.runner.call_visual_planner", fake_call_visual_planner)
    monkeypatch.setattr(
        "quality_core_v2.runner.render_v2_pipeline",
        lambda scenes, plans: {"scenes": scenes, "plans": plans},
    )

    run_v2_pipeline("aircraft wing flex", [])
    assert seen["topic_direction"] == "aircraft wing flex"
