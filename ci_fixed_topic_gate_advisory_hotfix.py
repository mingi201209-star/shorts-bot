from pathlib import Path


MAIN_PATH = Path("main.py")
MARKER = "[FIXED_TOPIC_GATE_ADVISORY]"


def apply_fixed_topic_gate_advisory(text):
    if MARKER in text:
        return text

    old = '''                if (\n                    topic_attempt\n                    < total_topic_attempts\n                ):\n\n                    print(\"\")\n\n                    print(\n                        \"➡️ Candidate Explorer 재탐색\"\n                    )\n\n                    continue\n\n                raise RuntimeError(\n                    \"Candidate Gate를 통과하는 \"\n                    \"Winner를 확보하지 못했습니다. \"\n                    \"마지막 이유: \"\n                    f\"{winner_gate.get('reason', '')}\"\n                )\n'''

    new = '''                if forced_topic:\n\n                    if topic_attempt == 1:\n\n                        print(\"\")\n                        print(\n                            \"➡️ 지정 주제 Gate 피드백으로 1회 재탐색\"\n                        )\n\n                        continue\n\n                    print(\"\")\n                    print(\n                        \"⚠️ [FIXED_TOPIC_GATE_ADVISORY] \"\n                        \"편집성 Candidate Gate 거절은 1회 피드백 후 \"\n                        \"advisory로 전환; FACT 및 downstream 품질 Gate는 유지\"\n                    )\n\n                else:\n\n                    if (\n                        topic_attempt\n                        < total_topic_attempts\n                    ):\n\n                        print(\"\")\n\n                        print(\n                            \"➡️ Candidate Explorer 재탐색\"\n                        )\n\n                        continue\n\n                    raise RuntimeError(\n                        \"Candidate Gate를 통과하는 \"\n                        \"Winner를 확보하지 못했습니다. \"\n                        \"마지막 이유: \"\n                        f\"{winner_gate.get('reason', '')}\"\n                    )\n'''

    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"fixed-topic Candidate Gate tail marker count mismatch: {count}"
        )

    return text.replace(old, new, 1)


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    patched = apply_fixed_topic_gate_advisory(text)
    MAIN_PATH.write_text(patched, encoding="utf-8")
    print("✅ Fixed-topic Candidate Gate bounded advisory hotfix applied")


if __name__ == "__main__":
    main()
