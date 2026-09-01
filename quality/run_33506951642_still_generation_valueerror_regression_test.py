import base64
import hashlib
import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCENE = {
    "text": "제트 엔진의 노즐 끝에 있는 치프론을 자세히 살펴보면, 그 형상이 독특하다는 것을 알 수 있습니다.",
    "visual_goal": "치프론의 독특한 형상",
    "keyword": "jet engine nacelle nozzle chevron serrated",
    "role": "phenomenon",
    "causal_role": "phenomenon",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        # Production trace priority was nozzle+nacelle+chevron+serrated+jet+engine.
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


def _reload_still_module():
    os.environ.setdefault("OPENAI_KEY", "regression-test-key")
    import config
    config.OPENAI_KEY = "regression-test-key"
    if "video.still_image_fallback" in sys.modules:
        del sys.modules["video.still_image_fallback"]
    return importlib.import_module("video.still_image_fallback")


def test_production_scene_fixture():
    still = _reload_still_module()
    prompt = still._prompt(SCENE)
    contract = still._canonical_still_contract(SCENE)
    assert contract["canonical_subject"] == "jet engine nacelle/nozzle chevrons"
    assert contract["required_viewpoint"] == "rear or rear-quarter close-up of the trailing edge"
    assert contract["subject_proof_priority"] == [
        "nozzle", "nacelle", "chevron", "serrated", "jet", "engine"
    ]
    # Run 33506951642 diagnostics recorded this exact production-composed prompt signature.
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16] == "7ad26d89be578cff"


def test_before_fix_exact_valueerror_shape():
    # Production preserved only type(exc).__name__ == ValueError. The exact
    # message was lost by the old broad catch. At the narrowed response handoff,
    # Python's legacy str -> base64 path produces the preserved class for
    # non-ASCII image payload text.
    try:
        base64.b64decode("é")
    except ValueError as exc:
        assert str(exc) == "string argument should contain only ASCII characters"
    else:
        raise AssertionError("legacy b64 handoff did not reproduce ValueError")


def test_after_fix_fail_closed_with_diagnostic_message():
    from ci_run_33506951642_still_generation_response_hotfix import main as install
    install()
    still = _reload_still_module()
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
        raise AssertionError(f"ValueError escaped after fix: {exc}") from exc
    else:
        raise AssertionError("malformed payload must fail closed without alternate URL")


def test_after_fix_uses_existing_url_without_new_generation_call():
    from ci_run_33506951642_still_generation_response_hotfix import main as install
    install()
    still = _reload_still_module()
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
    image_bytes, prompt = still._generate_image(SCENE)
    assert image_bytes == b"valid-image-bytes"
    assert "jet engine nacelle/nozzle chevrons" in prompt
    assert calls == {"post": 1, "get": 1}


def test_after_fix_valid_base64_is_unchanged():
    from ci_run_33506951642_still_generation_response_hotfix import main as install
    install()
    still = _reload_still_module()
    payload = base64.b64encode(b"valid-image-bytes").decode("ascii")
    still.requests.post = lambda *args, **kwargs: FakeResponse(
        {"data": [{"b64_json": payload}]}
    )
    image_bytes, prompt = still._generate_image(SCENE)
    assert image_bytes == b"valid-image-bytes"
    assert "Required viewpoint from trusted physical evidence: rear or rear-quarter close-up of the trailing edge" in prompt


def test_production_composition_wires_fix_after_visual_contracts():
    still_source = (ROOT / "video/still_image_fallback.py").read_text(encoding="utf-8")
    assert "RUN_33506951642_STILL_GENERATION_RESPONSE_V1" in still_source
    trace_source = (ROOT / "ci_still_vision_evidence_trace_hotfix.py").read_text(encoding="utf-8")
    assert "_patch_still_generation_response()" in trace_source
    final_qa = (ROOT / "ci_final_visual_semantic_qa_hotfix.py").read_text(encoding="utf-8")
    assert "_patch_still_vision_evidence_trace" in final_qa


def test_quality_and_budget_contracts_unchanged():
    source = (ROOT / "video/still_image_fallback.py").read_text(encoding="utf-8")
    assert 'STILL_IMAGE_MAX_PER_VIDEO = int(os.environ.get("STILL_IMAGE_MAX_PER_VIDEO", "2"))' in source
    assert "MAX_INFORMATION_USES_PER_PHYSICAL_STILL = 2" in source
    installer = (ROOT / "ci_run_33506951642_still_generation_response_hotfix.py").read_text(encoding="utf-8")
    forbidden = (
        "HOOK_SUBJECT_DOMINANCE_MIN =",
        "HOOK_ACTION_MATCH_MIN =",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
        "retry",
    )
    for token in forbidden:
        assert token not in installer


if __name__ == "__main__":
    tests = [
        test_production_scene_fixture,
        test_before_fix_exact_valueerror_shape,
        test_after_fix_fail_closed_with_diagnostic_message,
        test_after_fix_uses_existing_url_without_new_generation_call,
        test_after_fix_valid_base64_is_unchanged,
        test_production_composition_wires_fix_after_visual_contracts,
        test_quality_and_budget_contracts_unchanged,
    ]
    for test in tests:
        test()
    print("RUN_33506951642_STILL_GENERATION_VALUEERROR_REGRESSION: PASS")
