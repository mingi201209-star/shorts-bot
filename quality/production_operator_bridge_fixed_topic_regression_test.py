from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / ".github" / "scripts" / "production_operator_bridge_parser.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "production-operator-bridge.yml"

spec = spec_from_file_location("production_operator_bridge_parser", PARSER_PATH)
parser = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(parser)

MAIN = "4" * 40
TOPIC = "비행기 착륙할 때 날개 위 판이 갑자기 올라오는 이유"


def expect_reject(request: str) -> None:
    try:
        parser.parse_request(request, MAIN)
    except ValueError:
        return
    raise AssertionError(f"expected rejection: {request!r}")


def main() -> None:
    sha, scope, topic = parser.parse_request(f"RUN-SHORTS:{MAIN}:aviation:topic={TOPIC}", MAIN)
    assert sha == MAIN and scope == "aviation" and topic == TOPIC

    korean = "착륙 직후 스포일러가 올라오는 이유"
    assert parser.parse_request(f"RUN-SHORTS:{MAIN}:aviation:topic={korean}", MAIN)[2] == korean

    expect_reject(f"RUN-SHORTS:{'5' * 40}:aviation:topic={TOPIC}")
    expect_reject(f"RUN-SHORTS:{MAIN}:aviation:topic=bad\nvalue")
    expect_reject(f"RUN-SHORTS:{MAIN}:aviation:topic=bad\tvalue")

    shellish = "spoiler; echo PWNED $(touch /tmp/nope)"
    parsed = parser.parse_request(f"RUN-SHORTS:{MAIN}:aviation:topic={shellish}", MAIN)
    assert parsed[2] == shellish
    assert not Path("/tmp/nope").exists()

    assert parser.parse_request(f"RUN-SHORTS:{MAIN}:aviation", MAIN) == (MAIN, "aviation", "")
    assert parser.parse_request("RUN-SHORTS:main", MAIN) == (MAIN, "", "")
    assert parser.parse_request(f"RUN-SHORTS:{MAIN}:aviation-flaps", MAIN)[2] == parser.FLAPS_TOPIC

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "github.event.comment.user.login == github.repository_owner" in workflow
    assert "youtube_upload=false" in workflow
    assert "gh workflow run main.yml" in workflow
    assert "--ref main" in workflow
    assert "eval " not in workflow
    assert "production_operator_bridge_parser.py" in workflow
    assert "topic_b64" in workflow
    assert "workflow_dispatch" not in workflow.split("gh workflow run main.yml", 1)[1].splitlines()[0]

    print("Production Operator Bridge fixed-topic regression PASS")


if __name__ == "__main__":
    main()
