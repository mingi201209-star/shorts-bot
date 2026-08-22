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

EXPLORER_EXHAUSTED_MARKER = '''                raise RuntimeError(
                    "Candidate Explorer가 "
                    "제작 가능한 Winner를 "
                    "확보하지 못했습니다. "
                    f"마지막 이유: {reason}"
                )

            # =================================================
            # Winner / Runner-up
'''
EXPLORER_EXHAUSTED_REPLACEMENT = '''                recovered = select_best_recovery(recovery_candidates)

                if recovered is not None:
                    winner = recovered["candidate"]
                    runner_up = None
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
                    explorer_status = "RECOVERED"
                else:
                    raise RuntimeError(
                        "Candidate Explorer가 "
                        "제작 가능한 Winner를 "
                        "확보하지 못했습니다. "
                        f"마지막 이유: {reason}"
                    )

            if explorer_status == "RECOVERED":
                pass
            else:
                # =================================================
                # Winner / Runner-up
'''

# The winner extraction block must be indented under the recovery branch's
# `else:` until the Gate section. Rather than broadly rewriting main.py, apply
# a bounded indentation transform between stable markers.
WINNER_BLOCK_START = '''            # =================================================
            # Winner / Runner-up
            # =================================================
'''
GATE_BLOCK_START = '''            # =================================================
            # Winner Candidate Gate
            # =================================================
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
    for marker, replacement, name in (
        (IMPORT_MARKER, IMPORT_REPLACEMENT, "import"),
        (INIT_MARKER, INIT_REPLACEMENT, "init"),
    ):
        if text.count(marker) != 1:
            raise RuntimeError(f"Candidate recovery {name} marker mismatch: {text.count(marker)}")
        text = text.replace(marker, replacement, 1)

    # Handle Explorer exhaustion by recovering a previously gate-rejected
    # selected Winner. Keep the normal winner path unchanged otherwise.
    if text.count(EXPLORER_EXHAUSTED_MARKER) != 1:
        raise RuntimeError(
            "Candidate recovery explorer exhaustion marker mismatch: "
            f"{text.count(EXPLORER_EXHAUSTED_MARKER)}"
        )

    # Simpler fail-closed insertion: replace only the final raise with a
    # recovery branch and jump directly into the existing winner variables.
    explorer_old = '''                raise RuntimeError(
                    "Candidate Explorer가 "
                    "제작 가능한 Winner를 "
                    "확보하지 못했습니다. "
                    f"마지막 이유: {reason}"
                )
'''
    explorer_new = '''                recovered = select_best_recovery(recovery_candidates)
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
    if text.count(explorer_old) != 1:
        raise RuntimeError(
            "Candidate recovery explorer final raise mismatch: "
            f"{text.count(explorer_old)}"
        )
    text = text.replace(explorer_old, explorer_new, 1)

    if text.count(GATE_RECORD_MARKER) != 1:
        raise RuntimeError(
            "Candidate recovery gate marker mismatch: "
            f"{text.count(GATE_RECORD_MARKER)}"
        )
    text = text.replace(GATE_RECORD_MARKER, GATE_RECORD_REPLACEMENT, 1)

    path.write_text(text, encoding="utf-8")
    print("✅ Bounded grounded Candidate recovery hotfix applied")
