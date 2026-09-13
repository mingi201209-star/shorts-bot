"""Fail closed if the final production composition loses spoiler subject proof.

Exact HUMAN-QA counterexample: production Run 34786153210 rendered generic
night-vision/runway/wing B-roll because spoiler disappeared from the required
visual anchors and Scene 2 became a vacuous 0/0 contract.

This test intentionally applies no hotfix installers. It validates the files as
composed by the real production chain immediately before generation.
"""

from quality import final_visual_semantic_qa as fvs
from video import video_downloader as vd


def candidate(source_id, metadata):
    return {
        "id": source_id,
        "source_id": source_id,
        "provider": "pixabay",
        "url": f"https://cdn.test/{source_id}.mp4",
        "download_url": f"https://cdn.test/{source_id}.mp4",
        "source_url": f"https://pixabay.test/{source_id}",
        "title": metadata,
        "tags": metadata,
        "description": metadata,
        "search_position": 1,
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
    }


def strengthen(query, narration, goal):
    assert hasattr(vd, "enforce_visual_subject_anchor_query"), "subject-anchor contract missing from final composition"
    return vd.enforce_visual_subject_anchor_query(
        narration=narration,
        visual_goal=goal,
        query=query,
        visual_type="real_world_broll",
    )


# Exact Scene 1 shape from Run 34786153210.
scene1 = strengthen(
    "aircraft wing spoiler deployment",
    narration="스포일러가 착륙 직후 날개 위로 솟아올라 항공기의 공기 흐름을 변화시킵니다.",
    goal="착륙한 항공기의 날개 위에서 스포일러가 솟아오르는 순간을 보여줍니다.",
)
scene1_anchors = set(vd.extract_query_anchors(scene1))
assert scene1_anchors == {"aircraft", "wing", "spoiler"}, (scene1, scene1_anchors)

# Exact Scene 2 weak query from Run 34786153210. This used to become
# required=none detected=none completeness=1.00. Narration/goal make the
# aviation spoiler identity explicit, so it must bind to aircraft+wing+spoiler.
scene2 = strengthen(
    "why after touchdown",
    narration="그런데 왜 착륙 직후 스포일러가 솟아나는 걸까요?",
    goal="솟아오른 스포일러를 확대해 질문의 대상을 강조합니다.",
)
scene2_anchors = set(vd.extract_query_anchors(scene2))
assert scene2_anchors == {"aircraft", "wing", "spoiler"}, (scene2, scene2_anchors)
assert "spoiler" in scene2.split(), scene2
contract = vd.get_current_visual_subject_anchor_contract()
assert bool(contract.get("required")), contract
assert set(contract.get("required_anchors") or []) == {"aircraft", "wing", "spoiler"}, contract

# A spoiler Scene may relax wording, but never to the historical winglet ladder.
for fallback in vd.query_relaxation_ladder(scene1):
    words = set(fallback.split())
    assert "spoiler" in words, (scene1, fallback)
    assert "winglet" not in words, (scene1, fallback)

# Exact bad evidence family: generic aircraft+wing footage is only 2/3 proof.
generic = candidate(
    15270,
    "military aircraft airplane aviation wing runway night vision flight",
)
compat = vd.candidate_anchor_compatibility(generic, scene1)
assert compat["total"] == 3, compat
assert compat["matched"] == 2, compat
assert compat["compatible"] is False, compat
assert vd.choose_best_candidate([generic], subject_filter_query=scene1) is None

tier, label = vd.general_scene_unknown_safe_tier(generic, scene1)
assert tier >= 5, (tier, label)

# Positive control: visible deployed spoiler metadata remains eligible.
visible_spoiler = candidate(
    99701,
    "commercial aircraft airplane wing spoiler spoilers deployed after landing closeup",
)
positive = vd.candidate_anchor_compatibility(visible_spoiler, scene1)
assert positive["compatible"] is True, positive
assert vd.choose_best_candidate([visible_spoiler], subject_filter_query=scene1)["source_id"] == 99701

# Defense in depth: stale 2/3 lineage may not pass Final Visual Semantic QA.
partial_final_qa = {
    "query": scene1,
    "accepted": True,
    "anchor_matched": 2,
    "anchor_total": 3,
}
assert hasattr(fvs, "_missing_required_aviation_component_anchor")
assert fvs._missing_required_aviation_component_anchor(partial_final_qa) is True

# Blast radius: ordinary wing footage does not acquire a spoiler requirement.
plain = strengthen(
    "aircraft wing closeup",
    narration="비행기 날개가 공기 흐름을 만듭니다.",
    goal="비행기 날개를 가까이 보여줍니다.",
)
assert "spoiler" not in vd.extract_query_anchors(plain), plain

print("RUN 34786153210 SPOILER FINAL PRODUCTION COMPOSITION REGRESSION: PASS")
