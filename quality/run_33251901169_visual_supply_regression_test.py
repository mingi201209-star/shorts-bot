"""Run 33251901169 canonical visual-supply counterexamples.

Supply is strengthened; subject/explanatory gates are never relaxed.
No network/model call is performed by this regression.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# First preserve the production counterexamples through #254 exactly as-is.
subprocess.run(
    [sys.executable, str(ROOT / "quality/run_33248013901_visual_anchor_regression_test.py")],
    cwd=ROOT,
    check=True,
)
# Apply the new supply layer only after the established subject/explanation guards.
subprocess.run(
    [sys.executable, str(ROOT / "ci_canonical_visual_supply_contract_hotfix.py")],
    cwd=ROOT,
    check=True,
)

from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)
from video import video_downloader as vd
from video import still_image_fallback as still
from video import hook_visual_dominance as dominance


def stock(source_id, metadata):
    return {
        "id": source_id,
        "source_id": source_id,
        "provider": "pexels",
        "url": f"https://cdn.test/{source_id}.mp4",
        "download_url": f"https://cdn.test/{source_id}.mp4",
        "source_url": f"https://pexels.test/{source_id}",
        "title": metadata,
        "tags": metadata,
        "description": metadata,
        "metadata": metadata,
        "search_position": 1,
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
    }


candidate = {
    "topic": "비행기 엔진 뒤는 왜 톱니처럼 생겼을까",
    "angle": "엔진 뒤 톱니 모양의 설계 이유",
    "core_question": "왜 비행기 엔진 뒤가 톱니처럼 생겼을까?",
    "specific_observation": "비행기 엔진 뒤쪽의 톱니 모양 가장자리",
    "micro_narrative": {
        "hook": "비행기 엔진 뒤는 톱니처럼 생겼습니다.",
        "core_question": "왜 이런 모양일까요?",
        "reveal": "톱니 모양 셰브론은 흐름의 혼합을 바꿉니다.",
        "payoff": "대표적인 결과는 소음 감소입니다.",
    },
}
grounded = supply_trusted_subject_grounding(
    candidate,
    trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
assert grounded.get("canonical_subject") == "jet engine nacelle/nozzle chevrons"
assert float(grounded.get("subject_identity_confidence") or 0) == 0.98
profile = vd.build_canonical_visual_supply_profile(grounded)
assert profile.get("canonical_subject") == "jet engine nacelle/nozzle chevrons"
assert {"nacelle", "nozzle", "chevron", "serrated"}.issubset(set(profile.get("visual_discriminators") or []))

proof_query = vd.enforce_visual_subject_anchor_query(
    narration="비행기 엔진 뒤는 톱니처럼 생겼습니다.",
    visual_goal="톱니 모양의 엔진 배기구",
    query="airflow detail stage 1",
    visual_type="real_world_broll",
    scene_role="phenomenon",
    canonical_visual_supply=profile,
)
proof_words = set(proof_query.split())
required = set(vd.get_current_visual_subject_anchor_contract().get("required_anchors") or [])
assert required == {"aircraft", "engine", "chevron"}, required

# D/E. Canonical metadata must not degrade to aircraft-engine-detail; trusted
# physical discriminators must survive the opening stock query.
assert proof_query != "aircraft engine detail"
assert {"aircraft", "jet", "engine", "nacelle", "nozzle", "chevron", "serrated"}.issubset(proof_words), proof_query

fallbacks = vd._general_fallback_queries(proof_query)
assert 1 <= len(fallbacks) <= 3
for fallback in fallbacks:
    anchors = set(vd.extract_query_anchors(fallback))
    assert {"aircraft", "engine", "chevron"}.issubset(anchors), (fallback, anchors)
    words = set(fallback.split())
    assert "serrated" in words, fallback
    assert "nacelle" in words or "nozzle" in words, fallback
    assert "detail" not in words, fallback

# A. Generic aircraft+engine remains incomplete (2/3) and fail-closed.
generic_aircraft_engine = stock(15271, "aircraft airplane aviation jet engine closeup detail")
tier, _ = vd.general_scene_unknown_safe_tier(generic_aircraft_engine, fallbacks[0])
assert tier >= 5

# B. Generic jet-engine closeup with no visible/metadata chevron proof remains FAIL.
generic_engine = stock(33251902, "aircraft jet engine nacelle closeup turbine rear")
tier, _ = vd.general_scene_unknown_safe_tier(generic_engine, fallbacks[0])
assert tier >= 5

# C. Actual rear nacelle/nozzle with explicit chevron/serrated evidence can pass.
actual_chevron = stock(
    33251903,
    "aircraft jet engine rear nacelle nozzle chevron serrated edge closeup",
)
tier, label = vd.general_scene_unknown_safe_tier(actual_chevron, fallbacks[0])
assert tier < 5, (tier, label)

# F. Still fallback inherits the same canonical proof query and complete cache key.
scene = {
    "scene_id": 1,
    "role": "phenomenon",
    "text": "비행기 엔진 뒤는 톱니처럼 생겼습니다.",
    "visual_goal": "톱니 모양의 엔진 배기구",
    "keyword": proof_query,
}
assert still._anchor_signature(scene) == ("aircraft", "engine", "chevron"), still._anchor_signature(scene)
prompt = still._prompt(scene).lower()
for term in ("nacelle", "nozzle", "chevron", "serrated"):
    assert term in prompt, (term, prompt)

# G. An incomplete still never passes merely because aircraft+engine are visible.
original_eval = dominance.evaluate_hook_subject_dominance
try:
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: {
        "pass": True,
        "subject_visibility": 10.0,
        "visible_components": ["aircraft", "engine"],
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "reason": "aircraft and engine visible; chevron absent",
    }
    verified, evidence = still._verify_motion_clip(scene, ROOT / "not-read-because-verifier-is-mocked.mp4")
    assert verified is False
    assert "chevron" not in set(evidence.get("visible_components") or [])
finally:
    dominance.evaluate_hook_subject_dominance = original_eval

# H is covered above by A/B and by the pre-run #253 fixture.
# I/J are executed by run_33248013901_visual_anchor_regression_test.py before
# this layer: #254 explanatory nucleus still passes, while gas-stove, clock,
# partial anchors and green-screen counterexamples remain rejected.

print("RUN 33251901169 CANONICAL VISUAL SUPPLY REGRESSION: PASS")
