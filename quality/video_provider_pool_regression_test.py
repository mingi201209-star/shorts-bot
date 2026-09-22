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
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = ""
        vd.search_pexels_candidates = lambda query, per_page=None: [
            {"id": 123, "url": "https://cdn.test/p.mp4", "page_url": "https://pexels.com/video/city-building-123/", "width": 1080, "height": 1920, "duration": 8, "search_position": 1}
        ]
        pool = vd.search_video_candidates("city building")
        check("A Pexels-only pool remains available", len(pool) == 1 and pool[0]["provider"] == "pexels")
    finally:
        vd.search_pexels_candidates = original_p
        vd.PIXABAY_API_KEY = original_x
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_combined_and_isolation():
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
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
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


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


def test_pexels_rate_limit_switches_to_secondary_bounded():
    """429 is a provider availability failure, not a query failure: must not
    hammer Pexels with more fallback queries, and must switch to a configured
    secondary provider instead of failing the whole fetch."""
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    calls = []
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = "test"

        def raise_429(query, per_page=None):
            calls.append(query)
            raise vd.ProviderRateLimitedError("Pexels 검색 실패: HTTP 429")

        vd.search_pexels_candidates = raise_429
        vd.search_pixabay_candidates = lambda query, per_page=None: [
            candidate("pixabay", 999, "aircraft window corner detail")
        ]

        pool = vd.search_video_candidates("aircraft window corner", provider_state={})
        check(
            "429 -> secondary provider returns normal candidate",
            len(pool) == 1 and pool[0]["provider"] == "pixabay",
        )
        check("429 calls Pexels exactly once for this search", len(calls) == 1)
    finally:
        vd.search_pexels_candidates = original_p
        vd.search_pixabay_candidates = original_x_fn
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_pexels_rate_limit_no_repeat_calls_across_fallback_queries():
    """The real bug this regression guards: fetch_video() tries multiple
    fallback queries. Once Pexels is rate-limited on the first, subsequent
    fallback queries in the SAME pass must not call Pexels again."""
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    calls = []
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = "test"

        def raise_429(query, per_page=None):
            calls.append(query)
            raise vd.ProviderRateLimitedError("Pexels 검색 실패: HTTP 429")

        vd.search_pexels_candidates = raise_429
        # No candidates from the secondary provider either, on any query --
        # forces fetch_video() to actually walk its full fallback query list.
        vd.search_pixabay_candidates = lambda query, per_page=None: []

        result = vd.fetch_video("very specific uncommon compound search phrase")
        check("all providers exhausted -> explicit fail-close (None)", result is None)
        check(
            f"Pexels called at most once across all fallback queries (calls={calls})",
            len(calls) == 1,
        )
    finally:
        vd.search_pexels_candidates = original_p
        vd.search_pixabay_candidates = original_x_fn
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_pexels_transient_5xx_bounded_recovery():
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    calls = []
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = "test"

        def raise_503(query, per_page=None):
            calls.append(query)
            raise vd.ProviderTransientError("Pexels 검색 실패: HTTP 503")

        vd.search_pexels_candidates = raise_503
        vd.search_pixabay_candidates = lambda query, per_page=None: [
            candidate("pixabay", 321, "aircraft window corner")
        ]

        pool = vd.search_video_candidates("aircraft window corner", provider_state={})
        check("HTTP 5xx -> secondary provider candidate returned", len(pool) == 1 and pool[0]["provider"] == "pixabay")
        check("HTTP 5xx calls Pexels exactly once", len(calls) == 1)
    finally:
        vd.search_pexels_candidates = original_p
        vd.search_pixabay_candidates = original_x_fn
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_pexels_network_timeout_bounded_recovery():
    original_p = vd.search_pexels_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    calls = []
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = ""

        def raise_timeout(query, per_page=None):
            calls.append(query)
            raise vd.ProviderTransientError("Pexels 검색 실패: 네트워크 오류 (Timeout)")

        vd.search_pexels_candidates = raise_timeout

        result = vd.fetch_video("aircraft window corner")
        check("network timeout with no secondary provider -> explicit fail-close (None)", result is None)
        check("network timeout calls Pexels exactly once", len(calls) == 1)
    finally:
        vd.search_pexels_candidates = original_p
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_no_results_is_not_treated_as_provider_failure():
    """Zero results (HTTP 200, empty body) must keep using the existing
    semantic fallback-query behavior -- it is not a provider outage and must
    not switch providers or stop early."""
    original_p = vd.search_pexels_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    calls = []
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = ""
        vd.search_pexels_candidates = lambda query, per_page=None: calls.append(query) or []

        result = vd.fetch_video("very specific uncommon compound search phrase")
        check("zero results (not an error) -> fail-close (None)", result is None)
        check(
            f"zero results still walks multiple fallback queries (calls={len(calls)})",
            len(calls) > 1,
        )
    finally:
        vd.search_pexels_candidates = original_p
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_all_providers_fail_explicit_close():
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = "test"
        vd.search_pexels_candidates = lambda query, per_page=None: (_ for _ in ()).throw(
            vd.ProviderRateLimitedError("Pexels 검색 실패: HTTP 429")
        )
        vd.search_pixabay_candidates = lambda query, per_page=None: (_ for _ in ()).throw(
            RuntimeError("Pixabay search failed: HTTP 500")
        )

        result = vd.fetch_video("aircraft window corner")
        check("every provider failing -> explicit fail-close, never an arbitrary/unrelated video", result is None)
    finally:
        vd.search_pexels_candidates = original_p
        vd.search_pixabay_candidates = original_x_fn
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_aviation_window_subject_grounding_preserved_after_failover():
    """Provider failover must not bypass canonical_metadata/candidate
    plumbing -- the switched-to candidate still carries normal fields the
    rest of the pipeline (subject anchor / grounding) depends on."""
    original_p = vd.search_pexels_candidates
    original_x_fn = vd.search_pixabay_candidates
    original_x_key = vd.PIXABAY_API_KEY
    original_w = vd.WIKIMEDIA_COMMONS_ENABLED
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.PIXABAY_API_KEY = "test"
        vd.search_pexels_candidates = lambda query, per_page=None: (_ for _ in ()).throw(
            vd.ProviderRateLimitedError("Pexels 검색 실패: HTTP 429")
        )
        vd.search_pixabay_candidates = lambda query, per_page=None: [
            candidate("pixabay", 55, "aircraft window frame rounded corner fuselage")
        ]

        pool = vd.search_video_candidates("aircraft window corner", provider_state={})
        check("aviation/window query still returns a grounded candidate after failover", len(pool) == 1)
        check(
            "failover candidate metadata still carries the aircraft/window subject terms",
            "aircraft" in pool[0]["metadata_text"] and "window" in pool[0]["metadata_text"],
        )
    finally:
        vd.search_pexels_candidates = original_p
        vd.search_pixabay_candidates = original_x_fn
        vd.PIXABAY_API_KEY = original_x_key
        vd.WIKIMEDIA_COMMONS_ENABLED = original_w


def test_hook_scene_recovery_does_not_bypass_hook_visual_contract():
    """A Hook-scene provider failure must fall through to the existing
    legacy-path fallback (bounded), never silently accept a candidate that
    skipped the strict metadata gate / subject dominance gate.

    hook_visual.py binds its own `search_video_candidates` / `fetch_video`
    names at import time (from video.video_downloader import ...), so those
    -- not video_downloader's own attributes -- are what must be patched to
    intercept what fetch_hook_pexels_video actually calls."""
    original_search = hv.search_video_candidates
    original_fetch = hv.fetch_video
    calls = []
    fallback_calls = []
    try:

        def raise_429(query, per_page=None, provider_state=None):
            calls.append(query)
            raise vd.ProviderRateLimitedError("Pexels 검색 실패: HTTP 429")

        def stub_fetch_video(query):
            fallback_calls.append(query)
            return None

        hv.search_video_candidates = raise_429
        hv.fetch_video = stub_fetch_video

        scene = {"keyword": "aircraft window corner detail", "scene_id": "hook", "role": "hook"}
        result = hv.fetch_hook_pexels_video(scene)

        check("Hook scene 429 recovery falls back through the legacy path, not a silent accept", result is None)
        check(f"Hook scene 429 calls the provider search exactly once (calls={calls})", len(calls) == 1)
        check("Hook scene 429 still reaches the bounded legacy-path fallback call", len(fallback_calls) == 1)
    finally:
        hv.search_video_candidates = original_search
        hv.fetch_video = original_fetch


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
    test_pexels_rate_limit_switches_to_secondary_bounded()
    test_pexels_rate_limit_no_repeat_calls_across_fallback_queries()
    test_pexels_transient_5xx_bounded_recovery()
    test_pexels_network_timeout_bounded_recovery()
    test_no_results_is_not_treated_as_provider_failure()
    test_all_providers_fail_explicit_close()
    test_aviation_window_subject_grounding_preserved_after_failover()
    test_hook_scene_recovery_does_not_bypass_hook_visual_contract()
    test_same_gates_for_new_provider()
    print("✅ VIDEO PROVIDER POOL FOCUSED REGRESSION PASS")


if __name__ == "__main__":
    main()
