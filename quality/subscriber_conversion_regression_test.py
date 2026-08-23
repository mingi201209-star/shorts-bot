from content.subscriber_conversion import (
    apply_subscriber_conversion,
    build_subscriber_conversion_plan,
    infer_series_identity,
    validate_cta_text,
)


def aviation_candidate():
    return {
        "topic": "비행기 창문은 왜 둥글까",
        "angle": "익숙한 항공기 설계의 숨은 이유",
        "core_question": "비행기 창문 모서리는 왜 둥근가",
        "micro_narrative": {
            "hook": "비행기 창문은 일부러 둥글게 만듭니다.",
            "core_question": "왜 네모나게 만들지 않을까요?",
            "reveal": "압력이 모서리에 집중되는 것을 줄이기 위해서입니다.",
            "payoff": "둥근 형태가 반복 압력 변화에 더 유리합니다.",
        },
        "visual_proof": ["rounded airplane window", "aircraft cabin window"],
    }


def generic_candidate():
    return {
        "topic": "맨홀 뚜껑은 왜 둥글까",
        "angle": "일상 사물의 숨은 설계",
        "core_question": "맨홀 뚜껑이 둥근 이유는 무엇일까",
        "micro_narrative": {
            "hook": "맨홀 뚜껑은 대부분 둥급니다.",
            "core_question": "왜 굳이 둥글게 만들까요?",
            "reveal": "구멍 안으로 빠지기 어려운 형태입니다.",
            "payoff": "단순한 모양이 작업 안전성과 연결됩니다.",
        },
        "visual_proof": ["round manhole cover", "street manhole opening"],
    }


def bridge_candidate():
    return {
        "topic": "우산 끝의 작은 금속 캡",
        "angle": "익숙한 물건의 숨은 기능",
        "core_question": "이 작은 부품은 왜 있을까",
        "micro_narrative": {
            "hook": "우산 끝에는 작은 금속 캡이 있습니다.",
            "core_question": "왜 굳이 붙여둘까요?",
            "reveal": "끝부분을 보호하는 역할이 있습니다.",
            "payoff": "작은 부품이 마모를 줄이는 데 도움이 됩니다.",
        },
        "visual_proof": [],
    }


def weak_candidate():
    return {
        "topic": "고대 항아리 한 점",
        "angle": "유물 소개",
        "core_question": "언제 만들어졌을까",
        "micro_narrative": {},
        "visual_proof": [],
    }


def base_script(max_seconds=30, max_scenes=9, scene_count=7):
    scenes = []
    for index in range(scene_count):
        scenes.append({
            "text": f"짧은 설명 {index + 1}입니다.",
            "visual_goal": f"핵심 대상의 구체적인 변화 {index + 1}",
            "visual_type": "real_world_broll",
            "keyword": "airplane window detail" if index < 3 else "object design detail",
            "retention_role": "" if index >= 3 else ("phenomenon", "consequence", "causal_clue")[index],
        })
    return {
        "title": "fixture",
        "runtime_bucket": "24-30s",
        "retention_structure": {"max_seconds": max_seconds, "max_scenes": max_scenes},
        "scenes": scenes,
    }


def test_modes():
    assert build_subscriber_conversion_plan(aviation_candidate())["subscriber_conversion_mode"] == "soft_series_cta"
    assert build_subscriber_conversion_plan(generic_candidate())["subscriber_conversion_mode"] == "soft_series_cta"
    assert build_subscriber_conversion_plan(bridge_candidate())["subscriber_conversion_mode"] == "curiosity_bridge"
    assert build_subscriber_conversion_plan(weak_candidate())["subscriber_conversion_mode"] == "none"


def test_series_identity():
    assert "비행기" in infer_series_identity(aviation_candidate())
    assert "익숙한" in infer_series_identity(generic_candidate())


def test_language_guard():
    for text in (
        "구독해주세요.",
        "좋아요와 구독 부탁드립니다.",
        "알림 설정도 해주세요.",
        "다음 영상에서 공개합니다.",
    ):
        valid, _ = validate_cta_text(text)
        assert not valid, text
    valid, _ = validate_cta_text("숨은 이유가 더 궁금하시면 구독해 두세요.")
    assert valid


def test_cta_after_payoff():
    script = base_script()
    before = list(script["scenes"])
    result = apply_subscriber_conversion(script, aviation_candidate())
    assert result["cta_added"] is True
    assert len(result["scenes"]) == len(before) + 1
    assert result["scenes"][:-1] == before
    assert result["scenes"][-1]["retention_role"] == "subscriber_conversion"
    assert "구독" not in " ".join(scene["text"] for scene in result["scenes"][:3])


def test_runtime_headroom_omits_cta():
    script = base_script(max_seconds=4, max_scenes=9, scene_count=7)
    result = apply_subscriber_conversion(script, aviation_candidate())
    assert result["cta_added"] is False
    assert result["subscriber_conversion_mode"] == "none"
    assert result["cta_text"] == ""


def test_scene_headroom_omits_cta():
    script = base_script(max_seconds=30, max_scenes=7, scene_count=7)
    result = apply_subscriber_conversion(script, aviation_candidate())
    assert result["cta_added"] is False
    assert result["subscriber_conversion_mode"] == "none"


def main():
    test_modes()
    test_series_identity()
    test_language_guard()
    test_cta_after_payoff()
    test_runtime_headroom_omits_cta()
    test_scene_headroom_omits_cta()
    print("✅ Subscriber Conversion regression PASS")


if __name__ == "__main__":
    main()
