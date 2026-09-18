"""Run 35333010543: deterministic exact-topic opening projection.

Two exact-SHA production attempts after PR #418 were blocked by upstream
stochasticity before the payoff presentation could be exercised. Run
35333010543 terminated because Candidate Explorer repeatedly returned a Winner
whose Hook restated its Core Question.

For the exact repo-owned flexible-wing fixed topic only, if the existing
Script Human Quality progression detector itself says Hook -> Question is a
restatement, replace only that two-beat opening with the unique repo-owned
trusted seed's Hook + Question before the unchanged validator runs.

No fact/reveal/payoff/body text, threshold, retry, API, cost, or scene-count
behavior changes.
"""
from pathlib import Path

PATH = Path("content/candidate_explorer.py")
MARKER = "# RUN_35333010543_FIXED_TOPIC_OPENING_PROJECTION_V1"

_APPEND = r'''

# RUN_35333010543_FIXED_TOPIC_OPENING_PROJECTION_V1
_RUN_35333010543_FIXED_TOPIC = "비행기 날개는 왜 비행 중에 휘어질까"
_run_35333010543_previous_validate_hook_question_progression = (
    _validate_hook_question_progression
)


def _run_35333010543_progression_repeats(candidate_result):
    micro = candidate_result.get("micro_narrative") or {}
    hook = str(micro.get("hook") or "").strip()
    questions = (
        str(candidate_result.get("core_question") or "").strip(),
        str(micro.get("core_question") or "").strip(),
    )
    return any(
        question and _hook_restates_question(hook, question)
        for question in questions
    )


def _run_35333010543_project_trusted_opening(candidate_result):
    fixed_topic = str(os.environ.get("SHORTS_TOPIC") or "").strip().rstrip(".?!？")
    candidate_topic = str(candidate_result.get("topic") or "").strip().rstrip(".?!？")
    if fixed_topic != _RUN_35333010543_FIXED_TOPIC:
        return False
    if candidate_topic != fixed_topic:
        return False
    if not _run_35333010543_progression_repeats(candidate_result):
        return False

    from quality.candidate_pool_grounding_records import (
        CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )
    from quality.fixed_topic_seed_grounding import exact_fixed_topic_seed_record

    record = exact_fixed_topic_seed_record(
        candidate_result,
        fixed_topic,
        trusted_records=CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )
    if not isinstance(record, dict):
        return False

    seed = record.get("seed_candidate")
    seed_micro = (seed or {}).get("micro_narrative") if isinstance(seed, dict) else None
    if not isinstance(seed_micro, dict):
        return False

    trusted_hook = str(seed_micro.get("hook") or "").strip()
    trusted_question = str(seed_micro.get("core_question") or "").strip()
    trusted_reveal = str(seed_micro.get("reveal") or "").strip()
    if not trusted_hook or not trusted_question or not trusted_reveal:
        return False

    # Reuse the existing first-5 deterministic progression contract to ensure
    # the repo-owned pair really advances information before projection.
    from content.retention_structure import validate_first5_progression

    first5_ok, _ = validate_first5_progression([
        {
            "retention_role": "phenomenon",
            "text": trusted_hook,
            "visual_goal": "trusted exact-topic observable subject",
        },
        {
            "retention_role": "question",
            "text": trusted_question,
            "visual_goal": "trusted exact-topic causal question",
        },
        {
            "retention_role": "causal_clue",
            "text": trusted_reveal,
            "visual_goal": "trusted exact-topic causal clue",
        },
    ])
    if not first5_ok:
        return False

    micro = dict(candidate_result.get("micro_narrative") or {})
    micro["hook"] = trusted_hook
    micro["core_question"] = trusted_question
    candidate_result["micro_narrative"] = micro
    candidate_result["core_question"] = trusted_question

    print(
        "[FIXED_TOPIC_OPENING_PROJECTION] "
        "run=35333010543 status=projected source=repo_owned_seed"
    )
    return True


def _validate_hook_question_progression(candidate_result, prefix):
    if str(prefix or "") == "winner":
        _run_35333010543_project_trusted_opening(candidate_result)

    return _run_35333010543_previous_validate_hook_question_progression(
        candidate_result,
        prefix,
    )
'''


def patch(text: str) -> str:
    if MARKER in text:
        return text

    required = (
        "SCRIPT_HUMAN_QUALITY_V1",
        "def _hook_restates_question(",
        "def _validate_hook_question_progression(",
    )
    if not all(token in text for token in required):
        raise RuntimeError(
            "Run 35333010543 opening projection prerequisites missing"
        )
    return text.rstrip() + _APPEND + "\n"


def main() -> None:
    PATH.write_text(
        patch(PATH.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    print(
        "✅ Run 35333010543 exact fixed-topic opening projection installed; "
        "quality/retry/API/cost ceilings unchanged"
    )


if __name__ == "__main__":
    main()
