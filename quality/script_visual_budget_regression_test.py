from content.script_visual_budget import compact_duplicate_visual_demand, information_fingerprint


def scene(text, goal, keyword, role="mechanism", **extra):
    value = {"text": text, "visual_goal": goal, "keyword": keyword, "role": role}
    value.update(extra)
    return value


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

    # CASE 1/5: exact narration is identity even when visual metadata differs;
    # different narration never compacts.
    exact_different_visual = {
        "scenes": [
            scene("같은 설명입니다.", "화면 A", "aircraft wing stage a"),
            scene("같은 설명입니다.", "화면 B", "aircraft wing stage b"),
            scene("다른 설명입니다.", "화면 C", "aircraft wing stage c"),
        ]
    }
    exact_result = compact_duplicate_visual_demand(exact_different_visual)
    assert len(exact_result["scenes"]) == 2
    assert exact_result["scenes"][0]["text"] == "같은 설명입니다."
    assert exact_result["scenes"][1]["text"] == "다른 설명입니다."

    distinct = {
        "scenes": [
            scene("유도항력을 줄입니다.", "소용돌이", "aircraft wing vortex"),
            scene("연료 효율을 높입니다.", "효율 결과", "aircraft wing efficiency"),
        ]
    }
    untouched = compact_duplicate_visual_demand(distinct)
    assert len(untouched["scenes"]) == 2
    assert untouched["script_visual_budget"]["removed_duplicate_count"] == 0

    # CASE 6/7: protected roles are never blindly deleted. Multiple protected
    # duplicates are ambiguous and therefore fail closed/no-op.
    protected = {
        "scenes": [
            scene("같은 문장", "같은 화면", "same", "phenomenon"),
            scene("같은 문장", "다른 화면", "different", "phenomenon"),
            scene("결과", "결과", "result", "payoff"),
            scene("결과", "다른 결과", "other result", "payoff"),
        ]
    }
    protected_result = compact_duplicate_visual_demand(protected)
    assert len(protected_result["scenes"]) == 4

    # CASE 9/10: the normalized narration fingerprint and speech text are unchanged.
    assert information_fingerprint(scene("  같은   문장  ", "A", "B")) == ("같은 문장",)

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
    # CASE 2/3/11/12/13: protected payoff survives, narration is unchanged, and
    # the existing WINGLET_RESULT-compatible visual contract is inherited.
    assert production_result["scenes"][1]["visual_goal"] == "비행기의 연비 개선"
    assert "fuel efficiency" in production_result["scenes"][1]["keyword"]
    assert production_result["script_visual_budget"]["removed_duplicate_count"] == 2
    assert production_result["script_visual_budget"]["visual_contract_inheritance_count"] == 1
    assert production_result["script_visual_budget"]["extra_llm_calls"] == 0

    # CASE 4: unsupported donor must never overwrite protected visual metadata.
    unsupported = {
        "scenes": [
            scene(result_text, "추상적인 날개 질문", "aircraft wing question", "consequence"),
            scene(result_text, "보호된 원래 화면", "aircraft wing protected question", "payoff"),
        ]
    }
    unsupported_result = compact_duplicate_visual_demand(unsupported)
    assert len(unsupported_result["scenes"]) == 1
    assert unsupported_result["scenes"][0]["visual_goal"] == "보호된 원래 화면"
    assert unsupported_result["script_visual_budget"]["visual_contract_inheritance_count"] == 0

    # CASE 8: explicit FACT lineage mismatch blocks inheritance even if donor visual
    # is otherwise supported. Narration remains intact and protected Scene survives.
    fact_mismatch = {
        "scenes": [
            scene(
                result_text,
                "비행기의 연비 개선",
                "aircraft wing fuel efficiency",
                "consequence",
                fact_id="fact-a",
            ),
            scene(
                result_text,
                "보호된 원래 화면",
                "aircraft wing protected question",
                "payoff",
                fact_id="fact-b",
            ),
        ]
    }
    mismatch_result = compact_duplicate_visual_demand(fact_mismatch)
    assert len(mismatch_result["scenes"]) == 1
    assert mismatch_result["scenes"][0]["visual_goal"] == "보호된 원래 화면"
    assert mismatch_result["scenes"][0]["text"] == result_text
    assert mismatch_result["script_visual_budget"]["visual_contract_inheritance_count"] == 0

    # CASE 14/15: compaction is deterministic and adds no calls or budget mutation.
    assert "api_calls" not in production_result["script_visual_budget"]
    assert "cost" not in production_result["script_visual_budget"]
    print("SCRIPT_VISUAL_BUDGET_V1_REGRESSION_PASS")


if __name__ == "__main__":
    run()
