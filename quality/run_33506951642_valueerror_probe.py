from __future__ import annotations

from video import hook_visual_dominance as dominance
from video import still_image_fallback as still


SCENE = {
    "role": "phenomenon",
    "scene_role": "phenomenon",
    "text": "제트 엔진의 노즐 끝에 있는 치프론을 자세히 살펴보면, 그 형상이 독특하다는 것을 알 수 있습니다.",
    "visual_goal": "치프론의 독특한 형상",
    "keyword": "jet engine nacelle nozzle chevron serrated",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron", "chevrons"],
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
    },
}


class PromptBuilt(Exception):
    pass


def main() -> None:
    contract = still._canonical_still_contract(SCENE)
    assert contract["required_viewpoint"] == "rear or rear-quarter close-up of the trailing edge"

    original_extract = dominance._extract_vertical_frames
    original_authorize = dominance.authorize_call
    try:
        # The Run 33506951642 crash happened while evaluating the Vision prompt,
        # before API authorization. A synthetic frame path is enough to exercise
        # that exact f-string construction without any network/API call.
        dominance._extract_vertical_frames = lambda _url: ["synthetic-frame.jpg"]

        def stop_after_prompt(*_args, **_kwargs):
            raise PromptBuilt("prompt constructed without ValueError")

        dominance.authorize_call = stop_after_prompt
        candidate = {
            "id": "run33506951642-regression",
            "source_id": "run33506951642-regression",
            "provider": "openai_image",
            "source_type": "ai_generated_still_motion",
            "url": "synthetic-run33506951642.mp4",
            "duration": 6.86,
            "width": 1080,
            "height": 1920,
            "search_position": 0,
        }
        try:
            dominance.evaluate_hook_subject_dominance(candidate, SCENE)
        except PromptBuilt:
            pass
        else:
            raise AssertionError("expected prompt construction sentinel")
    finally:
        dominance._extract_vertical_frames = original_extract
        dominance.authorize_call = original_authorize

    print("RUN_33506951642_VALUEERROR_REGRESSION_PASS")


if __name__ == "__main__":
    main()
