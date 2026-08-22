from pathlib import Path

MAIN_PATH = Path("main.py")

OLD = '''            explorer_result = (\n                explore_candidates(\n                    topic_info,\n                    recent_topics=recent_topics,\n                    rejected_topics=(\n                        []\n                        if forced_topic\n                        else rejected_topics\n                    ),\n                    fixed_topic=(\n                        forced_topic\n                        or None\n                    ),\n                    fixed_topic_gate_feedback=(\n                        fixed_topic_gate_feedback\n                        if forced_topic\n                        else ""\n                    ),\n                )\n            )\n'''

NEW = '''            try:\n                explorer_result = (\n                    explore_candidates(\n                        topic_info,\n                        recent_topics=recent_topics,\n                        rejected_topics=(\n                            []\n                            if forced_topic\n                            else rejected_topics\n                        ),\n                        fixed_topic=(\n                            forced_topic\n                            or None\n                        ),\n                        fixed_topic_gate_feedback=(\n                            fixed_topic_gate_feedback\n                            if forced_topic\n                            else ""\n                        ),\n                    )\n                )\n            except TypeError as explorer_call_error:\n                if (\n                    "unexpected keyword argument 'fixed_topic_gate_feedback'"\n                    not in str(explorer_call_error)\n                ):\n                    raise\n\n                print(\n                    "⚠️ fixed_topic_gate_feedback runtime compatibility fallback"\n                )\n\n                explorer_result = (\n                    explore_candidates(\n                        topic_info,\n                        recent_topics=recent_topics,\n                        rejected_topics=(\n                            [fixed_topic_gate_feedback]\n                            if (\n                                forced_topic\n                                and fixed_topic_gate_feedback\n                            )\n                            else (\n                                []\n                                if forced_topic\n                                else rejected_topics\n                            )\n                        ),\n                        fixed_topic=(\n                            forced_topic\n                            or None\n                        ),\n                    )\n                )\n'''


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")

    if "[fixed_topic_gate_feedback]" in text and "runtime compatibility fallback" in text:
        print("✅ fixed-topic runtime call compatibility with feedback already applied")
        return

    if "fixed_topic_gate_feedback runtime compatibility fallback" in text:
        old_fallback = '''                        rejected_topics=(\n                            []\n                            if forced_topic\n                            else rejected_topics\n                        ),\n                        fixed_topic=(\n                            forced_topic\n                            or None\n                        ),\n'''
        new_fallback = '''                        rejected_topics=(\n                            [fixed_topic_gate_feedback]\n                            if (\n                                forced_topic\n                                and fixed_topic_gate_feedback\n                            )\n                            else (\n                                []\n                                if forced_topic\n                                else rejected_topics\n                            )\n                        ),\n                        fixed_topic=(\n                            forced_topic\n                            or None\n                        ),\n'''
        # Only replace the fallback occurrence: the wrapped primary call must keep
        # an empty rejected list in fixed-topic mode.
        idx = text.find("fixed_topic_gate_feedback runtime compatibility fallback")
        tail = text[idx:]
        if old_fallback not in tail:
            raise RuntimeError("runtime fallback rejected_topics marker not found")
        tail = tail.replace(old_fallback, new_fallback, 1)
        MAIN_PATH.write_text(text[:idx] + tail, encoding="utf-8")
        print("✅ fixed-topic runtime fallback now preserves Gate feedback")
        return

    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(
            f"fixed-topic explorer call marker count mismatch: {count}"
        )

    MAIN_PATH.write_text(
        text.replace(OLD, NEW, 1),
        encoding="utf-8",
    )
    print("✅ fixed-topic runtime call compatibility applied")


if __name__ == "__main__":
    main()
