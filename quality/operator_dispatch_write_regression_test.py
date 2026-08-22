import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
workflow_path = ROOT / ".github/workflows/shorts_operator_dispatch.yml"
policy_path = ROOT / ".github/workflow-dispatch-allowlist.json"

workflow = workflow_path.read_text(encoding="utf-8")
policy = json.loads(policy_path.read_text(encoding="utf-8"))
workflows = policy.get("workflows", {})

assert policy.get("version") == 1
assert "main.yml" in workflows
assert workflows["main.yml"]["ref"] == "main"
assert set(workflows["main.yml"]["allowed_inputs"]) == {"topic", "candidate_scope"}
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

for filename, settings in workflows.items():
    assert filename.endswith((".yml", ".yaml")), filename
    assert "/" not in filename and ".." not in filename, filename
    assert settings.get("ref") == "main", filename
    inputs = settings.get("allowed_inputs")
    assert isinstance(inputs, list) and len(inputs) == len(set(inputs)), filename
    assert all(isinstance(item, str) and item for item in inputs), filename

print("PASS: allowlisted workflow dispatch write contract")
