import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
workflow_path = ROOT / ".github/workflows/shorts_operator_dispatch.yml"
policy_path = ROOT / ".github/workflow-dispatch-allowlist.json"
main_workflow_path = ROOT / ".github/workflows/main.yml"

workflow = workflow_path.read_text(encoding="utf-8")
main_workflow = main_workflow_path.read_text(encoding="utf-8")
policy = json.loads(policy_path.read_text(encoding="utf-8"))
workflows = policy.get("workflows", {})

assert policy.get("version") == 1
assert "main.yml" in workflows
assert workflows["main.yml"]["ref"] == "main"
assert set(workflows["main.yml"]["allowed_inputs"]) == {
    "topic",
    "candidate_scope",
    "youtube_upload",
    "youtube_privacy",
}
assert "shorts_operator_dispatch.yml" not in workflows

required_guards = (
    "github.event.issue.number == 33",
    "github.event.comment.user.login == github.repository_owner",
    "Workflow is not allowlisted",
    "Unsupported inputs for",
    "already active",
    "--event workflow_dispatch",
    "--branch \"$REF\"",
    "--ref \"$REF\"",
    "run_sha",
)
for guard in required_guards:
    assert guard in workflow, f"missing dispatch safety guard: {guard}"

assert "startsWith(github.event.comment.body, '/workflow-run ')" in workflow
assert "args=(workflow run \"$WORKFLOW\"" in workflow
assert "gh \"\\${args[@]}\"" not in workflow
assert 'gh "${args[@]}"' in workflow

# Upload remains explicit and fail-closed: operator dispatch can forward the
# inputs, but main.yml defaults the mutation off and only turns it on when the
# caller supplies youtube_upload=true.
assert 'youtube_upload:' in main_workflow
assert 'default: false' in main_workflow
assert "ENABLE_YOUTUBE_UPLOAD: ${{ inputs.youtube_upload && '1' || '0' }}" in main_workflow
assert "SHORTS_YOUTUBE_PRIVACY: ${{ inputs.youtube_privacy }}" in main_workflow

for filename, settings in workflows.items():
    assert filename.endswith((".yml", ".yaml")), filename
    assert "/" not in filename and ".." not in filename, filename
    assert settings.get("ref") == "main", filename
    inputs = settings.get("allowed_inputs")
    assert isinstance(inputs, list) and len(inputs) == len(set(inputs)), filename
    assert all(isinstance(item, str) and item for item in inputs), filename

print("PASS: allowlisted workflow dispatch write contract")
