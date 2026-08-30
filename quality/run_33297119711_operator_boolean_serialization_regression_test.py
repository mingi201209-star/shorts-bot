import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".github/scripts/operator_dispatch_inputs.py"
BRIDGE = ROOT / ".github/workflows/shorts_operator_dispatch.yml"
MAIN = ROOT / ".github/workflows/main.yml"

spec = importlib.util.spec_from_file_location("operator_dispatch_inputs", HELPER)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
normalize = module.normalize_dispatch_input

# Run 33297119711 counterexample: Python bools must reach workflow_dispatch
# as the lowercase strings accepted by GitHub's boolean input schema.
assert normalize(False) == "false"
assert normalize(True) == "true"
assert normalize("false") == "false"
assert normalize("true") == "true"
assert normalize(False) != "False"
assert normalize(True) != "True"

expected_sha = "c1d888e5997922634c62cb286f97cad57be58feb"
topic = "비행기 엔진 뒤는 왜 톱니처럼 생겼을까"
candidate_scope = "aviation"
assert normalize(expected_sha) == expected_sha
assert normalize(topic) == topic
assert normalize(candidate_scope) == candidate_scope
assert normalize(7) == "7"
assert normalize(3.5) == "3.5"
assert normalize(None) == ""

for bad in ({"nested": True}, ["nested"], ("nested",)):
    try:
        normalize(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"non-scalar input did not fail closed: {bad!r}")

bridge = BRIDGE.read_text(encoding="utf-8")
main = MAIN.read_text(encoding="utf-8")

assert "from operator_dispatch_inputs import normalize_dispatch_input" in bridge
assert "normalized[key] = normalize_dispatch_input(value)" in bridge
assert 'str(value)' not in bridge.split("normalized = {}", 1)[1].split("output = Path", 1)[0]

# Existing safety contract stays intact.
for guard in (
    "github.event.comment.user.login == github.repository_owner",
    "Workflow is not allowlisted",
    "Unsupported inputs for",
    "already active",
    '--event workflow_dispatch',
    '--branch "$REF"',
    '--ref "$REF"',
):
    assert guard in bridge, f"missing bridge guard: {guard}"

# main.yml schema remains boolean and YouTube upload remains default-off.
youtube_block = main.split("youtube_upload:", 1)[1].split("youtube_privacy:", 1)[0]
assert "type: boolean" in youtube_block
assert "default: false" in youtube_block
assert "type: string" not in youtube_block
assert 'EXPECTED_SHA: ${{ inputs.expected_sha }}' in main
assert 'ref: ${{ inputs.expected_sha || github.sha }}' in main

print("PASS: Run 33297119711 workflow_dispatch boolean serialization regression")
