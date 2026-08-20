import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.first5_visual_contract import progression_passes, validate_reversal_query, visual_signature
from video import hook_visual as hv
from video import video_downloader as vd
from video.video_providers import candidate_unique_key, merge_provider_candidates


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def candidate(provider, source_id, metadata, *, page_url=None):
    return {
        "id": source_id,
        "provider": provider,
        "source_id": source_id,
        "source_url": page_url or f"https://example.test/{provider}/{source_id}",
        "download_url": f"https://cdn.test/{provider}/{source_id}.mp4",
        "provider_key": f"{provider}:{source_id}",
        "url": f"https://cdn.test/{provider}/{source_id}.mp4",
        "page_url": page_url or f"https://example.test/{provider}/{source_id}",
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
        "query": "test",
        "search_position": 1,
        "metadata_text": metadata,
        "tags": metadata,
    }


def test_pexels_only():
    original_p = vd.search_pexels_candidates
    original_x = vd.PIXABAY_API_KEY
    try:
        vd.PIXABAY_API_KEY = ""
        vd.search_pexels_candidates = lambda query, per_page=None: [
            {"id": 123, "url": "https://cdn.test/p.mp4", "page_url": "https://pexels.com/video/city-building-123/", "width": 1080, "height": 1920, "duration": 8, "search_position": 1}
        ]
        pool = vd.search_video_candidates("city building")
        check("A Pexels-only pool remains available", len(pool) == 1 and pool[0]["provider"] == "pexels")
    finally:
        vd.search_pexels_candidates = original_p
        vd.PIXABAY_API_KEY = original_x


def test_combined_and_isolation():
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    try:
        vd.PIXABAY_API_KEY = "test"
        vd.search_pexels_candidates = lambda query, per_page=None: [
            {"id": 123, "url": "https://cdn.test/p.mp4", "page_url": "https://pexels.com/video/city-building-123/", "width": 1080, "height": 1920, "duration": 8, "search_position": 1}
        ]
        vd.search_pixabay_candidates = lambda query, per_page=None: [candidate("pixabay", 456, "city building exterior")]
        pool = vd.search_video_candidates("city building")
        check("B Pexels + Pixabay unified pool", {item["provider"] for item in pool} == {"pexels", "pixabay"})

        def fail(*args, **kwargs):
            raise RuntimeError("synthetic provider outage")
        vd.search_pixabay_candidates = fail
        pool = vd.search_video_candidates("city building")
        check("C additional provider failure is isolated", len(pool) == 1 and pool[0]["provider"] == "pexels")

        vd.search_pixabay_candidates = lambda *args, **kwargs: []
        pool = vd.search_video_candidates("city building")
        check("D additional provider empty result falls back", len(pool) == 1 and pool[0]["provider"] == "pexels")
    finally:
        vd.search_pexels_candidates = original_p
        vd.search_pixabay_candidates = original_x_fn
        vd.PIXABAY_API_KEY = original_x_key


def test_provider_aware_dedupe():
    p = candidate("pexels", 123, "city building")
    x = candidate("pixabay", 123, "city building")
    merged = merge_provider_candidates([[p], [x]])
    check("E same numeric ID across providers remains distinct", len(merged) == 2 and candidate_unique_key(p) != candidate_unique_key(x))

    duplicate = dict(p)
    duplicate["download_url"] = "https://cdn.test/other.mp4"
    duplicate["url"] = duplicate["download_url"]
    merged = merge_provider_candidates([[p, duplicate]])
    check("F same provider/source ID is rejected as duplicate", len(merged) == 1)


def test_same_gates_for_new_provider():
    scene = {
        "keyword": "ordinary facade telecom infrastructure",
        "visual_goal": "평범한 건물처럼 보이지만 실제 통신 인프라",
        "text": "평범한 건물처럼 보이지만 실제로는 기반 시설이에요.",
    }
    bad = candidate("pixabay", 1, "radio tower antenna mast")
    scores, total = hv._score_candidate(bad, scene)
    check("G provider does not bypass first-5 strict metadata gate", not hv._passes_strict_gate({"candidate": bad, "scores": scores, "total_score": total}))

    valid, reason = validate_reversal_query({**scene, "keyword": "telecom tower antenna"})
    check("H PR15 reversal concept lock still rejects B-only query", not valid and reason == "reversal_appearance_side_missing")

    first = visual_signature("ordinary building facade exterior", "ordinary-building-facade-exterior")
    repeated = visual_signature("normal building facade exterior", "ordinary-building-facade-exterior-view")
    valid, _ = progression_passes(first, repeated)
    check("H PR15 opening progression still rejects repeated concept", not valid)

    check("Hook thresholds unchanged", hv.HOOK_VISUAL_MIN_SCORE == 7.0 and hv.HOOK_VISUAL_FLOORS == {"semantic_match": 7.0, "subject_visibility": 7.0, "mobile_clarity": 8.0})


def main():
    test_pexels_only()
    test_combined_and_isolation()
    test_provider_aware_dedupe()
    test_same_gates_for_new_provider()
    print("✅ VIDEO PROVIDER POOL FOCUSED REGRESSION PASS")


if __name__ == "__main__":
    main()
