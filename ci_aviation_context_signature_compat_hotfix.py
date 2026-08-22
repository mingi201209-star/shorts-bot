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

    insertion = f"    {keyword}={default},\n"
    for anchor in (
        "    fixed_topic=None,\n",
        "    rejected_topics=None,\n",
        "    recent_content=None,\n",
        "    recent_topics=None,\n",
    ):
        if anchor not in signature:
            continue
        extra = insertion
        if keyword == "fixed_topic_gate_feedback" and "fixed_topic" not in signature:
            extra = "    fixed_topic=None,\n" + insertion
        signature = signature.replace(anchor, anchor + extra, 1)
        return text[:start] + signature + text[end:]

    prefix = ""
    if keyword == "fixed_topic_gate_feedback" and "fixed_topic" not in signature:
        prefix = "    fixed_topic=None,\n"
    signature = signature.rstrip() + "\n" + prefix + insertion.rstrip("\n")
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
    # Any existing keyword assignment counts, including topic-input's normalized
    # expression. Adding a second assignment would create a SyntaxError.
    if f"{keyword}=" in call:
        return text

    insertion = f"        {keyword}={keyword},\n"
    for anchor in (
        "        fixed_topic=fixed_topic,\n",
        "        rejected_topics=rejected_topics,\n",
        "        recent_content=recent_content,\n",
        "        recent_topics=recent_topics,\n",
    ):
        if anchor not in call:
            continue
        extra = insertion
        if keyword == "fixed_topic_gate_feedback" and "fixed_topic=" not in call:
            extra = "        fixed_topic=fixed_topic,\n" + insertion
        call = call.replace(anchor, anchor + extra, 1)
        return text[:call_start] + call + text[call_end:]

    raise RuntimeError(f"{callee} forwarding anchor not found")


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    text = _ensure_signature_keyword(
        text, "build_execution_context", "fixed_topic_gate_feedback", '""'
    )
    text = _ensure_forwarded_keyword(
        text,
        "build_execution_context",
        "_aviation_specificity_previous_build_context",
        "fixed_topic_gate_feedback",
    )
    text = _ensure_signature_keyword(
        text, "explore_candidates", "fixed_topic_gate_feedback", '""'
    )
    text = _ensure_forwarded_keyword(
        text, "explore_candidates", "build_execution_context", "fixed_topic_gate_feedback"
    )

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation fixed-topic + gate-feedback signature compatibility applied")


if __name__ == "__main__":
    main()
