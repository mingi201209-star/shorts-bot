from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "RUN_34825745612_LEGACY_SELECTED_HOOK_REPAIR_V1"


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Run 34825745612 legacy SELECTED hook repair already applied")
        return

    text += r'''

# RUN_34825745612_LEGACY_SELECTED_HOOK_REPAIR_V1
# Production Run 34825745612 showed that aviation retries can return legacy
# SELECTED after an earlier CANDIDATE_POOL attempt. The pool path already has a
# bounded repeated-Hook repair, but legacy SELECTED reached the semantic
# validator first and failed repeatedly. Repair only that exact validation
# failure, only for an exact repo-owned fixed topic, from the repo-owned seed's
# already supplied specific_observation. No threshold, retry, budget, or gate is
# changed.
from copy import deepcopy as _run34825745612_deepcopy
from quality.fixed_topic_seed_grounding import (
    exact_fixed_topic_seed_record as _run34825745612_exact_seed_record,
)
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS as _run34825745612_prod_records,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS as _run34825745612_pool_records,
)

_run34825745612_previous_validate_explorer_output = validate_explorer_output
_run34825745612_repeat_markers = ("micro_narrative hook", "Core Question")


def _run34825745612_declarative(value):
    text = str(value or "").strip()
    if not text or text.endswith("?"):
        return False
    lowered = text.lower()
    return not lowered.startswith((
        "왜 ", "왜?", "어떻게 ", "무엇", "어떤 ", "언제 ", "어디",
        "how ", "why ", "what ", "when ", "where ",
    ))


def validate_explorer_output(data):
    try:
        return _run34825745612_previous_validate_explorer_output(data)
    except (TypeError, ValueError) as original_exc:
        error_text = str(original_exc)
        if not all(marker in error_text for marker in _run34825745612_repeat_markers):
            raise
        if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
            raise
        if not isinstance(data, dict) or str(data.get("status") or "").strip().upper() != "SELECTED":
            raise

        winner = data.get("winner")
        if not isinstance(winner, dict):
            raise
        fixed_topic = os.environ.get("SHORTS_TOPIC", "")
        trusted_records = tuple(_run34825745612_prod_records) + tuple(
            _run34825745612_pool_records
        )
        record = _run34825745612_exact_seed_record(
            winner,
            fixed_topic,
            trusted_records=trusted_records,
        )
        if record is None:
            raise
        seed = record.get("seed_candidate")
        observation = seed.get("specific_observation") if isinstance(seed, dict) else None
        if not _run34825745612_declarative(observation):
            raise

        repaired = _run34825745612_deepcopy(data)
        repaired_winner = _run34825745612_deepcopy(winner)
        repaired_micro = _run34825745612_deepcopy(
            repaired_winner.get("micro_narrative") or {}
        )
        repaired_micro["hook"] = str(observation).strip()
        repaired_winner["micro_narrative"] = repaired_micro
        repaired["winner"] = repaired_winner

        validated = _run34825745612_previous_validate_explorer_output(repaired)
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
