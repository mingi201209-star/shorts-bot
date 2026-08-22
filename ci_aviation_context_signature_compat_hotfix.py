from pathlib import Path

EXPLORER_PATH = Path("content/candidate_explorer.py")


def _ensure_signature_keyword(text, function_name, keyword, default):
    start = text.rfind(f"def {function_name}(")
    if start < 0:
        raise RuntimeError(f"{function_name} definition not found")
    end = text.find("\n):", start)
    if end < 0:
        raise RuntimeError(f"{function_name} signature terminator not found")

    signature = text[start:end]
    if keyword in signature:
        return text

    anchor = "    fixed_topic=None,\n"
    insertion = f"    {keyword}={default},\n"
    if anchor in signature:
        signature = signature.replace(anchor, anchor + insertion, 1)
    else:
        anchor = "    rejected_topics=None,\n"
        if anchor not in signature:
            raise RuntimeError(f"{function_name} signature anchor not found")
        signature = signature.replace(
            anchor,
            anchor + "    fixed_topic=None,\n" + insertion,
            1,
        )

    return text[:start] + signature + text[end:]


def _ensure_forwarded_keyword(text, function_name, callee, keyword):
    function_start = text.rfind(f"def {function_name}(")
    if function_start < 0:
        raise RuntimeError(f"{function_name} definition not found")

    call_start = text.find(f"{callee}(\n", function_start)
    if call_start < 0:
        raise RuntimeError(f"{callee} call not found in {function_name}")
    call_end = text.find("\n    )", call_start)
    if call_end < 0:
        call_end = text.find("\n        )", call_start)
    if call_end < 0:
        raise RuntimeError(f"{callee} call terminator not found")

    call = text[call_start:call_end]
    if f"{keyword}={keyword}" in call:
        return text

    anchor = "        fixed_topic=fixed_topic,\n"
    insertion = f"        {keyword}={keyword},\n"
    if anchor in call:
        call = call.replace(anchor, anchor + insertion, 1)
    else:
        anchor = "        rejected_topics=rejected_topics,\n"
        if anchor not in call:
            raise RuntimeError(f"{callee} forwarding anchor not found")
        call = call.replace(
            anchor,
            anchor + "        fixed_topic=fixed_topic,\n" + insertion,
            1,
        )

    return text[:call_start] + call + text[call_end:]


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    # Aviation specificity installs a later build_execution_context wrapper. Keep
    # the complete fixed-topic contract when that wrapper becomes the active one.
    text = _ensure_signature_keyword(
        text,
        "build_execution_context",
        "fixed_topic_gate_feedback",
        '""',
    )
    text = _ensure_forwarded_keyword(
        text,
        "build_execution_context",
        "_aviation_specificity_previous_build_context",
        "fixed_topic_gate_feedback",
    )

    # Production calls explore_candidates with both fixed_topic and Gate feedback.
    # Guard the public Explorer signature as well so later wrappers cannot narrow it.
    text = _ensure_signature_keyword(
        text,
        "explore_candidates",
        "fixed_topic_gate_feedback",
        '""',
    )
    text = _ensure_forwarded_keyword(
        text,
        "explore_candidates",
        "build_execution_context",
        "fixed_topic_gate_feedback",
    )

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation fixed-topic + gate-feedback signature compatibility applied")


if __name__ == "__main__":
    main()
