from pathlib import Path
import re

EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "FIXED_TOPIC_GATE_FEEDBACK_SIGNATURE_V1"


def _patch_signature(text, function_name):
    pattern = re.compile(
        rf"def {re.escape(function_name)}\(\n(?P<body>.*?)\n\):",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        raise RuntimeError(f"{function_name} signature not found")

    match = matches[-1]
    body = match.group("body")
    if "fixed_topic_gate_feedback" in body:
        return text

    anchor = "    fixed_topic=None,\n"
    if anchor not in body:
        raise RuntimeError(
            f"{function_name} fixed_topic signature anchor missing"
        )

    patched_body = body.replace(
        anchor,
        anchor + '    fixed_topic_gate_feedback="",\n',
        1,
    )
    return text[: match.start("body")] + patched_body + text[match.end("body") :]


def _patch_keyword_forwarding(text, callee):
    pattern = re.compile(
        rf"{re.escape(callee)}\(\n(?P<body>.*?)\n\s*\)",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        raise RuntimeError(f"{callee} call not found")

    # Patch the last call that already forwards fixed_topic. This avoids touching
    # unrelated legacy calls while keeping the active production wrapper intact.
    for match in reversed(matches):
        body = match.group("body")
        if "fixed_topic=fixed_topic" not in body:
            continue
        if "fixed_topic_gate_feedback" in body:
            return text
        anchor = "        fixed_topic=fixed_topic,\n"
        if anchor not in body:
            continue
        patched_body = body.replace(
            anchor,
            anchor
            + "        fixed_topic_gate_feedback=fixed_topic_gate_feedback,\n",
            1,
        )
        return text[: match.start("body")] + patched_body + text[match.end("body") :]

    raise RuntimeError(f"{callee} fixed_topic forwarding call not found")


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    # Topic input may be installed before aviation wrappers. Later wrappers must
    # not narrow the callable contract and drop the gate-feedback parameter.
    text = _patch_signature(text, "explore_candidates")
    text = _patch_signature(text, "build_execution_context")
    text = _patch_keyword_forwarding(text, "build_execution_context")

    if MARKER not in text:
        text = text.rstrip() + f"\n\n# {MARKER}\n"

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Fixed-topic gate-feedback runtime signature preserved")


if __name__ == "__main__":
    main()
