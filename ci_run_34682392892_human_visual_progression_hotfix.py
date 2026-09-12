from pathlib import Path


VALIDATION_PATH = Path("content/script_engine_v2_validation.py")
STILL_FALLBACK_PATH = Path("video/still_image_fallback.py")
VISUAL_EXPLANATION_PATH = Path("video/visual_explanation.py")

OPENING_MARKER = "# RUN_34682392892_NEGATED_REASON_TEASER_GUARD_V1"
PAYOFF_MARKER = "# RUN_34682392892_WINDOW_PAYOFF_STATE_SKIP_V1"
WORDING_MARKER = "# RUN_34682392892_WINDOW_MECHANISM_WORDING_V1"
PAYOFF_CLAIM_ID = "squarish_window_fatigue_rupture"


_OPENING_APPEND = r'''

# RUN_34682392892_NEGATED_REASON_TEASER_GUARD_V1
# Production Run 34682392892 passed the older opening-human contract with:
#   Scene 1: "... 이유는 단순한 미적 요소가 아닙니다."
#   Scene 2: "... 이유는 무엇일까요?"
# The negation is a claim marker, so the old token-overlap branch treated it as
# progression even though Scene 1 still withheld the actual causal clue. Add a
# narrow, generic Korean "reason is not X" teaser guard on top of the existing
# contract. Any real causal-content token still wins, so grounded contrast/
# pressure/stress/force/mechanism openings are untouched.
_RUN526_OPENING_REASON_BEFORE_NEGATED_TEASER = opening_human_contract_violation_reason
_RUN526_NEGATION_MARKERS = (
    "아닙니다", "아니다", "아니라", "아니고", "않습니다", "않는다",
)


def _run526_negated_reason_teaser(scene1_text, scene2_text):
    scene1 = str(scene1_text or "").strip()
    scene2 = str(scene2_text or "").strip()
    if not scene1 or not scene2:
        return False
    if "이유" not in scene1:
        return False
    if not any(marker in scene1 for marker in _RUN526_NEGATION_MARKERS):
        return False
    if any(token in scene1 for token in _OPENING_CAUSAL_CONTENT_TOKENS):
        return False
    if not _opening_scene2_asks_why_same_subject(scene1, scene2):
        return False
    return True


def opening_human_contract_violation_reason(scene1_text, scene2_text):
    prior = _RUN526_OPENING_REASON_BEFORE_NEGATED_TEASER(
        scene1_text,
        scene2_text,
    )
    if prior:
        return prior
    if _run526_negated_reason_teaser(scene1_text, scene2_text):
        return (
            "opening only negates a superficial explanation without adding a "
            "grounded causal clue before scene 2 asks the reason"
        )
    return ""
'''


_PAYOFF_APPEND = r'''

# RUN_34682392892_WINDOW_PAYOFF_STATE_SKIP_V1
# Run 34682392892 reused a subject-visible aircraft-window still for the
# grounded fatigue/rupture payoff even though the existing Vision reason
# explicitly said no fatigue/rupture action was observable. Subject identity is
# insufficient for this closed causal payoff. Skip raw still generation/reuse
# only when the existing trusted-grounding eligibility adapter proves the exact
# payoff claim; the normal deterministic AIRCRAFT_WINDOW_STRESS_V1 fallback can
# then render its already-bounded LEFT_FATIGUE_PAYOFF state. No new image,
# Vision, API, retry, or budget allowance is introduced.
from video.aircraft_window_stress_grounding import (
    supports_aircraft_window_stress_from_grounding as _run526_window_stress_eligibility,
)

_RUN526_STILL_FALLBACK_BEFORE_PAYOFF_STATE_SKIP = generate_still_motion_fallback


def _run526_requires_window_payoff_state(scene):
    eligibility = _run526_window_stress_eligibility(scene)
    return bool(
        isinstance(eligibility, dict)
        and eligibility.get("owned_claim_id") == "squarish_window_fatigue_rupture"
    )


def generate_still_motion_fallback(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    if _run526_requires_window_payoff_state(scene):
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} "
            "status=payoff_state_requires_explanation "
            f"trigger={trigger_reason} claim=squarish_window_fatigue_rupture"
        )
        return None
    return _RUN526_STILL_FALLBACK_BEFORE_PAYOFF_STATE_SKIP(
        scene,
        output_path=output_path,
        duration=duration,
        trigger_reason=trigger_reason,
    )
'''


MECHANISM_OLD = (
    '        draw.text((92, 132), "둥근 모서리는 응력을 흘려보냅니다", '
    'font=title_font, fill=(255, 255, 255, 250))\n'
)
MECHANISM_NEW = (
    '        # RUN_34682392892_WINDOW_MECHANISM_WORDING_V1\n'
    '        draw.text((92, 132), "둥근 모서리는 응력 집중을 줄입니다", '
    'font=title_font, fill=(255, 255, 255, 250))\n'
)


def apply_opening_guard(text: str) -> str:
    if OPENING_MARKER in text:
        return text
    prerequisites = (
        "# RUN_34663907508_OPENING_HUMAN_CONTRACT_V1",
        "def opening_human_contract_violation_reason(",
        "_OPENING_CAUSAL_CONTENT_TOKENS",
        "def _opening_scene2_asks_why_same_subject(",
    )
    if not all(item in text for item in prerequisites):
        raise RuntimeError(
            "Run 34682392892 opening guard requires final opening-human contract"
        )
    return text.rstrip() + "\n" + _OPENING_APPEND.strip() + "\n"


def apply_payoff_state_skip(text: str) -> str:
    if PAYOFF_MARKER in text:
        return text
    prerequisites = (
        "def generate_still_motion_fallback(",
        "def _scene_id(scene):",
        "# WINDOW_COMPARISON_INTENT_SKIP_V1",
    )
    if not all(item in text for item in prerequisites):
        raise RuntimeError(
            "Run 34682392892 payoff-state skip requires final still fallback composition"
        )
    return text.rstrip() + "\n" + _PAYOFF_APPEND.strip() + "\n"


def apply_mechanism_wording(text: str) -> str:
    if WORDING_MARKER in text:
        return text
    count = text.count(MECHANISM_OLD)
    if count != 1:
        raise RuntimeError(
            "Run 34682392892 mechanism wording anchor mismatch: "
            f"{count}"
        )
    return text.replace(MECHANISM_OLD, MECHANISM_NEW, 1)


def main() -> None:
    validation = VALIDATION_PATH.read_text(encoding="utf-8")
    patched_validation = apply_opening_guard(validation)
    if patched_validation != validation:
        VALIDATION_PATH.write_text(patched_validation, encoding="utf-8")
        print(
            "✅ Run 34682392892 opening negated-reason teaser guard installed"
        )
    else:
        print("ℹ️ Run 34682392892 opening guard already installed")

    still_fallback = STILL_FALLBACK_PATH.read_text(encoding="utf-8")
    patched_still = apply_payoff_state_skip(still_fallback)
    if patched_still != still_fallback:
        STILL_FALLBACK_PATH.write_text(patched_still, encoding="utf-8")
        print(
            "✅ Run 34682392892 grounded window payoff raw-still skip installed"
        )
    else:
        print("ℹ️ Run 34682392892 payoff-state skip already installed")

    explanation = VISUAL_EXPLANATION_PATH.read_text(encoding="utf-8")
    patched_explanation = apply_mechanism_wording(explanation)
    if patched_explanation != explanation:
        VISUAL_EXPLANATION_PATH.write_text(
            patched_explanation,
            encoding="utf-8",
        )
        print(
            "✅ Run 34682392892 window mechanism wording corrected without changing facts"
        )
    else:
        print("ℹ️ Run 34682392892 mechanism wording already installed")


if __name__ == "__main__":
    main()
