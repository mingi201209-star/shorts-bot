from pathlib import Path


path = Path("main.py")
text = path.read_text(encoding="utf-8")

IMPORT_MARKER = '''from content.candidate_gate import (
    evaluate_candidate,
)
'''
IMPORT_REPLACEMENT = '''from content.candidate_gate import (
    evaluate_candidate,
)

from content.candidate_recovery import (
    make_recovery_record,
    select_best_recovery,
)
'''

INIT_MARKER = '''        rejected_topics = []

        total_topic_attempts = (
'''
INIT_REPLACEMENT = '''        rejected_topics = []

        # CANDIDATE_GROUNDED_RECOVERY_V1
        # Only Explorer-selected Winners rejected by the editorial Candidate
        # Gate can enter this pool. Explorer hard-gate failures never do.
        recovery_candidates = []

        total_topic_attempts = (
'''

EXPLORER_STATUS_MARKER = '''            explorer_status = (
                explorer_result.get(
                    "status"
                )
            )
'''
EXPLORER_STATUS_REPLACEMENT = '''            explorer_status = (
                explorer_result.get(
                    "status"
                )
            )

            recovered_from_pool = False
'''

EXPLORER_FINAL_RAISE = '''                raise RuntimeError(
                    "Candidate Explorer가 "
                    "제작 가능한 Winner를 "
                    "확보하지 못했습니다. "
                    f"마지막 이유: {reason}"
                )
'''
EXPLORER_FINAL_RECOVERY = '''                recovered = select_best_recovery(recovery_candidates)
                if recovered is None:
                    raise RuntimeError(
                        "Candidate Explorer가 "
                        "제작 가능한 Winner를 "
                        "확보하지 못했습니다. "
                        f"마지막 이유: {reason}"
                    )

                winner = recovered["candidate"]
                runner_up = None
                current_topic = str(winner.get("topic", "")).strip()
                recovered_from_pool = True
                print("")
                print("=" * 64)
                print("🛟 CANDIDATE GROUNDED RECOVERY")
                print("=" * 64)
                print("복구 소재:", current_topic)
                print("원래 Gate 이유:", recovered.get("gate_reason", ""))
                print("복구 근거:", recovered.get("eligibility_reason", ""))
                print("복구 attempt:", recovered.get("attempt"))
                print("➡️ bounded recovery 후보 확보; 정상 winner 경로로 재진입")

                explorer_result = {
                    "status": "SELECTED",
                    "winner": winner,
                    "runner_up": None,
                }
'''

REJECTED_TOPIC_MARKER = '''            if (
                current_topic
                in rejected_topics
            ):
'''
REJECTED_TOPIC_REPLACEMENT = '''            if (
                current_topic
                in rejected_topics
                and not recovered_from_pool
            ):
'''

GATE_RECORD_MARKER = '''                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")

                    print(
                        "➡️ Candidate Explorer 재탐색"
                    )

                    continue

                raise RuntimeError(
                    "Candidate Gate를 통과하는 "
                    "Winner를 확보하지 못했습니다. "
                    "마지막 이유: "
                    f"{winner_gate.get('reason', '')}"
                )
'''
GATE_RECORD_REPLACEMENT = '''                print_budget_status()

                recovery_record = make_recovery_record(
                    winner,
                    winner_gate,
                    attempt=topic_attempt,
                )

                if recovery_record is not None:
                    recovery_candidates.append(recovery_record)
                    print(
                        "🧺 CANDIDATE_RECOVERY_POOL "
                        f"eligible=true attempt={topic_attempt} "
                        f"strength={recovery_record.get('strength')} "
                        f"reason={recovery_record.get('eligibility_reason')}"
                    )
                else:
                    print(
                        "🧺 CANDIDATE_RECOVERY_POOL "
                        f"eligible=false attempt={topic_attempt}"
                    )

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")

                    print(
                        "➡️ Candidate Explorer 재탐색"
                    )

                    continue

                recovered = select_best_recovery(recovery_candidates)

                if recovered is not None:
                    winner = recovered["candidate"]
                    current_topic = str(winner.get("topic", "")).strip()
                    print("")
                    print("=" * 64)
                    print("🛟 CANDIDATE GROUNDED RECOVERY")
                    print("=" * 64)
                    print("복구 소재:", current_topic)
                    print("원래 Gate 이유:", recovered.get("gate_reason", ""))
                    print("복구 근거:", recovered.get("eligibility_reason", ""))
                    print("복구 attempt:", recovered.get("attempt"))
                    print("➡️ bounded recovery로 Script Generator 진행")
                else:
                    raise RuntimeError(
                        "Candidate Gate를 통과하는 "
                        "Winner를 확보하지 못했습니다. "
                        "마지막 이유: "
                        f"{winner_gate.get('reason', '')}"
                    )
'''

if "# CANDIDATE_GROUNDED_RECOVERY_V1" in text:
    print("ℹ️ Candidate grounded recovery hotfix already applied")
else:
    replacements = (
        (IMPORT_MARKER, IMPORT_REPLACEMENT, "import"),
        (INIT_MARKER, INIT_REPLACEMENT, "init"),
        (EXPLORER_STATUS_MARKER, EXPLORER_STATUS_REPLACEMENT, "explorer_status"),
        (EXPLORER_FINAL_RAISE, EXPLORER_FINAL_RECOVERY, "explorer_exhaustion"),
        (REJECTED_TOPIC_MARKER, REJECTED_TOPIC_REPLACEMENT, "rejected_topic_guard"),
        (GATE_RECORD_MARKER, GATE_RECORD_REPLACEMENT, "gate_recovery"),
    )

    for marker, replacement, name in replacements:
        if text.count(marker) != 1:
            raise RuntimeError(
                f"Candidate recovery {name} marker mismatch: {text.count(marker)}"
            )
        text = text.replace(marker, replacement, 1)

    path.write_text(text, encoding="utf-8")
    print("✅ Bounded grounded Candidate recovery hotfix applied")
