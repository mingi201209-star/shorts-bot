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
    print("SCRIPT_VISUAL_BUDGET_V1_REGRESSION_PASS")


if __name__ == "__main__":
    run()
