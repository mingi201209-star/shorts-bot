"""Regression for Run 33954034420 pre-Writer observable opening failure.

No network/API call. Reproduce the production Script Engine V2 composition and
verify a grounded question-form opening is deterministically converted into a
Scene 1 observable statement before Writer planning, while Scene 2 remains the
question and factual content is unchanged.
"""
from __future__ import annotations

from copy import deepcopy
import importlib
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Install the same grounded Script Engine V2 layer that owns _grounded_opening,
# then install the Run 33954034420 repair at the actual production boundary.
runpy.run_path(str(ROOT / "ci_writer_compliance_plan_hotfix.py"), run_name="__main__")
runpy.run_path(str(ROOT / "ci_grounded_claim_plan_hotfix.py"), run_name="__main__")
runpy.run_path(str(ROOT / "ci_writer_observable_opening_hotfix.py"), run_name="__main__")

import content.script_engine_v2 as engine
engine = importlib.reload(engine)


def _candidate(hook: str):
    return {
        "topic": "기내 압력 조절 시스템의 창문 디자인",
        "angle": "비행기 창문의 둥근 모서리와 응력 분산",
        "core_question": "왜 비행기 창문은 둥글게 설계되었을까?",
        "micro_narrative": {
            "hook": hook,
            "core_question": "왜 비행기 창문은 둥글게 설계되었을까?",
            "reveal": "둥근 모서리는 응력이 한 지점에 집중되는 것을 줄입니다.",
            "payoff": "그래서 창문 주변의 응력 집중을 줄이는 데 도움이 됩니다.",
        },
        "fact_check_focus": ["rounded aircraft window", "stress concentration"],
        "visual_proof": ["modern passenger aircraft rounded window"],
        "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
        "subject_kind": "physical_entity",
    }


def main():
    original = _candidate("왜 비행기 창문은 둥글게 설계되었을까?")
    before = deepcopy(original)

    hook, question = engine._grounded_opening(original)
    assert original == before, "opening normalization must not mutate candidate"
    assert hook == "비행기 창문은 둥글게 설계되었습니다.", hook
    assert "?" not in hook
    assert question.startswith("그런데 "), question
    assert question.endswith("?"), question
    assert "둥글게 설계" in question

    # Existing declarative opening stays semantically and textually intact.
    declarative = _candidate("비행기 창문 모서리는 둥글게 생겼습니다.")
    good_hook, good_question = engine._grounded_opening(declarative)
    assert good_hook == "비행기 창문 모서리는 둥글게 생겼습니다."
    assert good_question.endswith("?")

    # No unrelated factual fields may be synthesized or changed.
    assert original["fact_check_focus"] == before["fact_check_focus"]
    assert original["visual_proof"] == before["visual_proof"]
    assert original["canonical_subject"] == before["canonical_subject"]

    assert engine.MAX_SCRIPT_API_CALLS == 3
    assert engine.MAX_LOCAL_REPAIR_CALLS == 2
    print("RUN 33954034420 PREWRITER OBSERVABLE OPENING REGRESSION: PASS")


if __name__ == "__main__":
    main()
