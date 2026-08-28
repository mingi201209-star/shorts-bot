from content.script_visual_budget import compact_duplicate_visual_demand


def scene(text, goal, keyword, role="mechanism"):
    return {"text": text, "visual_goal": goal, "keyword": keyword, "role": role}


def run():
    duplicate = scene("같은 정보입니다.", "같은 화면", "aircraft wing")
    script = {
        "scenes": [
            scene("첫 화면입니다.", "윙렛", "aircraft winglet", "phenomenon"),
            duplicate,
            dict(duplicate),
            scene("다른 사실입니다.", "다른 화면", "aircraft vortex"),
            scene("결론입니다.", "결과 화면", "aircraft result", "payoff"),
        ]
    }
    result = compact_duplicate_visual_demand(script)
    assert len(result["scenes"]) == 4
    assert result["script_visual_budget"]["removed_duplicate_count"] == 1
    assert result["script_visual_budget"]["extra_llm_calls"] == 0
    assert result["scenes"][0]["role"] == "phenomenon"
    assert result["scenes"][-1]["role"] == "payoff"

    distinct = {
        "scenes": [
            scene("유도항력을 줄입니다.", "소용돌이", "aircraft wing vortex"),
            scene("연료 효율을 높입니다.", "효율 결과", "aircraft wing efficiency"),
        ]
    }
    untouched = compact_duplicate_visual_demand(distinct)
    assert len(untouched["scenes"]) == 2
    assert untouched["script_visual_budget"]["removed_duplicate_count"] == 0

    protected = {
        "scenes": [
            scene("같은 문장", "같은 화면", "same", "phenomenon"),
            scene("같은 문장", "같은 화면", "same", "phenomenon"),
            scene("결과", "결과", "result", "payoff"),
            scene("결과", "결과", "result", "payoff"),
        ]
    }
    protected_result = compact_duplicate_visual_demand(protected)
    assert len(protected_result["scenes"]) == 4

    # Run 33183845374 production counterexample: exact information beats were
    # repeated with different visual contracts. The later protected reveal/payoff
    # must survive while the earlier intermediate duplicate is removed. If the
    # protected payoff's visual contract is unsupported but the removed duplicate
    # had an existing supported contract, the supported contract should move with
    # the retained information beat without changing narration.
    vortex_text = "날개 끝이 위로 꺾이면 날개 위아래의 압력 차가 소용돌이를 줄여줍니다."
    result_text = "결과적으로 유도항력이 줄어들어 비행기의 연비가 개선됩니다."
    production = {
        "scenes": [
            scene(vortex_text, "압력 차와 소용돌이의 관계", "aircraft wing vortex stage 9", "consequence"),
            scene(result_text, "비행기의 연비 개선", "aircraft wing fuel efficiency stage 10", "consequence"),
            scene(vortex_text, "비행기 날개 끝의 꺾인 형태", "aircraft wing wingtip design stage 11", "reveal"),
            scene(result_text, "비행기 날개 끝의 꺾인 형태", "aircraft wing wingtip question stage 12", "payoff"),
        ]
    }
    production_result = compact_duplicate_visual_demand(production)
    assert len(production_result["scenes"]) == 2
    assert [x["role"] for x in production_result["scenes"]] == ["reveal", "payoff"]
    assert production_result["scenes"][0]["text"] == vortex_text
    assert production_result["scenes"][1]["text"] == result_text
    # Existing supported result visual contract must be preserved on the payoff.
    assert production_result["scenes"][1]["visual_goal"] == "비행기의 연비 개선"
    assert "fuel efficiency" in production_result["scenes"][1]["keyword"]
    assert production_result["script_visual_budget"]["removed_duplicate_count"] == 2
    assert production_result["script_visual_budget"]["extra_llm_calls"] == 0
    print("SCRIPT_VISUAL_BUDGET_V1_REGRESSION_PASS")


if __name__ == "__main__":
    run()
