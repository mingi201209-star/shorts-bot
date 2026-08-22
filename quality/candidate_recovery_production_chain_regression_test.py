from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]

# This is the exact production prefix that mutates main.py before candidate
# grounded recovery runs. Keep this list in the same order as main.yml.
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

        patched = (work / "main.py").read_text(encoding="utf-8")
        required = (
            "# CANDIDATE_GROUNDED_RECOVERY_V1",
            "CANDIDATE_RECOVERY_POOL",
            "CANDIDATE GROUNDED RECOVERY",
            "and not recovered_from_pool",
        )
        for marker in required:
            if marker not in patched:
                raise AssertionError(f"missing production-chain marker: {marker}")

        # Idempotency is part of the production contract.
        run(TARGET, work)

    print("PASS: candidate recovery survives production hotfix prefix")


if __name__ == "__main__":
    main()
