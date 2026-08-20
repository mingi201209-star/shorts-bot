import os
from pathlib import Path

from content import hook_experiment, script_generator
from integrations import tts
from video import hook_visual, hook_visual_dominance


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"✅ PASS | {message}")


def _scene(text, keyword="cat face close up"):
    return {
        "text": text,
        "visual_goal": "한 마리 고양이 얼굴이 화면 중앙에 크게 보이는 실제 클로즈업",
        "keyword": keyword,
    }


def test_first_five_structure():
    source = Path("content/script_generator.py").read_text(encoding="utf-8")
    _assert(
        "[FIRST 5 SECONDS — RETENTION]" in source,
        "Script prompt contains explicit first-five retention structure",
    )
    _assert(
        "0~2초" in source and "2~5초" in source,
        "Script prompt separates 0~2s anomaly from 2~5s why/clue",
    )

    for phrase in (
        "알려드릴게요",
        "알려드려요",
        "알아봅니다",
        "보여드릴게요",
        "보여드려요",
        "소개합니다",
    ):
        _assert(
            phrase in script_generator.HOOK_BANNED_PATTERNS,
            f"First-five introductory phrase banned: {phrase}",
        )

    scenes = [
        _scene("이 건물에는 사람이 쓰지 않는 층이 있습니다."),
        _scene("그 이유를 지금 알려드릴게요."),
    ] + [
        _scene(f"설비 공간의 역할을 실제 구조로 설명합니다 {idx}.")
        for idx in range(10)
    ]
    valid, reason = script_generator.validate_scenes(scenes)
    _assert(
        not valid and "첫 5초 금지 표현" in reason,
        "Intro/preview wording cannot pass in the second opening scene",
    )

    scenes[1] = _scene("바로 이 층에 공조와 배관 설비가 들어갑니다.")
    valid, reason = script_generator.validate_scenes(scenes)
    _assert(valid, f"Direct second-scene answer clue remains valid: {reason}")


def test_tts_supported_prosody_only():
    _assert(tts.TTS_RATE == "+13%", "Production Hook/base TTS rate remains +13%")

    hook = tts.resolve_tts_prosody(
        "이 건물에는 빈 층이 있습니다.",
        hook_mode=True,
    )
    question = tts.resolve_tts_prosody(
        "왜 이런 층이 필요할까요?",
        hook_mode=False,
    )
    body = tts.resolve_tts_prosody(
        "이곳에는 공조와 배관 설비가 들어갑니다.",
        hook_mode=False,
    )

    _assert(
        hook["rate"] == "+13%" and hook["pitch"] == "+3Hz",
        "Hook keeps +13% energy with a small supported pitch lift",
    )
    _assert(
        question["rate"] == "+8%" and question["pitch"] == "+2Hz",
        "Body question uses calmer rate and small pitch lift",
    )
    _assert(
        body["rate"] == "+8%" and body["pitch"] == "-1Hz",
        "Body explanation uses calmer rate and small pitch lowering",
    )

    source = Path("integrations/tts.py").read_text(encoding="utf-8")
    _assert("<emphasis" not in source, "No fake SSML emphasis inserted")
    _assert("<break" not in source, "No unsupported SSML break inserted")


def test_first_five_visual_strict_path():
    original_search = hook_visual.search_pexels_candidates
    original_fallback = hook_visual.fetch_pexels_video
    try:
        good = {
            "id": 7592608,
            "url": "fixture://strict-cat",
            "page_url": "https://www.pexels.com/video/a-close-up-video-of-a-cat-s-face-7592608/",
            "width": 2160,
            "height": 3744,
            "duration": 8.0,
            "search_position": 1,
        }
        hook_visual.USED_VIDEO_IDS.discard(good["id"])
        hook_visual.search_pexels_candidates = lambda *args, **kwargs: [good]
        hook_visual.fetch_pexels_video = lambda query: "fixture://legacy"

        selected = hook_visual.fetch_early_retention_pexels_video({
            "keyword": "cat face close up",
            "visual_goal": "고양이 얼굴이 세로 화면 대부분을 차지하는 실제 클로즈업",
        })
        _assert(
            selected == "fixture://strict-cat",
            "Second opening scene uses existing Hook metadata strict gate",
        )

        bad = {
            "id": 990001,
            "url": "fixture://bad",
            "page_url": "https://www.pexels.com/video/generic-background-990001/",
            "width": 1920,
            "height": 1080,
            "duration": 8.0,
            "search_position": 1,
        }
        hook_visual.search_pexels_candidates = lambda *args, **kwargs: [bad]
        selected = hook_visual.fetch_early_retention_pexels_video({
            "keyword": "cat face close up",
            "visual_goal": "고양이 얼굴이 세로 화면 대부분을 차지하는 실제 클로즈업",
        })
        _assert(
            selected == "fixture://legacy",
            "Weak early visual is not promoted as strict",
        )
    finally:
        hook_visual.search_pexels_candidates = original_search
        hook_visual.fetch_pexels_video = original_fallback


def test_protected_thresholds():
    _assert(
        abs(hook_experiment.HOOK_MIN_SCORE - 7.2) < 1e-9,
        "Hook threshold remains 7.2",
    )
    _assert(
        hook_experiment.HOOK_CRITERIA_FLOORS == {
            "clarity": 7.0,
            "specificity": 7.0,
            "visual_potential": 8.0,
            "fact_safety": 8.0,
        },
        "Hook hard floors remain 7/7/8/8",
    )
    _assert(
        hook_visual.HOOK_VISUAL_FLOORS == {
            "semantic_match": 7.0,
            "subject_visibility": 7.0,
            "mobile_clarity": 8.0,
        },
        "Existing Hook metadata strict floors are unchanged",
    )
    _assert(
        hook_visual_dominance.HOOK_SUBJECT_DOMINANCE_MIN == 8.0,
        "Subject dominance threshold remains 8.0",
    )
    _assert(
        hook_visual_dominance.HOOK_MAX_COMPETING_SUBJECT_RISK == 4.0,
        "Competing subject threshold remains 4.0",
    )
    _assert(
        hook_visual_dominance.HOOK_ACTION_MATCH_MIN == 7.0,
        "Action-match threshold remains 7.0",
    )

    engine_source = Path("video/video_engine.py").read_text(encoding="utf-8")
    _assert(
        "fetch_early_retention_pexels_video" in engine_source
        and "elif idx == 1:" in engine_source,
        "Only the second opening scene receives the extra metadata strict path",
    )
    _assert(
        '"hook_mode" in voice_params' in engine_source,
        "Video engine passes Hook context without breaking two-argument voice fixtures",
    )


def main():
    test_first_five_structure()
    test_tts_supported_prosody_only()
    test_first_five_visual_strict_path()
    test_protected_thresholds()
    print("✅ FIRST-5 RETENTION + TTS HUMANIZATION REGRESSION PASS")


if __name__ == "__main__":
    main()
