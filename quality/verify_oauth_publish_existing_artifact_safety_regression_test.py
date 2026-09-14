"""Safety-contract regression for .github/workflows/verify_oauth_publish_existing_artifact.yml.

This workflow performs a REAL YouTube upload using production OAuth secrets
when dispatched, reusing an already-existing verified-shorts-* artifact (no
new video generation). This regression statically proves its safety
invariants hold in the committed YAML text, without dispatching it, without
touching any secret value, and without a PyYAML dependency (not in
requirements.txt -- plain text/regex checks only, matching this repo's
established convention for workflow-YAML regressions, e.g. PR #372's
youtube_oauth_credential_fallback_regression_test.py).
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "verify_oauth_publish_existing_artifact.yml"


def _on_block(text):
    """Return the raw text of the top-level `on:` block (up to the next
    top-level key), without depending on PyYAML's "on" -> True gotcha or any
    external dependency."""
    match = re.search(r"^on:\n(.*?)^\S", text, re.MULTILINE | re.DOTALL)
    assert match, "top-level 'on:' block not found"
    return match.group(1)


def _input_block(text, name):
    """Return the raw text of one workflow_dispatch input's block (from its
    own line to just before the next 6-space-indented input key or the end
    of the inputs section)."""
    match = re.search(
        rf"^      {re.escape(name)}:\n(.*?)(?=^      \S|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match, f"input block for {name!r} not found"
    return match.group(1)


def main():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert text.startswith("name: Verify OAuth Publish (Existing Artifact)")
    print("CASE A workflow file has the expected name/header: PASS")

    # CASE B: privacy is hardcoded to "private" -- no input exposes public
    # or unlisted, and the literal string is unconditional (not driven by
    # any input expression). The word "public" legitimately appears in this
    # file's own English safety-explanation comments ("post publicly"), so
    # check narrowly for the privacy-status usage shape, not the bare
    # substring.
    assert 'SHORTS_YOUTUBE_PRIVACY: "private"' in text, (
        "SHORTS_YOUTUBE_PRIVACY must be hardcoded private, not input-driven"
    )
    on_text = _on_block(text)
    assert "privacy" not in on_text.lower(), "no privacy-related input may exist on this workflow"
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
    assert 'echo "$YOUTUBE_ANALYTICS' not in text
    assert "print(value)" not in text
    print("CASE E only presence booleans are printed, no secret value ever echoed: PASS")

    # CASE F: required inputs exist and are all required (no accidental
    # default that could upload against the wrong artifact).
    for name in ("artifact_run_id", "artifact_name", "topic_title"):
        block = _input_block(text, name)
        assert "required: true" in block, f"input {name} must be required"
        assert "default:" not in block, f"input {name} must not have a default"
    print("CASE F all three inputs are required with no default: PASS")

    # CASE G: this workflow is workflow_dispatch only -- it never runs
    # automatically on push/pull_request/schedule.
    assert "workflow_dispatch:" in on_text
    for forbidden in ("push:", "pull_request:", "schedule:"):
        assert forbidden not in on_text, f"workflow must not trigger on {forbidden}"
    print("CASE G workflow_dispatch only, no automatic trigger: PASS")

    print("VERIFY OAUTH PUBLISH EXISTING ARTIFACT SAFETY REGRESSION: PASS")


if __name__ == "__main__":
    main()
