from pathlib import Path

RUNNER_PATH = Path("content/script_engine_v2_runner.py")
ENGINE_PATH = Path("content/script_engine_v2.py")
MARKER = "# SCRIPT_V2_GUNGGEUM_FORMAL_ENDING_V1"
HOOK_MARKER = "# SCRIPT_V2_RECOVERED_QUESTION_HOOK_V1"
NEEDLE = '    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n'
REPLACEMENT = (
    NEEDLE
    + '    # SCRIPT_V2_GUNGGEUM_FORMAL_ENDING_V1\n'
    + '    (r"궁금해진다(?=[.!?…]*$)", "궁금해집니다"),\n'
    + '    (r"용이해진다(?=[.!?…]*$)", "용이해집니다"),\n'
    + '    (r"가능해진다(?=[.!?…]*$)", "가능해집니다"),\n'
    + '    (r"이루어진다(?=[.!?…]*$)", "이루어집니다"),\n'
    + '    (r"사실(?=[.!?…]*$)", "사실입니다"),\n'
    + '    (r"있나요(?=[?…]*$)", "있습니까"),\n'
)
HOOK_NEEDLE = '_QUESTION_HOOK_REPAIRS = (\n'
HOOK_REPLACEMENT = (
    HOOK_NEEDLE
    + '    # SCRIPT_V2_RECOVERED_QUESTION_HOOK_V1\n'
    + '    (r"둥근가$", "둥급니다"),\n'
    + '    (r"있을까$", "있습니다"),\n'
    + '    (r"없을까$", "없습니다"),\n'
    + '    (r"일까$", "입니다"),\n'
    + '    (r"될까$", "됩니다"),\n'
    + '    (r"할까$", "합니다"),\n'
    + '    (r"올까$", "옵니다"),\n'
    + '    (r"갈까$", "갑니다"),\n'
)


def _patch_runner():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if text.count(NEEDLE) != 1:
        raise RuntimeError(
            "Script V2 formal-ending insertion marker mismatch: "
            f"{text.count(NEEDLE)}"
        )
    RUNNER_PATH.write_text(text.replace(NEEDLE, REPLACEMENT, 1), encoding="utf-8")
    return True


def _patch_engine():
    text = ENGINE_PATH.read_text(encoding="utf-8")
    if HOOK_MARKER in text:
        return False
    if text.count(HOOK_NEEDLE) != 1:
        raise RuntimeError(
            "Script V2 recovered-hook insertion marker mismatch: "
            f"{text.count(HOOK_NEEDLE)}"
        )
    ENGINE_PATH.write_text(
        text.replace(HOOK_NEEDLE, HOOK_REPLACEMENT, 1),
        encoding="utf-8",
    )
    return True


def main():
    runner_changed = _patch_runner()
    engine_changed = _patch_engine()
    if not runner_changed and not engine_changed:
        print("✅ Script V2 observed formal-ending + recovered-hook repairs already applied")
        return
    print("✅ Script V2 observed formal endings + recovered question hooks repaired deterministically")


if __name__ == "__main__":
    main()
