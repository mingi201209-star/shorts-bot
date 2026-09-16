from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]

# Relevant production composition from main.yml:
# prefix -> grounded recovery -> growth shadow (which imports Run 35065228877)
# -> final aviation/context compatibility re-apply before generator runtime.
PRODUCTION_PREFIX = (
    "ci_hotfix.py",
    "ci_novelty_budget_hotfix.py",
    "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py",
    "ci_first5_retention_tts_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_aviation_candidate_specificity_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
    "ci_aviation_specificity_output_repair_hotfix.py",
    "ci_aviation_specificity_projection_hotfix.py",
)
TARGET = "ci_candidate_grounded_recovery_hotfix.py"
GROWTH_LINK = "ci_growth_candidate_shadow_hotfix.py"
FINAL_CONTEXT_COMPAT = "ci_aviation_context_signature_compat_hotfix.py"
RUN_350652_REGRESSION = "quality/run_35065228877_bounded_supply_authority_regression_test.py"


def run(script, cwd):
    result = subprocess.run(
        [sys.executable, script],
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{script} failed in production-chain regression\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        work = Path(temp_dir)
        for path in ROOT.iterdir():
            if path.name == ".git":
                continue
            target = work / path.name
            if path.is_dir():
                import shutil
                shutil.copytree(path, target)
            else:
                target.write_bytes(path.read_bytes())

        for script in PRODUCTION_PREFIX:
            run(script, work)
        run(TARGET, work)
        run(GROWTH_LINK, work)

        # Production intentionally re-applies this compatibility installer after
        # later composition. Reproduce that final authority before runtime proof.
        run(FINAL_CONTEXT_COMPAT, work)

        patched_main = (work / "main.py").read_text(encoding="utf-8")
        required_main = (
            "# CANDIDATE_GROUNDED_RECOVERY_V1",
            "CANDIDATE_RECOVERY_POOL",
            "CANDIDATE GROUNDED RECOVERY",
            "and not recovered_from_pool",
            "GROWTH_CANDIDATE_SHADOW_V1",
        )
        for marker in required_main:
            if marker not in patched_main:
                raise AssertionError(f"missing production-chain marker: {marker}")

        patched_explorer = (work / "content/candidate_explorer.py").read_text(
            encoding="utf-8"
        )
        required_explorer = (
            "RUN_35065228877_BOUNDED_SUPPLY_AUTHORITY_V1",
            "DEFAULT AUTOMATIC SUPPLY RECOVERY AUTHORITY — RUN 35065228877",
            "fixed_topic_gate_feedback",
        )
        for marker in required_explorer:
            if marker not in patched_explorer:
                raise AssertionError(
                    f"missing final candidate-explorer composition marker: {marker}"
                )

        # Execute the exact counterexample against the final composed runtime,
        # not only against an isolated wrapper.
        run(RUN_350652_REGRESSION, work)

        # Idempotency is part of the production contract.
        run(TARGET, work)
        run(GROWTH_LINK, work)
        run(FINAL_CONTEXT_COMPAT, work)

    print("PASS: candidate recovery + Run 35065228877 survive production composition")


if __name__ == "__main__":
    main()
