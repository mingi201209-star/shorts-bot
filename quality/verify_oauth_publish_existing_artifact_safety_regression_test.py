"""Safety-contract regression for .github/workflows/verify_oauth_publish_existing_artifact.yml.

This workflow performs a REAL YouTube upload using production OAuth secrets
when dispatched, reusing an already-existing verified-shorts-* artifact (no
new video generation). This regression statically proves its safety
invariants hold in the committed YAML, without dispatching it or touching
any secret value.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "verify_oauth_publish_existing_artifact.yml"


def main():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    assert isinstance(doc, dict), "workflow YAML must parse to a mapping"
    # PyYAML (1.1 resolver) parses the bare "on:" key as the boolean True,
    # not the string "on" -- a well-known gotcha. Normalize it back.
    on_block = doc.get("on")
    if on_block is None and True in doc:
        on_block = doc[True]
    assert isinstance(on_block, dict), "workflow must have an 'on' trigger block"
    print("CASE A workflow YAML parses: PASS")

    # CASE B: privacy is hardcoded to "private" -- no input exposes public
    # or unlisted, and the literal string is unconditional (not driven by
    # any input expression).
    assert 'SHORTS_YOUTUBE_PRIVACY: "private"' in text, (
        "SHORTS_YOUTUBE_PRIVACY must be hardcoded private, not input-driven"
    )
    inputs = (on_block.get("workflow_dispatch") or {}).get("inputs") or {}
    assert "privacy" not in " ".join(inputs.keys()).lower(), (
        "no privacy-related input may exist on this workflow"
    )
    # "public" as a privacy value (e.g. an options list, or a YAML value
    # assignment) must never appear -- but the word legitimately appears in
    # this file's own English safety-explanation comments ("post publicly"),
    # so check narrowly for the privacy-status usage shape, not the bare
    # substring.
    assert not re.search(r"privacy_status.*public|SHORTS_YOUTUBE_PRIVACY.*public", text, re.IGNORECASE)
    assert "- public" not in text, "no options list may offer a public choice"
    print("CASE B privacy hardcoded to private, no public path exists: PASS")

    # CASE C: no new video is generated -- the workflow never invokes the
    # production generator (main.py) or the hotfix composition chain, only
    # downloads an existing artifact.
    assert "python main.py" not in text
    assert "Shorts Generator V3.2" not in text
    assert "ci_hotfix.py" not in text
    assert "actions/download-artifact" in text
    print("CASE C no new video generation invoked, artifact is downloaded: PASS")

    # CASE D: OAuth credential fallback wiring matches PR #372's pattern
    # exactly (current name first, legacy alias fallback), for both the
    # presence-check step and the actual publish step.
    fallback_pattern = re.compile(
        r"YOUTUBE_ANALYTICS_CLIENT_ID:\s*\$\{\{\s*secrets\.YOUTUBE_ANALYTICS_CLIENT_ID\s*\|\|\s*secrets\.YT_CLIENT_ID\s*\}\}"
    )
    assert len(fallback_pattern.findall(text)) == 2, "expected the fallback pattern in both steps that reference it"
    print("CASE D OAuth credential fallback wiring present in both steps: PASS")

    # CASE E: secret values are never echoed -- only presence booleans.
    assert "present={bool(value.strip())}" in text
    assert "echo \"$YOUTUBE_ANALYTICS" not in text
    assert "print(value)" not in text
    print("CASE E only presence booleans are printed, no secret value ever echoed: PASS")

    # CASE F: required inputs exist and are all required (no accidental
    # default that could upload against the wrong artifact).
    for name in ("artifact_run_id", "artifact_name", "topic_title"):
        assert name in inputs, f"missing required input: {name}"
        assert inputs[name].get("required") is True, f"input {name} must be required"
        assert "default" not in inputs[name], f"input {name} must not have a default"
    print("CASE F all three inputs are required with no default: PASS")

    # CASE G: this workflow is workflow_dispatch only -- it never runs
    # automatically on push/pull_request/schedule.
    assert set(on_block.keys()) == {"workflow_dispatch"}, (
        f"workflow must be workflow_dispatch only, got triggers: {list(on_block.keys())}"
    )
    print("CASE G workflow_dispatch only, no automatic trigger: PASS")

    print("VERIFY OAUTH PUBLISH EXISTING ARTIFACT SAFETY REGRESSION: PASS")


if __name__ == "__main__":
    main()
