from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bridge = (ROOT / ".github/workflows/production-operator-bridge.yml").read_text(encoding="utf-8")
production = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
parser_path = ROOT / ".github/scripts/production_operator_bridge_parser.py"

spec = spec_from_file_location("production_operator_bridge_parser", parser_path)
parser = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(parser)

main_sha = "a" * 40

# The bridge must validate an exact current-main SHA, dispatch main.yml from the
# branch ref main, and carry the verified commit separately as expected_sha.
assert 'github.event.comment.user.login == github.repository_owner' in bridge
assert 'main_sha="$(gh api "repos/$REPO/commits/main" --jq .sha)"' in bridge
assert 'production_operator_bridge_parser.py "$REQUEST" "$main_sha"' in bridge
assert 'gh workflow run main.yml --repo "$REPO" --ref main' in bridge
assert '-f expected_sha="$SHA"' in bridge
assert '-f candidate_scope="$SCOPE"' in bridge
assert '-f topic="$TOPIC"' in bridge
assert '-f youtube_upload=false' in bridge
assert '--ref "$SHA"' not in bridge
assert 'eval ' not in bridge

# Legacy operator commands remain supported through the validated parser.
assert parser.parse_request(f"RUN-SHORTS:{main_sha}:aviation", main_sha) == (main_sha, "aviation", "")
assert parser.parse_request(f"RUN-SHORTS:{main_sha}:aviation-flaps", main_sha)[2] == parser.FLAPS_TOPIC

# New arbitrary fixed-topic mode remains bounded to aviation and exact main.
topic = "비행기 착륙할 때 날개 위 판이 갑자기 올라오는 이유"
assert parser.parse_request(f"RUN-SHORTS:{main_sha}:aviation:topic={topic}", main_sha) == (main_sha, "aviation", topic)
try:
    parser.parse_request(f"RUN-SHORTS:{'b' * 40}:aviation:topic={topic}", main_sha)
except ValueError:
    pass
else:
    raise AssertionError("wrong expected SHA must fail closed")

# Production re-verifies the current main commit and the dispatch-resolved SHA,
# then pins checkout to the already-verified commit. Any mismatch fails closed.
assert 'expected_sha:' in production
assert 'current_main="$(gh api "repos/$REPO/commits/main" --jq .sha)"' in production
assert 'if [ "$current_main" != "$EXPECTED_SHA" ]' in production
assert 'if [ "$DISPATCH_SHA" != "$EXPECTED_SHA" ]' in production
assert 'ref: ${{ inputs.expected_sha || github.sha }}' in production

# Bridge work must not change production quality/cost contracts.
assert 'V3_MAX_API_CALLS: "60"' in production
assert 'V3_MAX_COST_USD: "0.05"' in production
assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in production

print("PASS: production operator bridge uses main ref with exact expected_sha pinning")
