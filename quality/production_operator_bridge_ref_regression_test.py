from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
bridge = (ROOT / ".github/workflows/production-operator-bridge.yml").read_text(encoding="utf-8")
production = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")

# The bridge must validate an exact current-main SHA, but GitHub workflow_dispatch
# requires a branch/tag ref. Pass main as the ref and carry the verified commit
# separately as expected_sha.
assert 'test "$requested" = "$main_sha"' in bridge
assert 'gh workflow run main.yml --repo "$REPO" --ref main -f expected_sha="$SHA"' in bridge
assert '--ref "$SHA"' not in bridge

# Production re-verifies the current main commit and the dispatch-resolved SHA,
# then pins checkout to the already-verified commit. Any mismatch fails closed.
assert 'expected_sha:' in production
assert 'current_main="$(gh api "repos/$REPO/commits/main" --jq .sha)"' in production
assert 'if [ "$current_main" != "$EXPECTED_SHA" ]' in production
assert 'if [ "$DISPATCH_SHA" != "$EXPECTED_SHA" ]' in production
assert 'ref: ${{ inputs.expected_sha || github.sha }}' in production

# This hotfix must not change production quality/cost contracts.
assert 'V3_MAX_API_CALLS: "60"' in production
assert 'V3_MAX_COST_USD: "0.05"' in production
assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in production

print("PASS: production operator bridge uses main ref with exact expected_sha pinning")
