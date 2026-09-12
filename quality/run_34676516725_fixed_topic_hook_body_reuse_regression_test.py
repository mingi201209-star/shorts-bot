from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_34676516725_fixed_topic_hook_body_reuse_hotfix import (
    MARKER,
    apply_fixed_topic_hook_body_reuse,
)


FIXTURE = '''def main():
    try:
        forced_topic = "fixed"
        fixed_topic_gate_feedback = ""

        final_script = None

        for topic_attempt in range(1, total_topic_attempts + 1):
            winner = {}
            # RUN_34671707523_OPENING_CANDIDATE_RECOVERY_V1
            # =================================================
            # Winner Script
            # =================================================
            script_data = (
                generate_script(
                    topic_info,
                    winner,
                )
            )

            if not isinstance(script_data, dict):
                raise RuntimeError("bad")

            # =================================================
            # Quality
            # =================================================

            quality_result = (
                run_quality_process(
                    script_data
                )
            )

            status = quality_result.get("status")
            if status == "REGENERATE_TOPIC":
                # RUN_34672661458_HOOK_FLOOR_FEEDBACK_V1
                if forced_topic:
                    hook_floor_reason = str(
                        quality_result.get(
                            "reason",
                            "",
                        )
                    ).strip()
                    if hook_floor_reason.startswith(
                        "Fixed-topic Hook가 bounded rewrite 후에도 "
                        "기존 품질 floor 미달"
                    ):
                        fixed_topic_gate_feedback = (
                            hook_floor_reason
                        )
    except Exception:
        raise
'''


def main():
    patched = apply_fixed_topic_hook_body_reuse(FIXTURE)

    assert MARKER in patched
    assert patched == apply_fixed_topic_hook_body_reuse(patched)

    assert "fixed_topic_hook_recovery_script = None" in patched
    assert "fixed_topic_last_writer_script = None" in patched
    assert patched.count("generate_script(") == 1
    assert "and fixed_topic_hook_recovery_script is not None" in patched
    assert "else:\n                script_data = (\n                    generate_script(" in patched

    assert "build_narrative_plan(winner)" in patched
    assert "recovery_scenes[0][\"text\"] = recovery_hook" in patched
    assert "preserved_question = str(" in patched
    assert "opening_human_contract_violation_reason(" in patched
    assert "Scene 2+ body; full Writer call skipped" in patched

    assignments = [
        line.strip()
        for line in patched.splitlines()
        if "recovery_scenes[" in line and "] =" in line
    ]
    assert assignments == ['recovery_scenes[0]["text"] = recovery_hook']

    cache_pos = patched.index("fixed_topic_last_writer_script = _hook_recovery_deepcopy(")
    quality_pos = patched.index("quality_result = (\n                run_quality_process(")
    assert cache_pos < quality_pos

    hook_gate_pos = patched.index("if hook_floor_reason.startswith(")
    promote_pos = patched.index("fixed_topic_hook_recovery_script = (")
    assert hook_gate_pos < promote_pos

    forbidden_assignments = (
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "MAX_REWRITES =",
        "MAX_TOPIC_REGENERATIONS =",
        "HOOK_MIN_SCORE =",
        "GOOD_ENOUGH_FLOORS =",
    )
    for token in forbidden_assignments:
        assert token not in patched

    assert "openai." not in patched
    assert "authorize_call(" not in patched
    assert "call_llm(" not in patched

    compile(patched, "synthetic-main.py", "exec")

    print("RUN 34676516725 FIXED-TOPIC HOOK BODY REUSE REGRESSION: PASS")


if __name__ == "__main__":
    main()
