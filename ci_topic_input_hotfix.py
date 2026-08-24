from pathlib import Path


MAIN_PATH = Path("main.py")
EXPLORER_PATH = Path("content/candidate_explorer.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text

    if (
        label == "main explorer call"
        and "fixed_topic_gate_feedback runtime compatibility fallback" in text
        and "fixed_topic_gate_feedback=(" in text
        and "fixed_topic=(" in text
    ):
        return text

    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label} marker count mismatch: {count}")
    return text.replace(marker, replacement, 1)


def patch_main():
    text = MAIN_PATH.read_text(encoding="utf-8")

    environment_marker = '''        validate_environment()\n\n        final_script = None\n'''
    environment_replacement = '''        validate_environment()\n\n        forced_topic = os.environ.get(\n            "SHORTS_TOPIC",\n            "",\n        ).strip()\n\n        if forced_topic:\n            print(\n                "🎯 지정 production 주제:",\n                forced_topic,\n            )\n\n        fixed_topic_gate_feedback = ""\n\n        final_script = None\n'''

    direction_marker = '''            topic_info = (\n                choose_topic_direction()\n            )\n'''
    direction_replacement = '''            if forced_topic:\n\n                topic_info = {\n                    "category": "지정 주제",\n                    "topic": forced_topic,\n                }\n\n            else:\n\n                topic_info = (\n                    choose_topic_direction()\n                )\n'''

    explorer_marker = '''                explore_candidates(\n                    topic_info,\n                    recent_topics=recent_topics,\n                    rejected_topics=rejected_topics,\n                )\n'''
    explorer_replacement = '''                explore_candidates(\n                    topic_info,\n                    recent_topics=recent_topics,\n                    rejected_topics=rejected_topics,\n                    fixed_topic=(\n                        forced_topic\n                        if forced_topic\n                        else None\n                    ),\n                    fixed_topic_gate_feedback=(\n                        fixed_topic_gate_feedback\n                        if forced_topic\n                        else None\n                    ),\n                )\n'''

    runner_marker = '''            runner_up = (\n                explorer_result.get(\n                    "runner_up"\n                )\n            )\n'''
    runner_replacement = '''            runner_up = (\n                None\n                if forced_topic\n                else explorer_result.get(\n                    "runner_up"\n                )\n            )\n'''

    rejected_marker = '''            if (\n                current_topic\n                in rejected_topics\n            ):\n'''
    rejected_replacement = '''            if (\n                not forced_topic\n                and current_topic\n                in rejected_topics\n            ):\n'''

    topic_guard_marker = '''            if not current_topic:\n\n                raise RuntimeError(\n                    "Candidate Explorer Winner에 "\n                    "topic이 없습니다."\n                )\n\n            print("")\n'''
    topic_guard_replacement = '''            if not current_topic:\n\n                raise RuntimeError(\n                    "Candidate Explorer Winner에 "\n                    "topic이 없습니다."\n                )\n\n            if (\n                forced_topic\n                and current_topic != forced_topic\n            ):\n\n                raise RuntimeError(\n                    "지정 production 주제와 "\n                    "Candidate Explorer Winner topic이 "\n                    "일치하지 않습니다."\n                )\n\n            print("")\n'''

    gate_feedback_marker = '''                print_budget_status()\n\n                if (\n                    topic_attempt\n                    < total_topic_attempts\n                ):\n\n                    print("")\n\n                    print(\n                        "➡️ Candidate Explorer 재탐색"\n                    )\n\n                    continue\n\n                raise RuntimeError(\n                    "Candidate Gate를 통과하는 "\n                    "Winner를 확보하지 못했습니다. "\n                    "마지막 이유: "\n                    f"{winner_gate.get('reason', '')}"\n                )\n'''
    gate_feedback_replacement = '''                print_budget_status()\n\n                if forced_topic:\n                    fixed_topic_gate_feedback = str(\n                        winner_gate.get(\n                            "reason",\n                            "",\n                        )\n                    ).strip()\n                    if (\n                        topic_attempt\n                        < total_topic_attempts\n                    ):\n                        print("")\n                        print(\n                            "➡️ 지정 주제는 유지하고 Candidate를 재탐색"\n                        )\n                        continue\n\n                elif (\n                    topic_attempt\n                    < total_topic_attempts\n                ):\n\n                    print("")\n\n                    print(\n                        "➡️ Candidate Explorer 재탐색"\n                    )\n\n                    continue\n\n                raise RuntimeError(\n                    "Candidate Gate를 통과하는 "\n                    "Winner를 확보하지 못했습니다. "\n                    "마지막 이유: "\n                    f"{winner_gate.get('reason', '')}"\n                )\n'''

    # Match the stable status branch itself, not the surrounding comment block.
    # Earlier hotfixes may add comments around Candidate Regeneration, which made
    # the old marker order-dependent even though runtime semantics were unchanged.
    quality_regen_marker = '''            if (\n                status\n                == "REGENERATE_TOPIC"\n            ):\n\n                rejected_topic = str(\n'''
    quality_regen_replacement = '''            # Fixed-topic Novelty Lock: an explicitly pinned production topic\n            # cannot become more novel by rediscovering the same topic. Keep the\n            # global Novelty threshold unchanged for automatic discovery, and\n            # fail-close for FACT_CRITICAL or any non-Novelty failure.\n            if (\n                forced_topic\n                and status == "REGENERATE_TOPIC"\n                and "Novelty" in str(\n                    quality_result.get(\n                        "reason",\n                        "",\n                    )\n                )\n                and quality_result.get(\n                    "failure_type"\n                ) != "FACT_CRITICAL"\n            ):\n                fixed_topic_script = quality_result.get(\n                    "script_data"\n                )\n                if not isinstance(fixed_topic_script, dict):\n                    raise RuntimeError(\n                        "지정 주제 Novelty lock에 사용할 검증 대본이 없습니다."\n                    )\n                fixed_script_topic = str(\n                    fixed_topic_script.get(\n                        "topic",\n                        current_topic,\n                    )\n                ).strip()\n                if fixed_script_topic != forced_topic:\n                    raise RuntimeError(\n                        "지정 주제 Novelty lock의 대본 topic이 production 주제와 다릅니다."\n                    )\n                print("")\n                print("=" * 64)\n                print("🔒 FIXED TOPIC NOVELTY LOCK")\n                print("=" * 64)\n                print(\n                    "지정 주제는 교체하지 않고 현재 검증 대본으로 production을 계속합니다."\n                )\n                print(\n                    "Novelty 점수는 기록하지만 자동 탐색 모드의 기준은 변경하지 않습니다."\n                )\n                final_script = fixed_topic_script\n                break\n\n            if (\n                status\n                == "REGENERATE_TOPIC"\n            ):\n\n                rejected_topic = str(\n'''

    for marker, replacement, label in (
        (environment_marker, environment_replacement, "main forced topic environment"),
        (direction_marker, direction_replacement, "main topic direction"),
        (explorer_marker, explorer_replacement, "main explorer call"),
        (runner_marker, runner_replacement, "main runner-up"),
        (rejected_marker, rejected_replacement, "main rejected topic guard"),
        (topic_guard_marker, topic_guard_replacement, "main fixed topic guard"),
        (gate_feedback_marker, gate_feedback_replacement, "main fixed topic gate feedback"),
        (quality_regen_marker, quality_regen_replacement, "main fixed topic novelty lock"),
    ):
        text = replace_once(text, marker, replacement, label)

    MAIN_PATH.write_text(text, encoding="utf-8")


def patch_candidate_explorer():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    # Existing candidate-explorer patch body is already installed by this file in
    # the branch. Keep it untouched when its production markers are present.
    if (
        "[PREVIOUS CANDIDATE GATE FEEDBACK]" in text
        and "fixed_topic_gate_feedback" in text
        and "Candidate Explorer가 지정 production 주제를" in text
    ):
        print("✅ production topic input hotfix already applied")
        return

    # The branch's historical installer contains the complete explorer migration;
    # refusing to guess here is safer than silently applying a partial contract.
    raise RuntimeError("candidate explorer fixed-topic contract is not installed")


def main():
    patch_main()
    patch_candidate_explorer()
    print("✅ production topic input + fixed-topic novelty lock hotfix applied")


if __name__ == "__main__":
    main()
