import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.first5_visual_contract import (
    progression_passes,
    validate_reversal_context,
    validate_reversal_query,
    visual_signature,
)


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"✅ PASS | {message}")


def test_reversal_concept_lock():
    missing_a = {
        "text": "평범한 건물처럼 보이지만 실제로는 통신 시설이에요.",
        "visual_goal": "평범한 건물처럼 위장된 실제 통신 인프라",
        "keyword": "telecom tower base station antenna",
    }
    valid, reason = validate_reversal_query(missing_a)
    _assert(not valid and reason == "reversal_appearance_side_missing", "A-side loss is rejected")

    preserved = {
        **missing_a,
        "keyword": "ordinary facade disguised telecom infrastructure",
    }
    valid, reason = validate_reversal_query(preserved)
    _assert(valid and reason == "reversal_concept_preserved", "A+B reversal concept is preserved")

    candidate_context = {
        "micro_narrative": {
            "hook": "평범한 건물처럼 보이지만 실제로는 기반 시설이에요.",
            "reveal": "겉모습과 실제 기능이 다릅니다.",
        }
    }
    valid, reason = validate_reversal_context(
        candidate_context,
        "telecom tower antenna",
    )
    _assert(not valid and reason == "reversal_appearance_side_missing", "Hook pool keeps original candidate reversal lock")

    valid, reason = validate_reversal_context(
        candidate_context,
        "ordinary facade telecom infrastructure",
    )
    _assert(valid, "Hook pool accepts preserved candidate reversal concept")

    normal = {
        "text": "벌집의 육각형은 재료를 효율적으로 사용해요.",
        "visual_goal": "벌집 육각형 셀 클로즈업",
        "keyword": "honeycomb hexagon cells closeup",
    }
    valid, reason = validate_reversal_query(normal)
    _assert(valid and reason == "non_reversal", "Normal non-reversal Hook remains unchanged")


def test_opening_progression():
    first = visual_signature(
        "ordinary building facade exterior",
        "ordinary-building-facade-exterior",
    )
    repeated = visual_signature(
        "normal building facade exterior",
        "ordinary-building-facade-exterior-view",
    )
    valid, reason = progression_passes(first, repeated)
    _assert(not valid, f"Different IDs with same visual concept are rejected: {reason}")

    reveal = visual_signature(
        "rooftop antenna telecom equipment",
        "telecom-antenna-equipment-rooftop",
    )
    valid, reason = progression_passes(first, reveal)
    _assert(valid and reason == "opening_progression_ok", "Exterior to infrastructure reveal progresses visually")


def main():
    test_reversal_concept_lock()
    test_opening_progression()
    print("✅ FIRST-5 VISUAL CONCEPT + PROGRESSION REGRESSION PASS")


if __name__ == "__main__":
    main()
