from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/shorts_continuous_relay.yml").read_text(
    encoding="utf-8"
)

required = (
    'workflows: ["Shorts Generator"]',
    "types: [completed]",
    "actions: write",
    "contents: read",
    "issues: write",
    "github.event.workflow_run.repository.full_name == github.repository",
    "github.event.workflow_run.head_branch == 'main'",
    "github.event.workflow_run.event == 'workflow_dispatch'",
    'MAX_TRANSIENT_ATTEMPTS: "2"',
    "shorts-relay:${RUN_ID}:${RUN_ATTEMPT}",
    "Relay checkpoint already exists",
    "verified-shorts-${RUN_ID}-${RUN_SHA}",
    ".expired == false",
    ".size_in_bytes > 0",
    'gh run rerun "$RUN_ID" --repo "$REPO" --failed',
    "RUN_ATTEMPT < MAX_TRANSIENT_ATTEMPTS",
    "no blind rerun was started",
)
for marker in required:
    assert marker in workflow, f"missing continuous relay guard: {marker}"

for forbidden in (
    "gh workflow run",
    "youtube_upload: true",
    "AI_VISUAL_FALLBACK_ENABLED: true",
    "--admin",
    "--force",
):
    assert forbidden not in workflow, f"unsafe relay behavior present: {forbidden}"

assert workflow.count("gh run rerun") == 1
print("PASS: bounded event-driven Shorts relay contract")
