"""Run 33618913580: audience-first Writer regression without duration gaming."""
from pathlib import Path
import importlib
import runpy
import sys


OLD_SCRIPT = [
    "제트 엔진의 노즐 끝에 있는 작은 돌출부, 치프론이 있습니다.",
    "그런데 왜 제트 엔진의 노즐에 치프론이 추가되었을까요?",
    "원인의 첫 단서는 엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 서로 만납니다.",
    "톱니 모양 셰브론은 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
    "이 혼합 변화의 대표적인 결과는 제트 엔진 소음 감소입니다.",
]

GOOD_SCRIPT = [
    "비행기 엔진 뒤를 보면 톱니처럼 뾰족한 부분이 있습니다. 이 부분을 치프론이라고 합니다.",
    "그런데 왜 제트 엔진의 노즐에 치프론이 추가되었을까요?",
    "엔진 뒤에서는 뜨거운 배기 흐름과 더 차가운 바깥쪽 흐름이 만납니다. 이 경계가 중요한 이유는 바로 이곳의 혼합이 치프론이 바꾸는 대상이기 때문입니다.",
    "치프론은 그 경계에서 배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다. 즉 앞 장면의 두 흐름이 만나는 구간에 장치가 작용합니다.",
    "그리고 이 혼합 방식의 변화는 제트 엔진 소음 감소라는 결과로 이어집니다. 그래서 앞의 흐름 변화와 마지막 소음 감소가 하나의 인과 흐름으로 연결됩니다.",
]


def _candidate():
    return {
        "topic": "jet engine nacelle/nozzle chevrons",
        "angle": "why the serrated trailing edge exists",
        "core_question": "왜 제트 엔진의 노즐에 치프론이 추가되었을까?",
        "micro_narrative": {
            "hook": OLD_SCRIPT[0],
            "core_question": "왜 제트 엔진의 노즐에 치프론이 추가되었을까?",
            "reveal": OLD_SCRIPT[3],
            "payoff": OLD_SCRIPT[4],
        },
        "fact_check_focus": [
            "hot exhaust and cooler ambient flow meet behind the engine",
            "chevrons alter exhaust and ambient-flow mixing",
            "the mixing change is linked to jet-engine noise reduction",
        ],
        "visual_proof": ["rear nozzle", "serrated chevron edge", "flow interface"],
    }


def _scene(text, goal, keyword):
    return {"text": text, "visual_goal": goal, "keyword": keyword}


def main():
    # Production composition entry point. No API calls are made.
    runpy.run_path("ci_script_v2_gunggeum_formal_ending_hotfix.py", run_name="__main__")
    sys.modules.pop("content.script_engine_v2", None)
    engine = importlib.import_module("content.script_engine_v2")

    # Keep this regression independent of Retention Story V2 policy. We test
    # only the Writer boundary that consumes an already-decided five-scene plan.
    engine.build_retention_plan = lambda candidate: {
        "runtime_bucket": "counterexample-only",
        "target_scene_count": 5,
    }
    plan = engine.build_narrative_plan(_candidate())
    contracts = plan["contracts"]
    assert [c["text_lock_mode"] for c in contracts] == [
        "semantic", "exact", "open", "semantic", "semantic"
    ]

    payload = engine.writer_payload(_candidate(), plan)
    rules = payload["rules"]
    assert rules["assume_zero_domain_knowledge"] is True
    assert rules["visual_referent_before_unfamiliar_term"] is True
    assert rules["plain_language_location_then_technical_name"] is True
    assert rules["consistent_primary_term_per_concept"] is True
    assert rules["claim_mentioned_is_not_explanation"] is True
    assert rules["bridge_each_causal_step_for_a_general_viewer"] is True
    assert rules["grounded_explanation_only"] is True
    assert rules["no_padding_or_repetition"] is True
    assert rules["no_fixed_duration_target"] is True
    assert "compress_single_causal_chain" not in rules

    # The old behavior forcibly restored Scene 1/reveal/payoff from the plan,
    # which made Writer audience improvements impossible. Semantic locks now
    # preserve Writer wording while the exact question remains locked.
    generated = {
        "title": "test",
        "scenes": [
            _scene(GOOD_SCRIPT[0], "rear engine serrated edge", "jet engine chevron rear"),
            _scene("writer tried to alter the question", "question visual", "jet engine chevron question"),
            _scene(GOOD_SCRIPT[2], "flow boundary", "jet engine flow interface"),
            _scene(GOOD_SCRIPT[3], "mixing change", "jet engine chevron mixing"),
            _scene(GOOD_SCRIPT[4], "noise result", "jet engine noise reduction"),
        ],
    }
    applied = engine.apply_locked_scenes(generated, plan)
    assert applied["scenes"][0]["text"] == GOOD_SCRIPT[0]
    assert applied["scenes"][1]["text"] == "그런데 왜 제트 엔진의 노즐에 치프론이 추가되었을까요?"
    assert applied["scenes"][3]["text"] == GOOD_SCRIPT[3]
    assert applied["scenes"][4]["text"] == GOOD_SCRIPT[4]

    # TERM-FIRST / weak-referent counterexample is explicitly present in the
    # source lock, but it is no longer forced back over the Writer's visual-first
    # wording. One primary Korean term is used across the improved script.
    assert "톱니처럼" in applied["scenes"][0]["text"]
    assert applied["scenes"][0]["text"].find("톱니") < applied["scenes"][0]["text"].find("치프론")
    assert all("셰브론" not in scene["text"] for scene in applied["scenes"])
    assert sum("치프론" in scene["text"] for scene in applied["scenes"]) >= 3

    # CLAIM != EXPLANATION: the good fixture adds only bridges already supported
    # by the three supplied facts; it does not invent a finer-grained mechanism.
    assert "경계가 중요한 이유" in applied["scenes"][2]["text"]
    assert "앞 장면" in applied["scenes"][3]["text"] and "섞이는 방식" in applied["scenes"][3]["text"]
    assert "인과 흐름" in applied["scenes"][4]["text"] and "소음 감소" in applied["scenes"][4]["text"]
    assert OLD_SCRIPT[2] != applied["scenes"][2]["text"]
    assert OLD_SCRIPT[3] != applied["scenes"][3]["text"]
    assert OLD_SCRIPT[4] != applied["scenes"][4]["text"]

    # System guidance must implement the same contract in the existing Writer
    # call. No second reviewer/rewrite call is introduced.
    runner_source = Path("content/script_engine_v2_runner.py").read_text(encoding="utf-8")
    assert "SCRIPT_V2_AUDIENCE_WRITER_GUIDANCE_V1" in runner_source
    for phrase in (
        "zero domain knowledge",
        "visible feature in plain language",
        "one primary Korean term",
        "do not merely name claims",
        "never compress away a necessary causal bridge",
        "never pad or repeat",
    ):
        assert phrase in runner_source

    # Duration gaming / cost / retry guards. This fix changes Writer guidance,
    # not timing, scene holds, TTS rate, call count, or cost ceilings.
    hotfix = Path("ci_writer_audience_comprehension_hotfix.py").read_text(encoding="utf-8")
    assert plan["audience_comprehension"]["fixed_duration_target"] is False
    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    for forbidden in (
        "authorize_call(", "openai.", "gpt-image", "AI_MAX_GENERATIONS",
        "TTS_RATE", "rate=", "duration =", "sleep(",
    ):
        assert forbidden not in hotfix

    # FACT-safety guidance forbids inventing detail and does not hardcode the
    # tempting unsupported mechanisms from the Human QA discussion.
    for unsafe in ("큰 소용돌이를 작은", "저주파", "고주파", "fuel efficiency", "thrust improvement"):
        assert unsafe not in hotfix

    print("RUN 33618913580 WRITER AUDIENCE COMPREHENSION REGRESSION: PASS")


if __name__ == "__main__":
    main()
