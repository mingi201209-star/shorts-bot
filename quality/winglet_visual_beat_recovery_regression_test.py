from copy import deepcopy

from content.winglet_visual_beat_recovery import recover_unsupported_winglet_visual_beat
from quality.budget_guard import get_budget_status, reset_budget
from video.visual_explanation import plan_explanation


NOISE_TEXT = "윙렛은 소음 감소에도 기여합니다."
NOISE_GOAL = "비행기 소음 감소 이미지"


def candidate(*, evidence=True):
    return {
        "topic": "비행기 날개 끝이 위로 꺾여 있는 이유",
        "angle": "윙렛이 날개 끝 공기 흐름과 유도항력에 미치는 영향",
        "core_question": "왜 비행기 날개 끝을 위로 꺾어 놓았을까?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "왜 비행기 날개 끝을 위로 꺾어 놓았을까?",
            "reveal": "윙렛은 날개 끝 소용돌이를 줄이는 데 도움을 줍니다.",
            "payoff": "그 결과 비행 효율 개선에 도움을 줍니다.",
        },
        "fact_check_focus": ["윙렛과 유도항력의 관계"],
        "visual_proof": ["윙렛 주변의 공기 흐름"] if evidence else [],
    }


def production_script(*, airflow_narrated=False, include_grounded_contract=True):
    scene3_goal = "윙렛의 공기 흐름 시뮬레이션" if include_grounded_contract else "윙렛과 유도항력 설명"
    scene3_keyword = "aircraft wing induced drag airflow stage 3" if include_grounded_contract else "aircraft wing induced drag stage 3"
    scene4_text = "윙렛은 날개 끝의 공기 흐름을 바꿉니다." if airflow_narrated else "윙렛은 비행기 날개의 디자인 중 하나입니다."
    return {
        "title": "비행기 날개 끝의 비밀",
        "script_engine": "v2",
        "script_engine_v2_calls": 1,
        "scenes": [
            {"text": "비행기 날개 끝이 위로 꺾여 있습니다.", "visual_goal": "비행기 날개의 윙렛 디자인", "keyword": "aircraft wing wingtip design stage 1", "role": "phenomenon"},
            {"text": "그런데 왜 비행기 날개 끝을 위로 꺾어 놓았을까요?", "visual_goal": "비행기 날개 끝 질문", "keyword": "aircraft wing wingtip question stage 2", "role": "question"},
            {"text": "원인의 첫 단서는 윙렛은 유도항력을 줄이는 데 기여합니다.", "visual_goal": scene3_goal, "keyword": scene3_keyword, "role": "causal_clue"},
            {"text": scene4_text, "visual_goal": "비행기 날개와 윙렛의 비교", "keyword": "aircraft wing winglet design stage 4", "role": "mechanism_1"},
            {"text": "윙렛은 비행기의 안정성을 높입니다.", "visual_goal": "윙렛과 비행 안정성", "keyword": "aircraft wing stability improvement stage 5", "role": "mechanism_2"},
            {"text": "윙렛은 연료 효율성을 높이는 데 도움을 줍니다.", "visual_goal": "윙렛과 연료 효율", "keyword": "aircraft wing fuel efficiency stage 6", "role": "mechanism_3"},
            {"text": NOISE_TEXT, "visual_goal": NOISE_GOAL, "keyword": "aircraft wing noise reduction stage 7", "role": "mechanism_4"},
            {"text": "윙렛은 비행 성능 개선에 도움을 줍니다.", "visual_goal": "윙렛의 비행 성능 결과", "keyword": "aircraft wing flight performance stage 8", "role": "consequence"},
            {"text": "윙렛은 날개 끝 소용돌이를 줄이는 데 도움을 줍니다.", "visual_goal": "윙렛과 날개 끝 소용돌이", "keyword": "aircraft wing vortex reduction stage 9", "role": "reveal"},
            {"text": "그 결과 비행 효율 개선에 도움을 줍니다.", "visual_goal": "윙렛의 효율 개선 결과", "keyword": "aircraft wing improved efficiency stage 10", "role": "payoff"},
        ],
    }


def assert_unchanged(before, after):
    assert after == before, (before, after)


def main():
    # BEFORE: the exact Run 33169424813 Scene 7 has no supported explanation plan.
    original = production_script()
    before_scene7 = original["scenes"][6]
    assert before_scene7["text"] == NOISE_TEXT
    assert before_scene7["visual_goal"] == NOISE_GOAL
    assert plan_explanation(before_scene7) is None

    # CASE 1/2/8: recovery is deterministic, aligns all semantic fields, and costs 0 calls.
    reset_budget()
    budget_before = get_budget_status()
    recovered = recover_unsupported_winglet_visual_beat(original, candidate())
    budget_after = get_budget_status()
    scene7 = recovered["scenes"][6]
    assert scene7["text"] == "윙렛은 날개 끝의 공기 흐름을 바꿉니다."
    assert scene7["visual_goal"] == "윙렛 주변 날개 끝 공기 흐름 방향"
    assert scene7["keyword"] == "aircraft wing airflow direction stage 7"
    assert recovered["script_engine_v2_calls"] == original["script_engine_v2_calls"]
    assert budget_after["calls"] == budget_before["calls"] == 0
    assert budget_after["cost_usd"] == budget_before["cost_usd"] == 0.0
    plan = plan_explanation(scene7)
    assert plan is not None
    assert plan["template"] == "WINGLET_FLOW"
    assert plan["scene_role"] == "mechanism"

    # CASE 3: information duplicate in narration -> reject rather than rephrase it.
    duplicate = production_script(airflow_narrated=True)
    assert_unchanged(duplicate, recover_unsupported_winglet_visual_beat(duplicate, candidate()))

    # CASE 4: without candidate evidence or the existing induced-drag+airflow contract, fail closed.
    ungrounded = production_script(include_grounded_contract=False)
    assert_unchanged(
        ungrounded,
        recover_unsupported_winglet_visual_beat(ungrounded, candidate(evidence=False)),
    )

    # Existing production script contract itself is acceptable grounding when Candidate evidence is sparse.
    grounded_by_script = production_script(include_grounded_contract=True)
    script_grounded_result = recover_unsupported_winglet_visual_beat(
        grounded_by_script,
        candidate(evidence=False),
    )
    assert script_grounded_result["scenes"][6]["text"] != NOISE_TEXT
    assert script_grounded_result["winglet_visual_beat_recovery"]["grounding"] == "existing_script_contract"

    # CASE 5: non-winglet noise scene must never be rewritten.
    non_winglet_candidate = deepcopy(candidate())
    non_winglet_candidate["topic"] = "도시 도로 소음이 줄어드는 이유"
    non_winglet_candidate["angle"] = "도로 표면"
    non_winglet_candidate["core_question"] = "도로 소음은 왜 달라질까?"
    non_winglet_candidate["micro_narrative"] = {
        "hook": "도로 표면은 서로 다릅니다.",
        "reveal": "표면 구조가 다릅니다.",
        "payoff": "소리 전달도 달라집니다.",
    }
    assert_unchanged(original, recover_unsupported_winglet_visual_beat(original, non_winglet_candidate))

    # CASE 6: an already-supported winglet scene is a no-op.
    supported = production_script()
    supported["scenes"][6] = {
        "text": "윙렛은 날개 끝 소용돌이를 줄이는 데 도움을 줍니다.",
        "visual_goal": "윙렛과 날개 끝 소용돌이",
        "keyword": "aircraft wing vortex reduction stage 7",
        "role": "mechanism_4",
    }
    assert plan_explanation(supported["scenes"][6])["template"] == "WINGLET_VORTEX"
    assert_unchanged(supported, recover_unsupported_winglet_visual_beat(supported, candidate()))

    # CASE 7: unrelated unsupported concept remains unsupported/fail-closed.
    unrelated = production_script()
    unrelated["scenes"][6] = {
        "text": "윙렛은 정비 시간을 줄이는 데 기여합니다.",
        "visual_goal": "윙렛 정비 시간 감소 이미지",
        "keyword": "aircraft wing maintenance time stage 7",
        "role": "mechanism_4",
    }
    assert plan_explanation(unrelated["scenes"][6]) is None
    assert_unchanged(unrelated, recover_unsupported_winglet_visual_beat(unrelated, candidate()))

    print("✅ Winglet unsupported visual beat recovery regression PASS")


if __name__ == "__main__":
    main()
