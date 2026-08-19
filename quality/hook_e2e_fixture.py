import argparse
import copy
import json

from moviepy.editor import AudioFileClip

from content import hook_experiment
from content.hook_experiment import (
    hook_experiment_enabled,
    select_hook,
    print_hook_audit,
)
from content.script_generator import _apply_selected_hook
from integrations.tts import create_voice
from video import hook_visual
from video.renderer import render_final_video
from video.video_engine import create_scene


TOPIC_INFO = {
    "category": "animals",
    "direction": "visible cat face close-up",
    "fixture": "hook-e2e-approved-input",
}

WINNER = {
    "topic": "고양이 얼굴 클로즈업",
    "core_question": "고양이 얼굴은 가까이에서 어떤 특징이 보일까?",
    "question": "고양이 얼굴은 가까이에서 어떤 특징이 보일까?",
    "micro_narrative": (
        "고양이 얼굴을 가까이 보면 눈, 코, 귀와 수염이 한 화면에 선명하게 보입니다. "
        "카메라에 크게 잡힌 한 마리 고양이의 얼굴 자체를 중심으로 설명합니다."
    ),
    "fact_check_focus": (
        "실제 한 마리 고양이의 얼굴이 가까이 보이는 장면에서 직접 확인 가능한 특징만 다룹니다."
    ),
    "visual_proof": (
        "한 마리 고양이 얼굴이 세로 화면 중앙을 크게 차지하는 실제 클로즈업"
    ),
    "selection_reason": "Deterministic Hook E2E fixture; production quality policy is not changed.",
}

HOOK_CANDIDATE_FIXTURE = [
    {
        "id": "fixture_hook_1",
        "text": "이 고양이 얼굴을 자세히 볼까요?",
        "visual_goal": "한 마리 고양이 얼굴이 화면 중앙에 크게 보이는 실제 세로 클로즈업",
        "keyword": "cat close up",
        "stop_power": 8.6,
        "curiosity_gap": 8.2,
        "clarity": 9.4,
        "specificity": 9.2,
        "visual_potential": 9.8,
        "fact_safety": 9.8,
        "reason": "대사와 화면이 같은 한 마리 고양이 얼굴을 직접 가리킵니다.",
    },
    {
        "id": "fixture_hook_2",
        "text": "고양이 얼굴은 어떻게 보일까요?",
        "visual_goal": "한 마리 고양이 얼굴의 눈과 수염이 선명한 정면 클로즈업",
        "keyword": "cat close up",
        "stop_power": 8.2,
        "curiosity_gap": 8.3,
        "clarity": 9.1,
        "specificity": 8.8,
        "visual_potential": 9.6,
        "fact_safety": 9.8,
        "reason": "한 마리 고양이 얼굴을 즉시 알아볼 수 있는 단순한 첫 화면입니다.",
    },
    {
        "id": "fixture_hook_3",
        "text": "가까운 고양이 얼굴을 볼까요?",
        "visual_goal": "다른 피사체 없이 한 마리 고양이 얼굴이 크게 잡힌 세로 영상",
        "keyword": "cat close up",
        "stop_power": 8.0,
        "curiosity_gap": 7.9,
        "clarity": 9.2,
        "specificity": 9.0,
        "visual_potential": 9.6,
        "fact_safety": 9.8,
        "reason": "관찰 대상이 한 마리 고양이 얼굴로 명확합니다.",
    },
    {
        "id": "fixture_hook_4",
        "text": "이 고양이 얼굴이 잘 보이나요?",
        "visual_goal": "한 마리 고양이 얼굴 특징이 모바일에서도 또렷한 정면 근접 촬영",
        "keyword": "cat close up",
        "stop_power": 8.1,
        "curiosity_gap": 8.1,
        "clarity": 9.0,
        "specificity": 9.1,
        "visual_potential": 9.5,
        "fact_safety": 9.7,
        "reason": "화면에 실제 보이는 고양이 얼굴 특징만 묻습니다.",
    },
    {
        "id": "fixture_hook_5",
        "text": "고양이 얼굴을 가까이서 볼까요?",
        "visual_goal": "한 마리 고양이 얼굴이 화면 대부분을 차지하는 자연스러운 클로즈업",
        "keyword": "cat close up",
        "stop_power": 8.0,
        "curiosity_gap": 7.8,
        "clarity": 9.3,
        "specificity": 9.0,
        "visual_potential": 9.5,
        "fact_safety": 9.8,
        "reason": "첫 화면에서 약속한 고양이 얼굴을 바로 보여줄 수 있습니다.",
    },
]

# Stable real Pexels source used only to remove search-ranking randomness from the
# positive E2E. The production Hook selector, metadata gate, 1080x1920 crop,
# frame extraction, real vision judge, dominance hard gate, and final selection
# still run unchanged. This source is a vertical close-up of one cat face.
CONTROLLED_HOOK_VIDEO = {
    "id": 7592608,
    "url": "https://videos.pexels.com/video-files/7592608/7592608-uhd_2160_3744_30fps.mp4",
    "page_url": "https://www.pexels.com/video/a-close-up-video-of-a-cat-s-face-7592608/",
    "width": 2160,
    "height": 3744,
    "duration": 8.0,
    "search_position": 1,
}

_LAST_HOOK_VISUAL_AUDIT = None


BASE_SCRIPT = {
    "title": "고양이 얼굴을 가까이 보면 보이는 특징",
    "topic": "고양이 얼굴 클로즈업",
    "scenes": [
        {
            "text": "고양이 얼굴을 가까이 보면 눈과 수염이 한 화면에 선명하게 보입니다.",
            "keyword": "cat close up",
            "visual_goal": "한 마리 고양이 얼굴이 화면 중앙에 크게 보이는 실제 세로 클로즈업",
            "visual_type": "real_world_broll",
        },
        {
            "text": "정면에서는 눈, 코, 귀와 얼굴 윤곽을 한 번에 살펴볼 수 있습니다.",
            "keyword": "cat face close up",
            "visual_goal": "한 마리 고양이의 정면 얼굴 윤곽이 또렷한 클로즈업",
            "visual_type": "real_world_broll",
        },
        {
            "text": "조명이 바뀌면 같은 털에서도 얼굴 윤곽의 명암이 다르게 보입니다.",
            "keyword": "cat portrait natural light",
            "visual_goal": "자연광에서 한 마리 고양이 얼굴의 명암이 선명한 근접 장면",
            "visual_type": "real_world_broll",
        },
        {
            "text": "시선이 조금 달라지면 눈과 귀 주변의 모양도 함께 달라져 보입니다.",
            "keyword": "cat expression close up",
            "visual_goal": "한 마리 고양이의 눈과 귀 주변이 잘 보이는 근접 장면",
            "visual_type": "real_world_broll",
        },
        {
            "text": "옆모습에서는 코와 수염처럼 정면과 다른 윤곽이 더 잘 드러납니다.",
            "keyword": "cat face side profile",
            "visual_goal": "한 마리 고양이의 옆얼굴 윤곽이 선명한 클로즈업",
            "visual_type": "real_world_broll",
        },
        {
            "text": "그래서 고양이 얼굴 클로즈업은 작은 특징도 모바일 화면에서 빠르게 확인하게 해줍니다.",
            "keyword": "cat close up portrait",
            "visual_goal": "한 마리 고양이 얼굴이 크게 보이는 세로 클로즈업 마무리",
            "visual_type": "real_world_broll",
        },
    ],
}


def _fixture_search_pexels_candidates(query, per_page):
    del query, per_page
    print("🧪 HOOK VISUAL CONTROLLED SOURCE: Pexels 7592608")
    return [copy.deepcopy(CONTROLLED_HOOK_VIDEO)]


def _capture_hook_visual_audit(audit):
    global _LAST_HOOK_VISUAL_AUDIT
    _LAST_HOOK_VISUAL_AUDIT = copy.deepcopy(audit)
    hook_visual._FIXTURE_ORIGINAL_PRINT_HOOK_VISUAL_AUDIT(audit)


def _fixture_request_candidates(
    topic_info,
    candidate,
    generation_round,
):
    del topic_info, candidate, generation_round
    print("🧪 HOOK FIXTURE CANDIDATES GENERATED: 5")
    return hook_experiment._normalize_candidates({
        "candidates": copy.deepcopy(HOOK_CANDIDATE_FIXTURE),
    })


def _build_script(mode):
    script = copy.deepcopy(BASE_SCRIPT)

    if mode == "off":
        if hook_experiment_enabled():
            raise AssertionError("Hook experiment must be disabled in OFF fixture")
        return script, None, None

    if not hook_experiment_enabled():
        raise AssertionError("Hook experiment must be enabled in ON fixture")

    original_request = hook_experiment._request_candidates
    hook_experiment._request_candidates = _fixture_request_candidates
    try:
        selected, audit = select_hook(
            TOPIC_INFO,
            WINNER,
        )
    finally:
        hook_experiment._request_candidates = original_request

    print_hook_audit(audit)

    if not selected:
        raise AssertionError(
            "Hook selector did not return a threshold-passing fixture hook"
        )

    if audit["attempts"][0]["candidate_count"] != 5:
        raise AssertionError("Hook E2E fixture did not exercise five candidates")

    script = _apply_selected_hook(
        script,
        selected,
        audit,
    )

    first = script["scenes"][0]
    if not first.get("hook_experiment", {}).get("selected"):
        raise AssertionError("Selected Hook was not applied to first scene")

    return script, selected, audit


def _render(script, mode):
    global _LAST_HOOK_VISUAL_AUDIT
    clips = []
    original_search = None
    original_print = None
    _LAST_HOOK_VISUAL_AUDIT = None

    if mode == "on":
        original_search = hook_visual.search_pexels_candidates
        original_print = hook_visual.print_hook_visual_audit
        hook_visual.search_pexels_candidates = _fixture_search_pexels_candidates
        hook_visual._FIXTURE_ORIGINAL_PRINT_HOOK_VISUAL_AUDIT = original_print
        hook_visual.print_hook_visual_audit = _capture_hook_visual_audit

    try:
        for idx, scene in enumerate(script["scenes"]):
            clips.append(
                create_scene(
                    idx,
                    scene,
                    create_voice,
                )
            )

        output = render_final_video(
            clips,
            output_path="final_shorts.mp4",
        )
        return output
    finally:
        if mode == "on":
            hook_visual.search_pexels_candidates = original_search
            hook_visual.print_hook_visual_audit = original_print
            if hasattr(hook_visual, "_FIXTURE_ORIGINAL_PRINT_HOOK_VISUAL_AUDIT"):
                delattr(hook_visual, "_FIXTURE_ORIGINAL_PRINT_HOOK_VISUAL_AUDIT")
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass


def _audio_duration(path):
    clip = AudioFileClip(path)
    try:
        return float(clip.duration)
    finally:
        clip.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("off", "on"),
        required=True,
    )
    args = parser.parse_args()

    script, selected, audit = _build_script(args.mode)
    output = _render(script, args.mode)

    hook_tts_seconds = _audio_duration("scene_0.mp3")

    if args.mode == "on" and hook_tts_seconds > 3.0:
        raise AssertionError(
            f"Actual Hook TTS exceeds 3.0s: {hook_tts_seconds:.3f}s"
        )

    result = {
        "mode": args.mode,
        "fixture": "single-cat-face-controlled-source-v6",
        "production_quality_policy_changed": False,
        "output": output,
        "hook_tts_seconds": round(hook_tts_seconds, 3),
        "selected_hook": selected,
        "hook_audit": audit,
        "controlled_source": (
            copy.deepcopy(CONTROLLED_HOOK_VIDEO)
            if args.mode == "on"
            else None
        ),
        "hook_visual_audit": copy.deepcopy(_LAST_HOOK_VISUAL_AUDIT),
    }

    with open(
        f"hook_{args.mode}_fixture_result.json",
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            result,
            handle,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "✅ FIXTURE E2E COMPLETE | "
        f"mode={args.mode} | hook_tts={hook_tts_seconds:.3f}s"
    )


if __name__ == "__main__":
    main()
