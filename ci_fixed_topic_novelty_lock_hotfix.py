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

    marker = '''            # =================================================\n            # Candidate Regeneration\n            # =================================================\n\n            if (\n                status\n                == "REGENERATE_TOPIC"\n            ):\n'''

    replacement = '''            # =================================================\n            # Fixed-topic Novelty Lock\n            # =================================================\n            # A user-pinned production topic cannot be replaced by Candidate\n            # regeneration. When REGENERATE_TOPIC is caused by Novelty only,\n            # keep the already-validated same-topic script instead of repeatedly\n            # rediscovering the same fixed topic until the API budget is exhausted.\n            # Global novelty thresholds and all FACT/HOLD paths remain unchanged.\n\n            if (\n                forced_topic\n                and status == "REGENERATE_TOPIC"\n                and "Novelty" in str(quality_result.get("reason", ""))\n                and quality_result.get("failure_type") != "FACT_CRITICAL"\n            ):\n                candidate_script = quality_result.get("script_data")\n                if not isinstance(candidate_script, dict):\n                    raise RuntimeError(\n                        "지정 주제 Novelty lock에 사용할 검증 대본이 없습니다."\n                    )\n                candidate_topic = str(\n                    candidate_script.get("topic", current_topic)\n                ).strip()\n                if candidate_topic != forced_topic:\n                    raise RuntimeError(\n                        "지정 주제 Novelty lock의 대본 topic이 production 주제와 다릅니다."\n                    )\n\n                print("")\n                print("=" * 64)\n                print("🔒 FIXED TOPIC NOVELTY LOCK")\n                print("=" * 64)\n                print(\n                    "지정 주제는 교체하지 않고 현재 검증 대본으로 production을 계속합니다."\n                )\n                print(\n                    "Novelty 점수는 기록하지만 자동 탐색 모드의 기준은 변경하지 않습니다."\n                )\n                final_script = candidate_script\n                break\n\n            # =================================================\n            # Candidate Regeneration\n            # =================================================\n\n            if (\n                status\n                == "REGENERATE_TOPIC"\n            ):\n'''

    text = replace_once(text, marker, replacement, "main fixed-topic novelty lock")
    MAIN_PATH.write_text(text, encoding="utf-8")
    print("✅ fixed-topic novelty regeneration loop guard applied")


if __name__ == "__main__":
    main()
