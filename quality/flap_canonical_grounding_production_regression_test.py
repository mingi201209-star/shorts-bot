"""Run 33974152422 flap canonical-grounding production regression.

The production counterexample reached the fixed-topic advisory path, then the
pre-Writer Canonical Subject Grounding Gate blocked because the selected flap
candidate remained UNKNOWN. This regression executes the real production
Candidate installer ordering, then validates the fixed flap payload in a fresh
Python process so module caching cannot hide the production trusted-record set.
"""

from pathlib import Path
import subprocess
import sys
import textwrap


FIXED_FLAP_TOPIC = "비행기 날개 뒤쪽 플랩은 왜 이착륙 때 펼쳐질까"
EXPECTED_CANONICAL = "aircraft trailing-edge flap"


def _apply_production_candidate_wiring():
    scripts = (
        "ci_topic_input_hotfix.py",
        "ci_aviation_candidate_context_hotfix.py",
        "ci_aviation_candidate_specificity_hotfix.py",
        "ci_aviation_context_signature_compat_hotfix.py",
        "ci_aviation_specificity_output_repair_hotfix.py",
        "ci_aviation_specificity_projection_hotfix.py",
        "ci_candidate_grounded_recovery_hotfix.py",
    )
    for script in scripts:
        subprocess.run([sys.executable, script], check=True)


def run():
    _apply_production_candidate_wiring()

    supply_source = Path("quality/canonical_subject_grounding_supply.py").read_text(
        encoding="utf-8"
    )
    assert supply_source.count("# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1") == 1

    # Re-run the leaf installer to prove the production extension is idempotent.
    subprocess.run([sys.executable, "ci_flap_canonical_grounding_hotfix.py"], check=True)
    supply_source = Path("quality/canonical_subject_grounding_supply.py").read_text(
        encoding="utf-8"
    )
    assert supply_source.count("# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1") == 1
    print("CASE A flap trusted-record installer is idempotent: PASS")

    fresh_process = textwrap.dedent(
        f'''\
        import content.candidate_explorer as explorer_package
        from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding
        from quality.canonical_subject_grounding_supply import (
            PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
            supply_trusted_subject_grounding,
        )

        validate_explorer_output = explorer_package._LEGACY.validate_explorer_output
        topic = {FIXED_FLAP_TOPIC!r}
        parsed = {{
            "status": "SELECTED",
            "winner": {{
                "topic": topic,
                "angle": "날개 뒤쪽 플랩이 이착륙 때 펼쳐지는 이유와 작동 원리를 설명",
                "core_question": "왜 비행기 날개 뒤쪽 플랩이 이착륙할 때 펼쳐질까?",
                "specific_observation": "비행기 날개 뒤쪽 플랩이 이착륙 때 아래로 펼쳐집니다.",
                "micro_narrative": {{
                    "hook": "비행기 날개 뒤쪽 플랩은 이착륙 때 펼쳐집니다.",
                    "core_question": "왜 이때만 날개 뒤쪽 플랩을 펼칠까요?",
                    "reveal": "플랩을 내리면 날개 형상이 바뀌어 저속에서 필요한 양력을 늘립니다.",
                    "payoff": "그래서 이착륙처럼 낮은 속도에서 플랩을 전개합니다.",
                }},
                "fact_check_focus": [
                    "플랩의 날개 뒤쪽 위치와 고양력 장치 역할",
                    "플랩 전개가 캠버와 양력 및 항력에 미치는 영향",
                ],
                "visual_proof": [
                    "항공기 날개 뒤쪽 플랩이 전개된 모습",
                ],
                "selection_reason": "실제 눈에 보이는 플랩 전개를 물리적 날개 구조와 연결할 수 있음",
            }},
            "runner_up": None,
        }}

        result = validate_explorer_output(parsed)
        winner = result["winner"]
        assert winner["canonical_subject"] == {EXPECTED_CANONICAL!r}, winner
        assert winner["subject_kind"] == "physical_entity", winner
        assert winner["subject_identity_confidence"] >= 0.80, winner
        assert winner.get("_trusted_grounding_evidence"), winner
        gate = evaluate_candidate_subject_grounding(winner)
        assert gate["status"] == "PASS", gate
        print("CASE B exact production flap topic reaches pre-Writer grounding as physical_entity: PASS")

        unrelated = {{
            "topic": "비행기 착륙 장치 바퀴는 왜 착륙 전에 미리 돌지 않을까",
            "angle": "landing gear wheel behavior",
            "core_question": "왜 착륙 전에 바퀴를 미리 돌리지 않을까?",
            "micro_narrative": {{
                "hook": "착륙 장치 바퀴는 접근 중 멈춰 있습니다.",
                "reveal": "착륙 순간 활주로와 접촉하며 회전합니다.",
                "payoff": "플랩과는 다른 물리 장치입니다.",
            }},
        }}
        unrelated = supply_trusted_subject_grounding(
            unrelated,
            trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
        assert unrelated.get("canonical_subject", "UNKNOWN") != {EXPECTED_CANONICAL!r}, unrelated
        print("CASE C unrelated aviation subject cannot inherit flap identity: PASS")
        '''
    )
    subprocess.run([sys.executable, "-c", fresh_process], check=True)

    print("FLAP CANONICAL GROUNDING PRODUCTION REGRESSION: PASS")


if __name__ == "__main__":
    run()
