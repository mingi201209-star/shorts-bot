import copy

import content.script_generator_router as router
from content.script_engine_v2 import build_narrative_plan


def chevrons_candidate():
    question = "비행기 엔진 뒤쪽의 톱니 모양은 왜 그렇게 설계되었을까?"
    return {
        "topic": "비행기 엔진 뒤는 왜 톱니처럼 생겼을까",
        "angle": "제트 엔진 셰브론의 공기 혼합과 소음 저감",
        "core_question": question,
        "micro_narrative": {
            "hook": question,
            "core_question": question,
            "reveal": "톱니 가장자리는 서로 다른 속도의 공기 흐름이 더 부드럽게 섞이도록 돕습니다.",
            "payoff": "그 결과 제트 소음을 줄이는 데 도움이 됩니다.",
        },
        "fact_check_focus": ["chevron identity", "hot/cool airflow mixing", "jet-noise reduction"],
        "visual_proof": ["jet engine nacelle nozzle chevrons"],
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "subject_kind": "physical_entity",
    }


def main():
    item = chevrons_candidate()
    original = copy.deepcopy(item)

    normalized = router._observable_hook_from_candidate(item)
    normalized = router._normalize_locked_candidate_narration(normalized)

    assert item == original, "router projection must not mutate Candidate input"
    assert normalized["core_question"].endswith("을까요?")
    assert normalized["micro_narrative"]["core_question"].endswith("을까요?")
    assert normalized["micro_narrative"]["hook"] == "비행기 엔진 뒤는 톱니처럼 생겼습니다."
    assert "?" not in normalized["micro_narrative"]["hook"]

    plan = build_narrative_plan(normalized)
    scene1, scene2 = plan["contracts"][:2]
    assert scene1["role"] == "phenomenon"
    assert scene1["locked"] is True
    assert scene1["locked_text"] == "비행기 엔진 뒤는 톱니처럼 생겼습니다."
    assert scene2["role"] == "question"
    assert scene2["locked"] is True
    assert scene2["locked_text"].startswith("그런데 ")
    assert scene2["locked_text"].endswith("?")
    assert scene2["locked_text"] != scene1["locked_text"]

    # Already-correct Scene 1 observations are byte-for-byte preserved.
    already_good = chevrons_candidate()
    already_good["micro_narrative"]["hook"] = "제트 엔진 뒤에는 톱니 모양 가장자리가 있습니다."
    good_normalized = router._observable_hook_from_candidate(already_good)
    assert good_normalized["micro_narrative"]["hook"] == already_good["micro_narrative"]["hook"]

    # Already-formal Scene 2 questions are preserved.
    formal_scene2 = chevrons_candidate()
    formal_scene2["core_question"] = "왜 이런 모양으로 설계했을까요?"
    formal_scene2["micro_narrative"]["core_question"] = "그런데 왜 이런 모양으로 설계했을까요?"
    formal_normalized = router._normalize_locked_candidate_narration(formal_scene2)
    assert formal_normalized["core_question"] == formal_scene2["core_question"]
    assert formal_normalized["micro_narrative"]["core_question"] == formal_scene2["micro_narrative"]["core_question"]

    # Non-physical/unsupported question hooks must stay on their existing path:
    # this physical-observation projection neither rewrites nor invents one.
    unsupported = {
        "topic": "사람들은 왜 이야기를 좋아할까",
        "core_question": "왜 사람들은 이야기를 좋아할까요?",
        "micro_narrative": {
            "hook": "왜 사람들은 이야기를 좋아할까요?",
            "core_question": "왜 사람들은 이야기를 좋아할까요?",
            "reveal": "여러 요인이 함께 작용합니다.",
            "payoff": "맥락에 따라 다르게 나타납니다.",
        },
        "fact_check_focus": [],
        "visual_proof": [],
    }
    unsupported_original = copy.deepcopy(unsupported)
    unsupported_normalized = router._observable_hook_from_candidate(unsupported)
    assert unsupported == unsupported_original
    assert unsupported_normalized == unsupported_original

    print("PASS: Script V2 Opening Role Contract regression")


if __name__ == "__main__":
    main()
