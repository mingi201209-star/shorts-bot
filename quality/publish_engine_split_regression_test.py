from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def read(name: str) -> str:
    return (WF / name).read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    assert needle in text, f"{label}: missing {needle!r}"


def forbid(text: str, needle: str, label: str) -> None:
    assert needle not in text, f"{label}: forbidden {needle!r}"


def test_bootstrap_baseline() -> None:
    data = json.loads((ROOT / "ops" / "publish_stable_bootstrap.json").read_text(encoding="utf-8"))
    assert data["stable_ref"] == "publish-stable"
    assert data["initial_stable_sha"] == "026e33ee4d3cdbeeea77e3ee40154414393d796b"
    assert data["source_production_run"] == 33871645717
    assert data["human_qa"] == "UPLOAD_READY=YES"


def test_development_tracks_main() -> None:
    text = read("development_engine.yml")
    require(text, "ENGINE_MODE=DEVELOPMENT", "development mode")
    require(text, 'commits/main', "development main resolution")
    require(text, '--ref main', "development dispatch ref")
    require(text, '-f expected_sha="$MAIN_SHA"', "development exact-main pin")
    require(text, '-f youtube_upload=false', "development no upload")


def test_publish_uses_stable_ref_not_main_runtime() -> None:
    text = read("publish_engine.yml")
    require(text, "ENGINE_MODE=PUBLISH", "publish mode")
    require(text, "STABLE_REF: publish-stable", "stable pointer")
    require(text, 'commits/$STABLE_REF', "stable SHA resolution")
    require(text, '--ref "$STABLE_REF"', "stable dispatch ref")
    require(text, '-f expected_sha=""', "stable dispatch must not assert current main")
    require(text, '-f youtube_upload=false', "publish controller no upload")
    forbid(text, 'commits/main', "publish must not resolve runtime from main")
    forbid(text, 'python ci_', "publish controller must not execute main hotfixes")
    forbid(text, 'python -m diagnostics.runner', "publish controller must not execute main generator")


def test_publish_fail_closes_sha_and_preserves_manifest() -> None:
    text = read("publish_engine.yml")
    require(text, 'if [ "$child_sha" != "$STABLE_SHA" ]', "stable SHA mismatch guard")
    require(text, "STABLE_SHA_MATCH=YES", "stable SHA match log")
    require(text, '"engine_mode": "PUBLISH"', "publish artifact mode")
    require(text, '"stable_sha": "$STABLE_SHA"', "publish artifact stable SHA")
    require(text, '"checkout_sha": "$STABLE_SHA"', "publish artifact checkout SHA")
    require(text, "production-diagnostics-*", "failure diagnostics preservation")
    require(text, "PUBLISH_FAILURE_SCOPE=STABLE_ENGINE_OR_RUNTIME", "failure scope log")


def test_stable_runtime_is_self_contained() -> None:
    publish = read("publish_engine.yml")
    stable_main = read("main.yml")
    # PUBLISH dispatches the stable ref's own main.yml. That workflow pins checkout
    # to github.sha when expected_sha is blank, so hotfixes/generator/QA all come
    # from one stable commit rather than the controller's current main tree.
    require(publish, "Verify stable workflow is self-contained", "stable contract probe")
    require(stable_main, 'ref: ${{ inputs.expected_sha || github.sha }}', "stable checkout authority")
    require(stable_main, 'if [ -z "$EXPECTED_SHA" ]', "blank expected SHA contract")
    require(stable_main, "python ci_final_visual_semantic_qa_hotfix.py", "stable hotfix composition")
    require(stable_main, "python -m diagnostics.runner", "stable generator")
    require(stable_main, "final_visual_semantic_qa.json", "stable final semantic QA")
    require(stable_main, "final_director_qa.json", "stable Director QA")


def test_promotion_is_explicit_and_validated() -> None:
    text = read("promote_publish_stable.yml")
    require(text, "workflow_dispatch:", "promotion manual trigger")
    forbid(text, "pull_request:", "promotion must not auto-trigger")
    forbid(text, "push:", "promotion must not auto-trigger")
    require(text, 'STABLE-PROMOTE:$NEW_SHA:$SOURCE_RUN', "promotion approval token")
    require(text, 'actions/runs/$SOURCE_RUN', "source production validation")
    require(text, 'run_sha" != "$NEW_SHA', "source run exact SHA guard")
    require(text, 'run_conclusion" != "success', "source run success guard")
    require(text, 'git/refs/heads/publish-stable', "stable pointer mutation")


def test_rollback_is_pointer_only_and_explicit() -> None:
    text = read("rollback_publish_stable.yml")
    require(text, "workflow_dispatch:", "rollback manual trigger")
    forbid(text, "pull_request:", "rollback must not auto-trigger")
    forbid(text, "push:", "rollback must not auto-trigger")
    require(text, 'STABLE-ROLLBACK:$TARGET_SHA', "rollback approval token")
    require(text, 'git/refs/heads/publish-stable', "rollback pointer mutation")
    require(text, '-F force=true', "rollback allows restoring an older validated SHA")


def test_main_merge_does_not_auto_promote() -> None:
    promote = read("promote_publish_stable.yml")
    rollback = read("rollback_publish_stable.yml")
    publish = read("publish_engine.yml")
    # Only explicit promotion/rollback workflows may mutate publish-stable.
    require(promote, 'git/refs/heads/publish-stable', "promotion mutation")
    require(rollback, 'git/refs/heads/publish-stable', "rollback mutation")
    forbid(publish, 'git/refs/heads/publish-stable', "publish execution must be read-only")


def run() -> None:
    tests = [
        test_bootstrap_baseline,
        test_development_tracks_main,
        test_publish_uses_stable_ref_not_main_runtime,
        test_publish_fail_closes_sha_and_preserves_manifest,
        test_stable_runtime_is_self_contained,
        test_promotion_is_explicit_and_validated,
        test_rollback_is_pointer_only_and_explicit,
        test_main_merge_does_not_auto_promote,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("PASS DEVELOPMENT_PUBLISH_ENGINE_SPLIT")


if __name__ == "__main__":
    run()
