from pathlib import Path

RUNNER_PATH = Path("content/script_engine_v2_runner.py")
ENGINE_PATH = Path("content/script_engine_v2.py")
MARKER = "# SCRIPT_V2_GUNGGEUM_FORMAL_ENDING_V1"
GENERAL_DECLARATIVE_MARKER = "# SCRIPT_V2_GENERAL_HANDA_FORMAL_ENDING_V1"
HOOK_MARKER = "# SCRIPT_V2_RECOVERED_QUESTION_HOOK_V1"
TOPIC_HOOK_MARKER = "# SCRIPT_V2_RECOVERED_TOPIC_HOOK_V1"
FINAL_HOOK_MARKER = "# SCRIPT_V2_FINAL_OBSERVABLE_HOOK_NORMALIZATION_V1"
PLAIN_QUESTION_MARKER = "# SCRIPT_V2_PLAIN_QUESTION_BOUNDARY_V1"
GROUNDED_TOPIC_QUESTION_MARKER = "# SCRIPT_V2_GROUNDED_TOPIC_QUESTION_FALLBACK_V1"
NEEDLE = '    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n'
REPLACEMENT = (
    NEEDLE
    + '    # SCRIPT_V2_GUNGGEUM_FORMAL_ENDING_V1\n'
    + '    (r"궁금해진다(?=[.!?…]*$)", "궁금해집니다"),\n'
    + '    (r"용이해진다(?=[.!?…]*$)", "용이해집니다"),\n'
    + '    (r"가능해진다(?=[.!?…]*$)", "가능해집니다"),\n'
    + '    (r"이루어진다(?=[.!?…]*$)", "이루어집니다"),\n'
    + '    (r"알려진다(?=[.!?…]*$)", "알려집니다"),\n'
    + '    (r"도와준다(?=[.!?…]*$)", "도와줍니다"),\n'
    + '    (r"사실(?=[.!?…]*$)", "사실입니다"),\n'
    + '    (r"있나요(?=[?…]*$)", "있습니까"),\n'
    + '    # SCRIPT_V2_GENERAL_HANDA_FORMAL_ENDING_V1\n'
    + '    # Declarative-only terminal normalization. Deliberately excludes ? so\n'
    + '    # question contracts remain owned by the existing question repair path.\n'
    + '    (r"한다(?=[.!…]*$)", "합니다"),\n'
)
HOOK_NEEDLE = '_QUESTION_HOOK_REPAIRS = (\n'
HOOK_REPLACEMENT = (
    HOOK_NEEDLE
    + '    # SCRIPT_V2_RECOVERED_QUESTION_HOOK_V1\n'
    + '    (r"(?:이 )?작은 갈고리는 비행기의 비행 성능에 어떤 영향을 미칠까$", "비행기 날개에는 작은 갈고리가 있습니다"),\n'
    + '    (r"둥글게 설계되었을까$", "둥글게 설계되었습니다"),\n'
    + '    (r"펼쳐질까$", "펼쳐집니다"),\n'
    + '    (r"둥근가$", "둥급니다"),\n'
    + '    (r"있을까$", "있습니다"),\n'
    + '    (r"없을까$", "없습니다"),\n'
    + '    (r"일까$", "입니다"),\n'
    + '    (r"될까$", "됩니다"),\n'
    + '    (r"할까$", "합니다"),\n'
    + '    (r"올까$", "옵니다"),\n'
    + '    (r"갈까$", "갑니다"),\n'
)
TOPIC_HOOK_NEEDLE = '_TOPIC_OBSERVATION_REPAIRS = (\n'
TOPIC_HOOK_REPLACEMENT = (
    TOPIC_HOOK_NEEDLE
    + '    # SCRIPT_V2_RECOVERED_TOPIC_HOOK_V1\n'
    + '    (r"둥근$", "둥급니다"),\n'
)
FINAL_HOOK_NEEDLE = '    value = re.sub(r"^(?:그런데\\s+)?왜\\s+", "", _text(text)).rstrip().rstrip(".?!")\n'
FINAL_HOOK_REPLACEMENT = (
    FINAL_HOOK_NEEDLE
    + '    # SCRIPT_V2_FINAL_OBSERVABLE_HOOK_NORMALIZATION_V1\n'
    + '    # Remove an embedded interrogative marker before applying only the\n'
    + '    # already-approved terminal predicate repairs below. This preserves\n'
    + '    # the question presupposition as an observation without adding facts.\n'
    + '    value = re.sub(r"\\s+왜\\s+", " ", value)\n'
)
PLAIN_QUESTION_NEEDLE = '    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):\n'
PLAIN_QUESTION_REPLACEMENT = (
    '    # SCRIPT_V2_PLAIN_QUESTION_BOUNDARY_V1\n'
    + '    if "?" in hook or hook.endswith(("까", "까요", "나요", "어요", "예요")):\n'
)
GROUNDED_TOPIC_QUESTION_NEEDLE = (
    '    for pattern, replacement in _QUESTION_HOOK_REPAIRS:\n'
    '        converted, count = re.subn(pattern, replacement, value)\n'
    '        if count:\n'
    '            return converted + "."\n'
    '    return _topic_to_observation(topic)\n'
)
GROUNDED_TOPIC_QUESTION_REPLACEMENT = (
    '    for pattern, replacement in _QUESTION_HOOK_REPAIRS:\n'
    '        converted, count = re.subn(pattern, replacement, value)\n'
    '        if count:\n'
    '            return converted + "."\n'
    '    grounded = _topic_to_observation(topic)\n'
    '    if grounded:\n'
    '        return grounded\n'
    '    # SCRIPT_V2_GROUNDED_TOPIC_QUESTION_FALLBACK_V1\n'
    '    # If the approved candidate topic is itself a question, preserve only\n'
    '    # its observable presupposition using the same bounded repair table.\n'
    '    topic_value = re.sub(r"^(?:그런데\\s+)?왜\\s+", "", _text(topic)).rstrip().rstrip(".?!")\n'
    '    topic_value = re.sub(r"\\s+왜\\s+", " ", topic_value)\n'
    '    for pattern, replacement in _QUESTION_HOOK_REPAIRS:\n'
    '        converted, count = re.subn(pattern, replacement, topic_value)\n'
    '        if count:\n'
    '            return converted + "."\n'
    '    return ""\n'
)


def _patch_runner():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    changed = False
    if MARKER not in text:
        if text.count(NEEDLE) != 1:
            raise RuntimeError(
                "Script V2 formal-ending insertion marker mismatch: "
                f"{text.count(NEEDLE)}"
            )
        text = text.replace(NEEDLE, REPLACEMENT, 1)
        changed = True
    elif GENERAL_DECLARATIVE_MARKER not in text:
        insertion = '    (r"있나요(?=[?…]*$)", "있습니까"),\n'
        replacement = (
            insertion
            + '    # SCRIPT_V2_GENERAL_HANDA_FORMAL_ENDING_V1\n'
            + '    # Declarative-only terminal normalization. Deliberately excludes ? so\n'
            + '    # question contracts remain owned by the existing question repair path.\n'
            + '    (r"한다(?=[.!…]*$)", "합니다"),\n'
        )
        if text.count(insertion) != 1:
            raise RuntimeError(
                "Script V2 general formal-ending insertion marker mismatch: "
                f"{text.count(insertion)}"
            )
        text = text.replace(insertion, replacement, 1)
        changed = True
    if changed:
        RUNNER_PATH.write_text(text, encoding="utf-8")
    return changed


def _patch_engine():
    text = ENGINE_PATH.read_text(encoding="utf-8")
    changed = False
    if HOOK_MARKER not in text:
        if text.count(HOOK_NEEDLE) != 1:
            raise RuntimeError(
                "Script V2 recovered-hook insertion marker mismatch: "
                f"{text.count(HOOK_NEEDLE)}"
            )
        text = text.replace(HOOK_NEEDLE, HOOK_REPLACEMENT, 1)
        changed = True
    if TOPIC_HOOK_MARKER not in text:
        if text.count(TOPIC_HOOK_NEEDLE) != 1:
            raise RuntimeError(
                "Script V2 recovered-topic insertion marker mismatch: "
                f"{text.count(TOPIC_HOOK_NEEDLE)}"
            )
        text = text.replace(TOPIC_HOOK_NEEDLE, TOPIC_HOOK_REPLACEMENT, 1)
        changed = True
    if FINAL_HOOK_MARKER not in text:
        if text.count(FINAL_HOOK_NEEDLE) != 1:
            raise RuntimeError(
                "Script V2 final-hook normalization marker mismatch: "
                f"{text.count(FINAL_HOOK_NEEDLE)}"
            )
        text = text.replace(FINAL_HOOK_NEEDLE, FINAL_HOOK_REPLACEMENT, 1)
        changed = True
    if PLAIN_QUESTION_MARKER not in text:
        if text.count(PLAIN_QUESTION_NEEDLE) != 1:
            raise RuntimeError(
                "Script V2 plain-question boundary marker mismatch: "
                f"{text.count(PLAIN_QUESTION_NEEDLE)}"
            )
        text = text.replace(PLAIN_QUESTION_NEEDLE, PLAIN_QUESTION_REPLACEMENT, 1)
        changed = True
    if GROUNDED_TOPIC_QUESTION_MARKER not in text:
        if text.count(GROUNDED_TOPIC_QUESTION_NEEDLE) != 1:
            raise RuntimeError(
                "Script V2 grounded-topic question fallback marker mismatch: "
                f"{text.count(GROUNDED_TOPIC_QUESTION_NEEDLE)}"
            )
        text = text.replace(GROUNDED_TOPIC_QUESTION_NEEDLE, GROUNDED_TOPIC_QUESTION_REPLACEMENT, 1)
        changed = True
    if changed:
        ENGINE_PATH.write_text(text, encoding="utf-8")
    return changed


def main():
    runner_changed = _patch_runner()
    engine_changed = _patch_engine()
    if not runner_changed and not engine_changed:
        print("✅ Script V2 observed formal-ending + recovered-hook repairs already applied")
        return
    print("✅ Script V2 final observable Hook normalization + grounded topic-question fallback + formal repairs applied deterministically")


if __name__ == "__main__":
    main()
