from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
FINAL_VISUAL_PATH = Path("video/visual_explanation.py")
MARKER = "RUN_34825745612_LEGACY_SELECTED_HOOK_REPAIR_V1"
FINAL_READY_MARKER = "GROUNDED_DETERMINISTIC_EXPLANATION_V1"


def main():
    # The aviation compatibility installer runs once early and once after the
    # final production composition. Install this wrapper only on the latter pass
    # so it remains the outermost Candidate Explorer validator wrapper.
    if not FINAL_VISUAL_PATH.exists() or FINAL_READY_MARKER not in FINAL_VISUAL_PATH.read_text(
        encoding="utf-8"
    ):
        print("⏭️ Run 34825745612 legacy hook repair deferred until final production state")
        return

    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Run 34825745612 legacy SELECTED hook repair already applied")
        return

    text += r'''

# RUN_34825745612_LEGACY_SELECTED_HOOK_REPAIR_V1
# Production Run 34825745612 showed that aviation retries can return legacy
# SELECTED after an earlier CANDIDATE_POOL attempt. The pool path already has a
# bounded repeated-Hook repair, but legacy SELECTED reached the semantic
# validator first and failed repeatedly. This outermost final-composition wrapper
# delegates the exact repair decision to a pure fail-closed helper, then reruns
# the unchanged validator. No threshold, retry, budget, or gate is changed.
from quality.legacy_selected_hook_repair import (
    validate_legacy_selected_with_exact_hook_repair as _run34825745612_validate_with_repair,
)
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS as _run34825745612_prod_records,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS as _run34825745612_pool_records,
)

_run34825745612_previous_validate_explorer_output = validate_explorer_output


def validate_explorer_output(data):
    validated, repaired = _run34825745612_validate_with_repair(
        data,
        validate_output_fn=_run34825745612_previous_validate_explorer_output,
        scope=os.environ.get("SHORTS_CANDIDATE_SCOPE", ""),
        fixed_topic=os.environ.get("SHORTS_TOPIC", ""),
        trusted_records=(
            tuple(_run34825745612_prod_records)
            + tuple(_run34825745612_pool_records)
        ),
    )
    if repaired:
        print(
            "[LEGACY_SELECTED_HOOK_NORMALIZE] "
            "status=REPAIRED_REPEATED_HOOK_FROM_EXACT_FIXED_TOPIC_SEED "
            "source_field=specific_observation"
        )
    return validated
'''

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Run 34825745612 bounded legacy SELECTED hook repair applied")


if __name__ == "__main__":
    main()
