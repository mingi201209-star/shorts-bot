"""RECENT_TOPIC_MEMORY_WIRING_V1 regression test.

Run 604 on main failed with "Candidate Gate를 통과하는 Winner를 확보하지
못했습니다" after 10 API calls and $0.0079, i.e. before a script was ever
written.  main.py had lost the remember_used_topic() call that publish-stable
still had, and main.yml had neither the restore nor the preserve step for
recent_topics.json, so the Candidate Explorer's "recent content" context was
empty on every run and it kept re-proposing over-covered topics.

This test asserts the three pieces stay wired together.  It changes no
threshold, budget, or retry behaviour -- it only fails if the wiring is
removed again.
"""

import os
import re


REPO_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__),
    )
)


def read(relative_path):

    with open(
        os.path.join(REPO_ROOT, relative_path),
        encoding="utf-8",
    ) as handle:
        return handle.read()


def test_main_imports_and_calls_remember_used_topic():

    source = read("main.py")

    assert "remember_used_topic" in source, (
        "main.py no longer references remember_used_topic; the Candidate "
        "Explorer's recent-topic context will be empty on every run."
    )

    assert re.search(
        r"^\s*remember_used_topic\(\s*script_data\s*\)\s*$",
        source,
        re.MULTILINE,
    ), (
        "main.py imports remember_used_topic but never calls it with the "
        "produced script_data."
    )


def test_topic_selector_persists_what_main_records():

    source = read("content/topic_selector.py")

    assert "def remember_used_topic(" in source
    assert "save_recent_topics(" in source, (
        "remember_used_topic must persist through save_recent_topics so the "
        "memory survives to the preserve step."
    )


def test_workflow_restores_and_preserves_recent_topics():

    workflow = read(".github/workflows/main.yml")

    assert "name: Restore recent-topics memory" in workflow, (
        "main.yml lost the restore step; recent_topics.json starts empty on "
        "every run."
    )

    assert "python -m analytics.restore_history_artifact" in workflow

    assert "name: Preserve recent-topics memory" in workflow, (
        "main.yml lost the preserve step; recent_topics.json is discarded "
        "when the job ends."
    )

    assert "name: recent-topics-${{ github.run_id }}" in workflow

    restore_at = workflow.index("name: Restore recent-topics memory")
    generator_at = workflow.index("name: Run Shorts Generator V3.2")

    assert restore_at < generator_at, (
        "the restore step must run before the generator, otherwise the "
        "memory is loaded after the Candidate Explorer has already run."
    )


def test_restore_and_generator_agree_on_the_file_name():

    workflow = read(".github/workflows/main.yml")
    config_source = read("config.py")

    assert re.search(
        r"^RECENT_TOPICS_FILE\s*=\s*\"recent_topics\.json\"\s*$",
        config_source,
        re.MULTILINE,
    ), (
        "config.RECENT_TOPICS_FILE changed; the workflow's recent_topics.json "
        "paths would no longer match what topic_selector reads and writes."
    )

    assert "SHORTS_ANALYTICS_HISTORY_PATH: recent_topics.json" in workflow
    assert "path: recent_topics.json" in workflow


if __name__ == "__main__":

    test_main_imports_and_calls_remember_used_topic()
    test_topic_selector_persists_what_main_records()
    test_workflow_restores_and_preserves_recent_topics()
    test_restore_and_generator_agree_on_the_file_name()

    print("RECENT_TOPIC_MEMORY_WIRING_V1 regression test: PASS")
