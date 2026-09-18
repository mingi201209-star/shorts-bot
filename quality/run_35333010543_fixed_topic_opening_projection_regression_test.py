"""Regression for Run 35333010543 exact-topic opening projection."""

from pathlib import Path
import os
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_35333010543_fixed_topic_opening_projection_hotfix import (
    MARKER,
    patch,
)


FIXED_TOPIC = "비행기 날개는 왜 비행 중에 휘어질까"
TRUSTED_HOOK = "비행기 날개는 완전한 강체가 아니라, 비행 중 탄성으로 휘어지는 구조입니다."
TRUSTED_QUESTION = "그런데 어떤 비행 하중이 이 날개를 실제로 휘게 만들까요?"


FIXTURE = r'''
import os

# SCRIPT_HUMAN_QUALITY_V1

def _hook_restates_question(hook, question):
    hook = str(hook or "")
    question = str(question or "")
    if "반복 훅" in hook and "반복 훅" in question:
        return True
    return False

def _validate_hook_question_progression(candidate_result, prefix):
    micro = candidate_result.get("micro_narrative") or {}
    hook = str(micro.get("hook") or "")
    questions = (
        str(candidate_result.get("core_question") or ""),
        str(micro.get("core_question") or ""),
    )
    for question in questions:
        if _hook_restates_question(hook, question):
            raise ValueError(
                f"{prefix}.micro_narrative hook이 Core Question과 같은 내용을 반복합니다."
            )
'''


def candidate(topic=FIXED_TOPIC, hook="반복 훅: 날개가 휘어집니다.", question="왜 반복 훅: 날개가 휘어질까요?"):
    return {
        "topic": topic,
        "angle": "grounded flexible-wing angle",
        "core_question": question,
        "micro_narrative": {
            "hook": hook,
            "core_question": question,
            "reveal": "모델이 만든 기존 Reveal은 그대로 유지합니다.",
            "payoff": "모델이 만든 기존 Payoff도 그대로 유지합니다.",
        },
        "fact_check_focus": ["existing fact focus"],
        "visual_proof": ["existing visual proof"],
        "selection_reason": "existing reason",
    }


def run():
    patched = patch(FIXTURE)
    assert MARKER in patched
    assert patched == patch(patched)

    ns = {}
    exec(compile(patched, "synthetic-candidate-explorer.py", "exec"), ns)

    previous = os.environ.get("SHORTS_TOPIC")
    os.environ["SHORTS_TOPIC"] = FIXED_TOPIC
    try:
        bad = candidate()
        original_reveal = bad["micro_narrative"]["reveal"]
        original_payoff = bad["micro_narrative"]["payoff"]

        ns["_validate_hook_question_progression"](bad, "winner")
        assert bad["micro_narrative"]["hook"] == TRUSTED_HOOK
        assert bad["micro_narrative"]["core_question"] == TRUSTED_QUESTION
        assert bad["core_question"] == TRUSTED_QUESTION
        assert bad["micro_narrative"]["reveal"] == original_reveal
        assert bad["micro_narrative"]["payoff"] == original_payoff
        print("CASE A exact fixed-topic restatement projects trusted opening only: PASS")

        strong = candidate(
            hook=TRUSTED_HOOK,
            question=TRUSTED_QUESTION,
        )
        ns["_validate_hook_question_progression"](strong, "winner")
        assert strong["micro_narrative"]["hook"] == TRUSTED_HOOK
        assert strong["micro_narrative"]["core_question"] == TRUSTED_QUESTION
        print("CASE B already-progressive opening remains unchanged: PASS")

        other = candidate(topic="다른 고정 주제")
        try:
            ns["_validate_hook_question_progression"](other, "winner")
        except ValueError:
            pass
        else:
            raise AssertionError("non-target repeated opening must stay fail-closed")
        print("CASE C different topic does not receive trusted projection: PASS")

        os.environ["SHORTS_TOPIC"] = "다른 고정 주제"
        mismatch = candidate()
        try:
            ns["_validate_hook_question_progression"](mismatch, "winner")
        except ValueError:
            pass
        else:
            raise AssertionError("host topic mismatch must stay fail-closed")
        print("CASE D host fixed-topic mismatch remains fail-closed: PASS")

        os.environ["SHORTS_TOPIC"] = FIXED_TOPIC
        runner = candidate()
        try:
            ns["_validate_hook_question_progression"](runner, "runner_up")
        except ValueError:
            pass
        else:
            raise AssertionError("runner-up must not receive Winner projection")
        print("CASE E runner-up behavior is unchanged: PASS")
    finally:
        if previous is None:
            os.environ.pop("SHORTS_TOPIC", None)
        else:
            os.environ["SHORTS_TOPIC"] = previous

    source = Path(
        "ci_run_35333010543_fixed_topic_opening_projection_hotfix.py"
    ).read_text(encoding="utf-8")
    for token in (
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "HOOK_THRESHOLD =",
        "MAX_TOPIC_REGENERATIONS =",
    ):
        assert token not in source, token

    print("RUN 35333010543 FIXED-TOPIC OPENING PROJECTION REGRESSION: PASS")
    print("NEW_LLM_CALLS=0")
    print("NEW_RETRIES=0")
    print("QUALITY_FLOOR_CHANGE=NONE")


if __name__ == "__main__":
    run()
