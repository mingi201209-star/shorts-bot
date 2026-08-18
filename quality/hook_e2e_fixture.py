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
from video.renderer import render_final_video
from video.video_engine import create_scene


TOPIC_INFO = {
    "category": "nature",
    "direction": "visible structure and function",
    "fixture": "hook-e2e-approved-input",
}

WINNER = {
    "topic": "벌집의 육각형 구조",
    "core_question": "벌집의 방은 왜 육각형 모양으로 이어져 있을까?",
    "question": "벌집의 방은 왜 육각형 모양으로 이어져 있을까?",
    "micro_narrative": (
        "벌집을 가까이 보면 반복되는 육각형 방이 보인다. "
        "각 방이 맞닿아 이어지는 구조 자체를 중심으로 설명한다."
    ),
    "fact_check_focus": (
        "벌집에서 반복되는 육각형 셀의 형태와 서로 맞닿는 구조만 다룬다."
    ),
    "visual_proof": (
        "실제 벌집의 육각형 셀을 화면에서 직접 식별할 수 있는 클로즈업"
    ),
    "selection_reason": "Deterministic Hook E2E fixture; production quality policy is not changed.",
}

HOOK_CANDIDATE_FIXTURE = [
    {
        "id": "fixture_hook_1",
        "text": "벌집의 방은 왜 육각형일까요?",
        "visual_goal": "육각형 벌집 셀이 화면 중앙에 크게 보이는 실제 벌집 클로즈업",
        "keyword": "honeycomb hexagon close up",
        "stop_power": 8.4,
        "curiosity_gap": 8.2,
        "clarity": 9.0,
        "specificity": 9.0,
        "visual_potential": 9.4,
        "fact_safety": 9.6,
        "reason": "질문과 화면에 같은 벌집 육각형 구조가 직접 등장한다.",
    },
    {
        "id": "fixture_hook_2",
        "text": "벌집 육각형은 어떻게 이어질까요?",
        "visual_goal": "서로 맞닿은 육각형 벌집 셀 여러 개가 선명한 매크로 장면",
        "keyword": "honeycomb cells macro",
        "stop_power": 8.1,
        "curiosity_gap": 8.3,
        "clarity": 8.8,
        "specificity": 8.8,
        "visual_potential": 9.2,
        "fact_safety": 9.6,
        "reason": "맞닿은 셀 구조를 실제 화면으로 바로 검증할 수 있다.",
    },
    {
        "id": "fixture_hook_3",
        "text": "벌집의 육각형 방을 자세히 볼까요?",
        "visual_goal": "실제 벌집의 육각형 방 경계가 또렷한 근접 촬영",
        "keyword": "honeycomb hexagonal cells",
        "stop_power": 7.8,
        "curiosity_gap": 7.6,
        "clarity": 9.2,
        "specificity": 9.1,
        "visual_potential": 9.4,
        "fact_safety": 9.8,
        "reason": "보이는 구조만 말해 사실 위험과 시각 불일치 위험이 낮다.",
    },
    {
        "id": "fixture_hook_4",
        "text": "벌집 방마다 왜 육각형이 보일까요?",
        "visual_goal": "반복되는 육각형 셀 패턴이 크게 보이는 자연 벌집",
        "keyword": "natural honeycomb hexagon",
        "stop_power": 8.0,
        "curiosity_gap": 8.0,
        "clarity": 8.8,
        "specificity": 8.9,
        "visual_potential": 9.3,
        "fact_safety": 9.5,
        "reason": "육각형 반복 패턴이 대사와 화면에서 직접 일치한다.",
    },
    {
        "id": "fixture_hook_5",
        "text": "벌집 속 육각형은 어떻게 맞닿을까요?",
        "visual_goal": "육각형 셀 경계끼리 맞닿은 모습을 식별할 수 있는 벌집 매크로",
        "keyword": "honeycomb pattern macro",
        "stop_power": 8.0,
        "curiosity_gap": 8.2,
        "clarity": 8.7,
        "specificity": 9.0,
        "visual_potential": 9.2,
        "fact_safety": 9.6,
        "reason": "구조적 질문과 시각 증거가 동일한 대상을 가리킨다.",
    },
]

BASE_SCRIPT = {
    "title": "벌집을 가까이 보면 보이는 육각형",
    "topic": "벌집의 육각형 구조",
    "scenes": [
        {
            "text": "벌집을 가까이 보면 작은 방들이 이어져 있습니다.",
            "keyword": "honeycomb close up",
            "visual_goal": "육각형 벌집 셀이 화면 중앙에 크게 보이는 실제 벌집 클로즈업",
            "visual_type": "real_world_broll",
        },
        {
            "text": "각 방의 테두리를 따라가면 반복되는 육각형 모양이 보입니다.",
            "keyword": "honeycomb hexagon macro",
            "visual_goal": "반복되는 육각형 셀 경계가 선명한 벌집 매크로 촬영",
            "visual_type": "real_world_broll",
        },
        {
            "text": "셀들은 빈틈 없이 서로 맞닿아 한 장의 구조처럼 이어집니다.",
            "keyword": "honeycomb cells macro",
            "visual_goal": "서로 맞닿은 벌집 셀 여러 개가 한 화면에 보이는 장면",
            "visual_type": "real_world_broll",
        },
        {
            "text": "벌이 셀 주변을 움직이면 구조의 크기와 반복 패턴도 쉽게 비교됩니다.",
            "keyword": "bees honeycomb close up",
            "visual_goal": "벌과 육각형 벌집 셀이 함께 선명하게 보이는 근접 장면",
            "visual_type": "real_world_broll",
        },
        {
            "text": "다른 부분을 확대해도 같은 육각형 셀이 계속 이어지는 모습을 볼 수 있습니다.",
            "keyword": "honeycomb pattern macro",
            "visual_goal": "벌집의 넓은 부분에서 반복되는 육각 패턴이 명확한 장면",
            "visual_type": "real_world_broll",
        },
        {
            "text": "그래서 벌집은 가까이 볼수록 규칙적인 셀 구조가 더 또렷하게 드러납니다.",
            "keyword": "natural honeycomb detail",
            "visual_goal": "자연 벌집의 육각형 셀 디테일이 또렷한 마무리 장면",
            "visual_type": "real_world_broll",
        },
    ],
}


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


def _render(script):
    clips = []
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
    output = _render(script)

    hook_tts_seconds = _audio_duration("scene_0.mp3")

    if args.mode == "on" and hook_tts_seconds > 3.0:
        raise AssertionError(
            f"Actual Hook TTS exceeds 3.0s: {hook_tts_seconds:.3f}s"
        )

    result = {
        "mode": args.mode,
        "fixture": "honeycomb-visible-structure-v2",
        "production_quality_policy_changed": False,
        "output": output,
        "hook_tts_seconds": round(hook_tts_seconds, 3),
        "selected_hook": selected,
        "hook_audit": audit,
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
