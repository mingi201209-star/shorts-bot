from pathlib import Path


MAIN_PATH = Path("main.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"fixed-topic novelty-lock {label} marker mismatch: {count}")
    return text.replace(marker, replacement, 1)


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")

    marker = '''            # =================================================\n            # Runner-up Failed\n            # =================================================\n\n            if (\n                quality_result.get(\n                    "fallback_used",\n                    False,\n                )\n            ):\n'''

    replacement = '''            # =================================================\n            # Fixed-topic Novelty Lock\n            # =================================================\n            # A user-pinned production topic cannot be replaced by Candidate\n            # regeneration. If the quality process reached REGENERATE_TOPIC only\n            # because the editorial Novelty score stayed below its global floor,\n            # keep the already-validated script and continue production instead of\n            # re-exploring the exact same topic until the API budget is exhausted.\n            # This does NOT alter the global novelty threshold and does NOT bypass\n            # FACT_CRITICAL or other HOLD/fail-close paths.\n\n            if (\n                forced_topic\n                and status == "REGENERATE_TOPIC"\n                and "Novelty" in str(\n                    quality_result.get("reason", "")\n                )\n                and quality_result.get("failure_type")\n                not in {"FACT_CRITICAL"}\n            ):\n                candidate_script = quality_result.get("script_data")\n                if not isinstance(candidate_script, dict):\n                    raise RuntimeError(\n                        "지정 주제 Novelty lock에 사용할 검증 대본이 없습니다."\n                    )\n                candidate_topic = str(\n                    candidate_script.get("topic", current_topic)\n                ).strip()\n                if candidate_topic != forced_topic:\n                    raise RuntimeError(\n                        "지정 주제 Novelty lock의 대본 topic이 production 주제와 다릅니다."\n                    )\n\n                print("")\n                print("=" * 64)\n                print("🔒 FIXED TOPIC NOVELTY LOCK")\n                print("=" * 64)\n                print(\n                    "지정 주제는 교체하지 않고 현재 검증 대본으로 production을 계속합니다."\n                )\n                print(\n                    "Novelty 기준은 기록만 유지하며 자동 탐색 모드의 기준은 변경하지 않습니다."\n                )\n                final_script = candidate_script\n                break\n\n            # =================================================\n            # Runner-up Failed\n            # =================================================\n\n            if (\n                quality_result.get(\n                    "fallback_used",\n                    False,\n                )\n            ):\n'''

    # Insert after the existing REGENERATE_TOPIC block. We anchor at Runner-up
    # handling because all normal regeneration logic above remains untouched.
    text = replace_once(text, marker, replacement, "main fixed-topic novelty lock")
    MAIN_PATH.write_text(text, encoding="utf-8")
    print("✅ fixed-topic novelty regeneration loop guard applied")


if __name__ == "__main__":
    main()
