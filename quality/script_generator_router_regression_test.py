import os
import sys
import types

import content.script_generator_router as router


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾인 이유",
        "angle": "윙렛과 유도항력",
        "core_question": "왜 비행기 날개 끝은 위로 꺾여 있을까요?",
        "micro_narrative": {"hook": "비행기 날개 끝이 위로 꺾여 있습니다."},
        "fact_check_focus": ["압력 차이"],
        "visual_proof": ["winglet"],
        "selection_reason": "aviation continuity",
    }


def main():
    original = os.environ.get("SCRIPT_ENGINE_MODE")
    old_legacy = sys.modules.get("content.script_generator")
    old_v2 = sys.modules.get("content.script_engine_v2_runner")
    try:
        legacy_module = types.ModuleType("content.script_generator")
        legacy_module.generate_script = lambda topic_info, item: {"engine": "legacy"}
        v2_module = types.ModuleType("content.script_engine_v2_runner")
        seen_candidates = []

        def fake_v2(item):
            seen_candidates.append(item)
            scenes = [{
                "text": item["micro_narrative"]["hook"],
                "visual_goal": "show winglet",
                "keyword": "airplane winglet closeup",
            }]
            if item.get("micro_narrative", {}).get("core_question"):
                scenes.append({
                    "text": item["micro_narrative"]["core_question"],
                    "visual_goal": "show winglet question",
                    "keyword": "winglet closeup question",
                })
            if item.get("micro_narrative", {}).get("payoff"):
                scenes.append({
                    "text": item["micro_narrative"]["payoff"],
                    "visual_goal": "show winglet result",
                    "keyword": "winglet efficiency result",
                })
            return {
                "engine": "v2",
                "title": "윙렛의 이유",
                "scenes": scenes,
            }

        v2_module.generate_script_v2 = fake_v2
        sys.modules["content.script_generator"] = legacy_module
        sys.modules["content.script_engine_v2_runner"] = v2_module

        os.environ.pop("SCRIPT_ENGINE_MODE", None)
        result = router.generate_script({"topic": "aviation", "category": "항공"}, candidate())
        assert result["engine"] == "v2"
        assert result["topic"] == candidate()["topic"]
        assert result["category"] == "항공"
        assert result["angle"] == candidate()["angle"]
        assert result["core_question"] == candidate()["core_question"]
        assert result["micro_narrative"] == candidate()["micro_narrative"]
        assert result["fact_check_focus"] == ["압력 차이"]
        assert result["visual_proof"] == ["winglet"]
        assert result["candidate_selection_reason"] == "aviation continuity"
        assert result["scenes"][0]["visual_type"] == "real_world_broll"

        # Production Run 32642764834 shape: Candidate supplies a why-question
        # as Scene 1 even though V2 requires an observable statement.
        question_item = candidate()
        question_item["topic"] = "비행기 날개 끝이 위로 꺾여 있는 이유"
        question_item["micro_narrative"]["hook"] = "왜 비행기 날개 끝이 위로 꺾여 있을까요?"
        original_question = question_item["micro_narrative"]["hook"]
        question_result = router.generate_script(
            {"topic": "aviation", "category": "항공"},
            question_item,
        )
        assert seen_candidates[-1]["micro_narrative"]["hook"] == "비행기 날개 끝이 위로 꺾여 있습니다."
        assert question_result["scenes"][0]["text"] == "비행기 날개 끝이 위로 꺾여 있습니다."
        assert question_result["micro_narrative"]["hook"] == "비행기 날개 끝이 위로 꺾여 있습니다."
        assert question_item["micro_narrative"]["hook"] == original_question

        # Production Run 32840924781 shape: the exact fixed topic is already an
        # observable statement, but Candidate Explorer returns a question Hook.
        statement_topic_item = candidate()
        statement_topic_item["topic"] = "비행기 날개는 일부러 휘어지게 만든다"
        statement_topic_item["micro_narrative"]["hook"] = (
            "왜 비행기 날개는 일부러 휘어지게 만들까요?"
        )
        original_statement_question = statement_topic_item["micro_narrative"]["hook"]
        statement_result = router.generate_script(
            {"topic": "aviation", "category": "항공"},
            statement_topic_item,
        )
        assert seen_candidates[-1]["micro_narrative"]["hook"] == (
            "비행기 날개는 일부러 휘어지게 만듭니다."
        )
        assert statement_result["scenes"][0]["text"] == (
            "비행기 날개는 일부러 휘어지게 만듭니다."
        )
        assert statement_topic_item["micro_narrative"]["hook"] == (
            original_statement_question
        )

        # Production Run 32853693033: a fixed statement topic ending in
        # ~단다 still retained Candidate Explorer's question Hook. Project the
        # exact statement into a formal observable opening before V2 locks it.
        danda_item = candidate()
        danda_item["topic"] = "비행기 엔진은 날개 아래에 단다"
        danda_item["micro_narrative"]["hook"] = (
            "왜 비행기 엔진은 날개 아래에 장착될까요?"
        )
        original_danda_question = danda_item["micro_narrative"]["hook"]
        danda_result = router.generate_script(
            {"topic": "aviation", "category": "항공"},
            danda_item,
        )
        assert seen_candidates[-1]["micro_narrative"]["hook"] == (
            "비행기 엔진은 날개 아래에 답니다."
        )
        assert danda_result["scenes"][0]["text"] == (
            "비행기 엔진은 날개 아래에 답니다."
        )
        assert danda_item["micro_narrative"]["hook"] == original_danda_question

        # Production Run 32643474443 shape: Scene 1 is fixed, but the locked
        # Scene 2 question and payoff arrive in plain-form Korean. They must be
        # normalized before V2 freezes the narration contracts.
        locked_item = candidate()
        locked_item["topic"] = "비행기 날개 끝이 위로 꺾여 있는 이유"
        locked_item["core_question"] = "왜 비행기 날개 끝을 위로 꺾어 놓았을까?"
        locked_item["micro_narrative"] = {
            "hook": "왜 비행기 날개 끝이 위로 꺾여 있을까요?",
            "core_question": "그런데 왜 비행기 날개 끝을 위로 꺾어 놓았을까?",
            "reveal": "윙렛은 날개 끝 소용돌이를 약하게 만들어 유도항력을 줄입니다.",
            "payoff": "결과적으로 비행기의 연료 효율이 개선되고 안정성이 높아진다.",
        }
        original_locked = {
            "core_question": locked_item["core_question"],
            "micro_narrative": dict(locked_item["micro_narrative"]),
        }
        locked_result = router.generate_script(
            {"topic": "aviation", "category": "항공"},
            locked_item,
        )
        normalized = seen_candidates[-1]
        assert normalized["micro_narrative"]["hook"] == "비행기 날개 끝이 위로 꺾여 있습니다."
        assert normalized["core_question"] == "왜 비행기 날개 끝을 위로 꺾어 놓았을까요?"
        assert normalized["micro_narrative"]["core_question"] == "그런데 왜 비행기 날개 끝을 위로 꺾어 놓았을까요?"
        assert normalized["micro_narrative"]["payoff"] == "결과적으로 비행기의 연료 효율이 개선되고 안정성이 높아집니다."
        assert locked_result["scenes"][1]["text"].endswith("놓았을까요?")
        assert locked_result["scenes"][-1]["text"].endswith("높아집니다.")
        assert locked_item["core_question"] == original_locked["core_question"]
        assert locked_item["micro_narrative"] == original_locked["micro_narrative"]

        os.environ["SCRIPT_ENGINE_MODE"] = "legacy"
        assert router.generate_script({"topic": "direction"}, candidate())["engine"] == "legacy"

        os.environ["SCRIPT_ENGINE_MODE"] = "unknown"
        try:
            router.generate_script({}, {})
        except ValueError as exc:
            assert "Unsupported SCRIPT_ENGINE_MODE" in str(exc)
        else:
            raise AssertionError("unsupported mode must fail closed")
    finally:
        if old_legacy is not None:
            sys.modules["content.script_generator"] = old_legacy
        else:
            sys.modules.pop("content.script_generator", None)
        if old_v2 is not None:
            sys.modules["content.script_engine_v2_runner"] = old_v2
        else:
            sys.modules.pop("content.script_engine_v2_runner", None)
        if original is None:
            os.environ.pop("SCRIPT_ENGINE_MODE", None)
        else:
            os.environ["SCRIPT_ENGINE_MODE"] = original

    print("PASS: Script Generator router V2 default + production locked narration normalization + legacy rollback")


if __name__ == "__main__":
    main()
