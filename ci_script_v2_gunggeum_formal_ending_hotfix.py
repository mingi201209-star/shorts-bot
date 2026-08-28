from pathlib import Path
import re

RUNNER_PATH = Path("content/script_engine_v2_runner.py")
ENGINE_PATH = Path("content/script_engine_v2.py")
MARKER = "# SCRIPT_FORMAL_ENDING_PRODUCTION_CORPUS_V1"
LOCKED_PARITY_MARKER = "# SCRIPT_FORMAL_ENDING_LOCKED_PARITY_V1"
HOOK_MARKER = "# SCRIPT_V2_RECOVERED_QUESTION_HOOK_V1"
TOPIC_HOOK_MARKER = "# SCRIPT_V2_RECOVERED_TOPIC_HOOK_V1"
FINAL_HOOK_MARKER = "# SCRIPT_V2_FINAL_OBSERVABLE_HOOK_NORMALIZATION_V1"
PLAIN_QUESTION_MARKER = "# SCRIPT_V2_PLAIN_QUESTION_BOUNDARY_V1"
GROUNDED_TOPIC_QUESTION_MARKER = "# SCRIPT_V2_GROUNDED_TOPIC_QUESTION_FALLBACK_V1"


def _ensure_shared_import(text: str) -> tuple[str, bool]:
    import_line = "from content.script_formal_endings import formalize_declarative_text\n"
    if import_line in text:
        return text, False
    needle = "import re\n"
    if text.count(needle) < 1:
        raise RuntimeError("Script formal corpus import marker missing")
    return text.replace(needle, needle + import_line, 1), True


def _patch_runner():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    changed = False
    text, imported = _ensure_shared_import(text)
    changed = changed or imported

    if MARKER not in text:
        pattern = re.compile(
            r"def _formalize_common_ending\(text: Any\) -> str:\n.*?(?=\ndef _deterministic_keyword)",
            flags=re.DOTALL,
        )
        replacement = (
            "def _formalize_common_ending(text: Any) -> str:\n"
            "    # SCRIPT_FORMAL_ENDING_PRODUCTION_CORPUS_V1\n"
            "    # Shared deterministic terminal normalization for unlocked/final text.\n"
            "    return formalize_declarative_text(text)\n"
        )
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise RuntimeError(
                f"Script formal corpus runner function marker mismatch: {count}"
            )
        changed = True

    if changed:
        RUNNER_PATH.write_text(text, encoding="utf-8")
    return changed


def _patch_engine():
    text = ENGINE_PATH.read_text(encoding="utf-8")
    changed = False
    text, imported = _ensure_shared_import(text)
    changed = changed or imported

    if LOCKED_PARITY_MARKER not in text:
        pattern = re.compile(
            r"def deterministic_scene_repair\(text: str, role: str\) -> str:\n.*?(?=\ndef repair_failed_scenes)",
            flags=re.DOTALL,
        )
        replacement = (
            "def deterministic_scene_repair(text: str, role: str) -> str:\n"
            "    # SCRIPT_FORMAL_ENDING_LOCKED_PARITY_V1\n"
            "    # LOCK preserves factual/semantic content, not invalid speech style.\n"
            "    value = formalize_declarative_text(_text(text))\n"
            "    if role == \"causal_clue\" and value and not any(\n"
            "        token in value for token in CAUSAL_CLUE_TOKENS\n"
            "    ):\n"
            "        value = \"원인의 첫 단서는 \" + value\n"
            "    return value\n"
        )
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise RuntimeError(
                f"Script formal corpus engine function marker mismatch: {count}"
            )
        changed = True

    hook_needle = "_QUESTION_HOOK_REPAIRS = (\n"
    if HOOK_MARKER not in text:
        replacement = (
            hook_needle
            + "    # SCRIPT_V2_RECOVERED_QUESTION_HOOK_V1\n"
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
        if text.count(hook_needle) != 1:
            raise RuntimeError("Script V2 hook insertion marker mismatch")
        text = text.replace(hook_needle, replacement, 1)
        changed = True

    topic_needle = "_TOPIC_OBSERVATION_REPAIRS = (\n"
    if TOPIC_HOOK_MARKER not in text:
        replacement = (
            topic_needle
            + "    # SCRIPT_V2_RECOVERED_TOPIC_HOOK_V1\n"
            + '    (r"둥근$", "둥급니다"),\n'
        )
        if text.count(topic_needle) != 1:
            raise RuntimeError("Script V2 topic insertion marker mismatch")
        text = text.replace(topic_needle, replacement, 1)
        changed = True

    final_needle = '    value = re.sub(r"^(?:그런데\\s+)?왜\\s+", "", _text(text)).rstrip().rstrip(".?!")\n'
    if FINAL_HOOK_MARKER not in text:
        replacement = (
            final_needle
            + "    # SCRIPT_V2_FINAL_OBSERVABLE_HOOK_NORMALIZATION_V1\n"
            + '    value = re.sub(r"\\s+왜\\s+", " ", value)\n'
        )
        if text.count(final_needle) != 1:
            raise RuntimeError("Script V2 final-hook marker mismatch")
        text = text.replace(final_needle, replacement, 1)
        changed = True

    plain_needle = '    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):\n'
    if PLAIN_QUESTION_MARKER not in text:
        replacement = (
            "    # SCRIPT_V2_PLAIN_QUESTION_BOUNDARY_V1\n"
            + '    if "?" in hook or hook.endswith(("까", "까요", "나요", "어요", "예요")):\n'
        )
        if text.count(plain_needle) != 1:
            raise RuntimeError("Script V2 plain-question marker mismatch")
        text = text.replace(plain_needle, replacement, 1)
        changed = True

    grounded_needle = (
        '    for pattern, replacement in _QUESTION_HOOK_REPAIRS:\n'
        '        converted, count = re.subn(pattern, replacement, value)\n'
        '        if count:\n'
        '            return converted + "."\n'
        '    return _topic_to_observation(topic)\n'
    )
    if GROUNDED_TOPIC_QUESTION_MARKER not in text and grounded_needle in text:
        replacement = (
            '    for pattern, replacement in _QUESTION_HOOK_REPAIRS:\n'
            '        converted, count = re.subn(pattern, replacement, value)\n'
            '        if count:\n'
            '            return converted + "."\n'
            '    grounded = _topic_to_observation(topic)\n'
            '    if grounded:\n'
            '        return grounded\n'
            '    # SCRIPT_V2_GROUNDED_TOPIC_QUESTION_FALLBACK_V1\n'
            '    topic_value = re.sub(r"^(?:그런데\\s+)?왜\\s+", "", _text(topic)).rstrip().rstrip(".?!")\n'
            '    topic_value = re.sub(r"\\s+왜\\s+", " ", topic_value)\n'
            '    for pattern, replacement in _QUESTION_HOOK_REPAIRS:\n'
            '        converted, count = re.subn(pattern, replacement, topic_value)\n'
            '        if count:\n'
            '            return converted + "."\n'
            '    return ""\n'
        )
        text = text.replace(grounded_needle, replacement, 1)
        changed = True

    if changed:
        ENGINE_PATH.write_text(text, encoding="utf-8")
    return changed


def main():
    runner_changed = _patch_runner()
    engine_changed = _patch_engine()
    if not runner_changed and not engine_changed:
        print("✅ Script formal-ending production corpus already installed")
        return
    print("✅ Script Formal-Ending Production Corpus V1 installed")


if __name__ == "__main__":
    main()
