import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video import video_downloader as vd
from video.video_providers import search_wikimedia_commons_candidates


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


class FakeResponse:
    ok = True
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeRequests:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def meta(value):
    return {"value": value}


def page(pageid, title, mime, license_name, *, restrictions="", url=None):
    return {
        "pageid": pageid,
        "title": title,
        "imageinfo": [{
            "url": url or f"https://upload.wikimedia.org/{pageid}.webm",
            "mime": mime,
            "width": 1920,
            "height": 1080,
            "extmetadata": {
                "LicenseShortName": meta(license_name),
                "LicenseUrl": meta("https://example.test/license"),
                "Artist": meta("Test creator"),
                "ImageDescription": meta("<b>Aircraft spoiler deployment</b>"),
                "Copyrighted": meta("False"),
                "Restrictions": meta(restrictions),
            },
        }],
    }


def test_commons_license_gate():
    payload = {
        "query": {
            "pages": [
                page(1, "File:CC0 spoiler.webm", "video/webm", "CC0"),
                page(2, "File:PD spoiler.ogv", "video/ogg", "Public domain"),
                page(3, "File:BY spoiler.webm", "video/webm", "CC BY 4.0"),
                page(4, "File:BYSA spoiler.webm", "video/webm", "CC BY-SA 4.0"),
                page(5, "File:Unknown spoiler.webm", "video/webm", "Unknown"),
                page(6, "File:Image.jpg", "image/jpeg", "CC0", url="https://upload.wikimedia.org/6.jpg"),
                page(7, "File:Restricted.webm", "video/webm", "CC0", restrictions="permission required"),
            ]
        }
    }
    fake = FakeRequests(payload)
    results = search_wikimedia_commons_candidates(
        "aircraft spoiler",
        per_page=12,
        requests_module=fake,
    )

    check("A only attribution-free Commons video licenses auto-enter pool", [item["source_id"] for item in results] == [1, 2])
    check("B Commons candidates carry provider identity", all(item["provider"] == "wikimedia_commons" for item in results))
    check("C Commons auto-use metadata is explicitly commercial/modifiable/no-attribution", all(
        item["commercial_use"] is True
        and item["modification_allowed"] is True
        and item["attribution_required"] is False
        and item["license_review_required"] is False
        for item in results
    ))
    check("D Commons API request declares a User-Agent", bool(fake.calls and fake.calls[0][1].get("headers", {}).get("User-Agent")))
    check("E Commons query requests machine-readable license metadata", "extmetadata" in fake.calls[0][1].get("params", {}).get("iiprop", ""))


def _candidate(provider, source_id):
    return {
        "id": source_id,
        "provider": provider,
        "source_id": source_id,
        "source_url": f"https://example.test/{provider}/{source_id}",
        "download_url": f"https://cdn.test/{provider}/{source_id}.mp4",
        "provider_key": f"{provider}:{source_id}",
        "url": f"https://cdn.test/{provider}/{source_id}.mp4",
        "page_url": f"https://example.test/{provider}/{source_id}",
        "width": 1080,
        "height": 1920,
        "duration": 8.0,
        "query": "aircraft",
        "search_position": 1,
        "metadata_text": "aircraft wing spoiler",
    }


def test_composed_provider_pool():
    original_enabled = vd.WIKIMEDIA_COMMONS_ENABLED
    original_pix_key = vd.PIXABAY_API_KEY
    original_pexels = vd.search_pexels_candidates
    original_commons = vd.search_wikimedia_commons_candidates
    original_fetch_pexels = vd.fetch_pexels_video
    try:
        vd.WIKIMEDIA_COMMONS_ENABLED = True
        vd.PIXABAY_API_KEY = ""
        vd.search_pexels_candidates = lambda query, per_page=None: [{
            "id": 100,
            "url": "https://cdn.test/pexels/100.mp4",
            "page_url": "https://pexels.test/video/aircraft-wing-spoiler-100/",
            "width": 1080,
            "height": 1920,
            "duration": 8.0,
            "search_position": 1,
        }]
        vd.search_wikimedia_commons_candidates = lambda query, per_page=None: [_candidate("wikimedia_commons", 200)]
        pool = vd.search_video_candidates("aircraft wing spoiler")
        check("F enabled Commons joins Pexels without requiring Pixabay", {item["provider"] for item in pool} == {"pexels", "wikimedia_commons"})

        def fail(*args, **kwargs):
            raise RuntimeError("synthetic Commons outage")

        vd.search_wikimedia_commons_candidates = fail
        pool = vd.search_video_candidates("aircraft wing spoiler")
        check("G Commons outage is isolated and Pexels remains usable", len(pool) == 1 and pool[0]["provider"] == "pexels")

        vd.WIKIMEDIA_COMMONS_ENABLED = False
        vd.fetch_pexels_video = lambda query: "https://legacy.test/pexels.mp4"
        check("H disabled Commons + no Pixabay preserves exact legacy path", vd.fetch_video("aircraft wing") == "https://legacy.test/pexels.mp4")
    finally:
        vd.WIKIMEDIA_COMMONS_ENABLED = original_enabled
        vd.PIXABAY_API_KEY = original_pix_key
        vd.search_pexels_candidates = original_pexels
        vd.search_wikimedia_commons_candidates = original_commons
        vd.fetch_pexels_video = original_fetch_pexels


def test_no_quality_or_budget_relaxation():
    hotfix = (ROOT / "ci_video_provider_hotfix.py").read_text(encoding="utf-8")
    forbidden = (
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
        "HOOK_VISUAL_MIN_SCORE =",
        "HOOK_VISUAL_FLOORS =",
    )
    check("I provider expansion does not alter quality floors or model/API budgets", not any(token in hotfix for token in forbidden))


def main():
    test_commons_license_gate()
    test_composed_provider_pool()
    test_no_quality_or_budget_relaxation()
    print("✅ LEGAL VISUAL SUPPLY POOL V2 REGRESSION PASS")


if __name__ == "__main__":
    main()
