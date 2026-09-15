import base64
import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCENE = {
    "scene_id": 1,
    "text": "제트 엔진 노즐 끝의 치프론을 보여줍니다.",
    "visual_goal": "제트 엔진 노즐의 치프론을 크게 보여준다",
    "keyword": "jet engine nacelle nozzle chevron serrated",
    "role": "phenomenon",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "canonical_terms": ["jet", "engine"],
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
    },
}


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _reload_still():
    os.environ.setdefault("OPENAI_KEY", "regression-test-key")
    import config

    config.OPENAI_KEY = "regression-test-key"
    sys.modules.pop("video.still_image_fallback", None)
    return importlib.import_module("video.still_image_fallback")


def _install():
    from ci_run_33506951642_still_generation_response_hotfix import main

    main()


def test_malformed_non_ascii_fails_closed_without_valueerror_escape():
    _install()
    still = _reload_still()
    still.requests.post = lambda *args, **kwargs: FakeResponse(
        {"data": [{"b64_json": "é"}]}
    )
    try:
        still._generate_image(SCENE)
    except RuntimeError as exc:
        message = str(exc)
        assert "b64_json decode failed" in message
        assert "UnicodeEncodeError" in message
    except ValueError as exc:
        raise AssertionError(f"ValueError escaped after response hardening: {exc}") from exc
    else:
        raise AssertionError("malformed b64_json must fail closed")


def test_same_response_url_is_used_without_extra_generation_call():
    _install()
    still = _reload_still()
    calls = {"post": 0, "get": 0}

    def post(*args, **kwargs):
        calls["post"] += 1
        return FakeResponse(
            {"data": [{"b64_json": "é", "url": "https://example.invalid/image.png"}]}
        )

    def get(*args, **kwargs):
        calls["get"] += 1
        return FakeResponse(content=b"valid-image-bytes")

    still.requests.post = post
    still.requests.get = get
    image_bytes, _ = still._generate_image(SCENE)
    assert image_bytes == b"valid-image-bytes"
    assert calls == {"post": 1, "get": 1}


def test_valid_base64_behavior_is_preserved():
    _install()
    still = _reload_still()
    payload = base64.b64encode(b"valid-image-bytes").decode("ascii")
    still.requests.post = lambda *args, **kwargs: FakeResponse(
        {"data": [{"b64_json": payload}]}
    )
    image_bytes, _ = still._generate_image(SCENE)
    assert image_bytes == b"valid-image-bytes"


def test_standards_data_uri_is_normalized():
    _install()
    still = _reload_still()
    payload = base64.b64encode(b"data-uri-image").decode("ascii")
    still.requests.post = lambda *args, **kwargs: FakeResponse(
        {"data": [{"b64_json": f"data:image/png;base64,{payload}"}]}
    )
    image_bytes, _ = still._generate_image(SCENE)
    assert image_bytes == b"data-uri-image"


def test_production_composition_wires_the_fix():
    trace = (ROOT / "ci_still_vision_evidence_trace_hotfix.py").read_text(encoding="utf-8")
    assert "def _patch_still_generation_response():" in trace
    assert trace.count("_patch_still_generation_response()") >= 3

    final_qa = (ROOT / "ci_final_visual_semantic_qa_hotfix.py").read_text(encoding="utf-8")
    assert "_patch_still_vision_evidence_trace" in final_qa


def test_quality_and_budget_contracts_are_unchanged():
    source = (ROOT / "video/still_image_fallback.py").read_text(encoding="utf-8")
    assert 'STILL_IMAGE_MAX_PER_VIDEO = int(os.environ.get("STILL_IMAGE_MAX_PER_VIDEO", "2"))' in source
    assert "MAX_INFORMATION_USES_PER_PHYSICAL_STILL = 2" in source

    installer = (ROOT / "ci_run_33506951642_still_generation_response_hotfix.py").read_text(encoding="utf-8")
    for forbidden in (
        "HOOK_SUBJECT_DOMINANCE_MIN =",
        "HOOK_ACTION_MATCH_MIN =",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "MAX_INFORMATION_USES_PER_PHYSICAL_STILL =",
    ):
        assert forbidden not in installer


if __name__ == "__main__":
    tests = [
        test_malformed_non_ascii_fails_closed_without_valueerror_escape,
        test_same_response_url_is_used_without_extra_generation_call,
        test_valid_base64_behavior_is_preserved,
        test_standards_data_uri_is_normalized,
        test_production_composition_wires_the_fix,
        test_quality_and_budget_contracts_are_unchanged,
    ]
    for test in tests:
        test()
    print("RUN_33506951642_STILL_GENERATION_RESPONSE_CURRENT_MAIN: PASS")
