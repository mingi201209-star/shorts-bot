#!/usr/bin/env python3
import base64
import re
import sys

MAX_TOPIC_LEN = 180
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
FIXED_RE = re.compile(r"^RUN-SHORTS:([^:]+):aviation:topic=(.+)$", re.DOTALL)
LEGACY_FLAPS_RE = re.compile(r"^RUN-SHORTS:([^:]+):aviation-flaps$")
LEGACY_AVIATION_RE = re.compile(r"^RUN-SHORTS:([^:]+):aviation$")
LEGACY_MAIN_RE = re.compile(r"^RUN-SHORTS:([^:]+)$")

FLAPS_TOPIC = "비행기 날개 뒤쪽 플랩은 왜 이착륙 때 펼쳐질까"


def _validate_topic(topic: str) -> str:
    if not topic or len(topic) > MAX_TOPIC_LEN:
        raise ValueError("topic length invalid")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in topic):
        raise ValueError("topic contains control characters")
    return topic


def parse_request(request: str, current_main: str) -> tuple[str, str, str]:
    scope = ""
    topic = ""

    match = FIXED_RE.fullmatch(request)
    if match:
        requested, topic = match.groups()
        scope = "aviation"
        topic = _validate_topic(topic)
    else:
        match = LEGACY_FLAPS_RE.fullmatch(request)
        if match:
            requested = match.group(1)
            scope = "aviation"
            topic = FLAPS_TOPIC
        else:
            match = LEGACY_AVIATION_RE.fullmatch(request)
            if match:
                requested = match.group(1)
                scope = "aviation"
            else:
                match = LEGACY_MAIN_RE.fullmatch(request)
                if not match:
                    raise ValueError("unsupported RUN-SHORTS command")
                requested = match.group(1)

    requested = requested.strip()
    if requested == "main":
        requested = current_main
    if not SHA_RE.fullmatch(requested):
        raise ValueError("expected SHA must be 40 hex characters")
    if requested.lower() != current_main.lower():
        raise ValueError("expected SHA does not match current main")
    return requested.lower(), scope, topic


def encode_topic(topic: str) -> str:
    return base64.b64encode(topic.encode("utf-8")).decode("ascii")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: production_operator_bridge_parser.py <request> <current-main>", file=sys.stderr)
        return 2
    try:
        sha, scope, topic = parse_request(sys.argv[1], sys.argv[2])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"sha={sha}")
    print(f"scope={scope}")
    print(f"topic_b64={encode_topic(topic)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
