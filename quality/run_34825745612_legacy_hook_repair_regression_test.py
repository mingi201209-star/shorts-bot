from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)
from quality.legacy_selected_hook_repair import (
    validate_legacy_selected_with_exact_hook_repair,
)


FIXED_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"
EXPECTED_OBSERVATION = "착륙 직후 날개 윗면의 판 모양 스포일러가 위로 솟습니다."
EXPLORER_PATH = REPO_ROOT / "content/candidate_explorer.py"
VISUAL_PATH = REPO_ROOT / "video/visual_explanation.py"
MARKER = "RUN_34825745612_LEGACY_SELECTED_HOOK_REPAIR_V1"
FINAL_READY_MARKER = "GROUNDED_DETERMINISTIC_EXPLANATION_V1"
TRUSTED_RECORDS = tuple(PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS) + tuple(
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
)


def candidate(topic: str = FIXED_TOPIC) -> dict:
    question = "왜 비행기는 착륙 직후 날개의 양력을 일부러 없앨까?"
    return {
        "status": "SELECTED",
        "winner": {
            "topic": topic,
            "angle": "착륙 직후 스포일러 전개",
            "core_question": question,
            "micro_narrative": {
                "hook": question,
                "core_question": question,
                "reveal": "스포일러가 양력을 줄이고 항력을 늘립니다.",
                "payoff": "바퀴 제동 효과를 높이는 데 도움이 됩니다.",
            },
            "fact_check_focus": [],
            "visual_proof": ["착륙 직후 날개 위 스포일러"],
            "selection_reason": "화면에서 직접 확인할 수 있습니다.",
            "specific_observation": "모델이 만든 관찰문",
        },
        "runner_up": None,
    }


def repeated_hook_validator(data: dict) -> dict:
    winner = data["winner"]
    micro = winner["micro_narrative"]
    if micro["hook"] == winner["core_question"]:
        raise ValueError(
            "winner.micro_narrative hook이 Core Question과 같은 내용을 반복합니다. "
            "첫 두 beat는 새 정보를 전진시켜야 합니다."
        )
    return data


def main() -> None:
    # A. Exact production counterexample repairs only the Hook and reruns the
    # unchanged validator.
    repaired, did_repair = validate_legacy_selected_with_exact_hook_repair(
        candidate(),
        validate_output_fn=repeated_hook_validator,
        scope="aviation",
        fixed_topic=FIXED_TOPIC,
        trusted_records=TRUSTED_RECORDS,
    )
    assert did_repair is True
    assert repaired["status"] == "SELECTED"
    assert repaired["winner"]["micro_narrative"]["hook"] == EXPECTED_OBSERVATION
    assert repaired["winner"]["core_question"] == candidate()["winner"]["core_question"]

    # B. Non-exact topic stays fail-closed.
    try:
        validate_legacy_selected_with_exact_hook_repair(
            candidate("착륙 직후 다른 스포일러 주제"),
            validate_output_fn=repeated_hook_validator,
            scope="aviation",
            fixed_topic=FIXED_TOPIC,
            trusted_records=TRUSTED_RECORDS,
        )
    except ValueError as exc:
        assert "Core Question" in str(exc)
    else:
        raise AssertionError("non-exact topic unexpectedly repaired")

    # C. Outside aviation scope stays fail-closed.
    try:
        validate_legacy_selected_with_exact_hook_repair(
            candidate(),
            validate_output_fn=repeated_hook_validator,
            scope="",
            fixed_topic=FIXED_TOPIC,
            trusted_records=TRUSTED_RECORDS,
        )
    except ValueError as exc:
        assert "Core Question" in str(exc)
    else:
        raise AssertionError("non-aviation scope unexpectedly repaired")

    # D. Unrelated validation failures remain authoritative.
    def unrelated_failure(_data: dict) -> dict:
        raise ValueError("unrelated schema failure")

    try:
        validate_legacy_selected_with_exact_hook_repair(
            candidate(),
            validate_output_fn=unrelated_failure,
            scope="aviation",
            fixed_topic=FIXED_TOPIC,
            trusted_records=TRUSTED_RECORDS,
        )
    except ValueError as exc:
        assert str(exc) == "unrelated schema failure"
    else:
        raise AssertionError("unrelated validation error was swallowed")

    # E. Installer wiring defers until final production composition, then appends
    # exactly one wrapper. This checks the final-pass integration without dynamic
    # module reload tricks.
    original_explorer = EXPLORER_PATH.read_text(encoding="utf-8")
    original_visual = VISUAL_PATH.read_text(encoding="utf-8")
    try:
        EXPLORER_PATH.write_text(original_explorer.replace(MARKER, ""), encoding="utf-8")
        VISUAL_PATH.write_text(
            original_visual.replace(FINAL_READY_MARKER, "RUN348_FINAL_NOT_READY"),
            encoding="utf-8",
        )
        hotfix = importlib.import_module("ci_run_34825745612_legacy_hook_repair_hotfix")
        hotfix.main()
        assert MARKER not in EXPLORER_PATH.read_text(encoding="utf-8")

        VISUAL_PATH.write_text(
            original_visual + f"\n# {FINAL_READY_MARKER}\n",
            encoding="utf-8",
        )
        hotfix.main()
        assert EXPLORER_PATH.read_text(encoding="utf-8").count(MARKER) == 1
    finally:
        EXPLORER_PATH.write_text(original_explorer, encoding="utf-8")
        VISUAL_PATH.write_text(original_visual, encoding="utf-8")

    print("PASS: Run 34825745612 bounded legacy SELECTED hook repair regression")


if __name__ == "__main__":
    main()
