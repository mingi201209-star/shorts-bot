from pathlib import Path

EXPLORER_PATH = Path("content/candidate_explorer.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label} marker count mismatch: {count}")
    return text.replace(marker, replacement, 1)


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    signature_marker = '''def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
):
    context = _aviation_specificity_previous_build_context(
'''
    signature_replacement = '''def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
):
    context = _aviation_specificity_previous_build_context(
'''

    forward_marker = '''        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
    )
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
'''
    forward_replacement = '''        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic=fixed_topic,
    )
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
'''

    text = replace_once(
        text,
        signature_marker,
        signature_replacement,
        "aviation specificity context signature compatibility",
    )
    text = replace_once(
        text,
        forward_marker,
        forward_replacement,
        "aviation specificity fixed_topic forwarding",
    )

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation specificity fixed_topic signature compatibility applied")


if __name__ == "__main__":
    main()
