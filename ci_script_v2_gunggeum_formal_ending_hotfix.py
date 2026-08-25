from pathlib import Path

RUNNER_PATH = Path("content/script_engine_v2_runner.py")
MARKER = "# SCRIPT_V2_GUNGGEUM_FORMAL_ENDING_V1"
NEEDLE = '    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n'
REPLACEMENT = (
    NEEDLE
    + '    # SCRIPT_V2_GUNGGEUM_FORMAL_ENDING_V1\n'
    + '    (r"궁금해진다(?=[.!?…]*$)", "궁금해집니다"),\n'
    + '    (r"용이해진다(?=[.!?…]*$)", "용이해집니다"),\n'
    + '    (r"가능해진다(?=[.!?…]*$)", "가능해집니다"),\n'
    + '    (r"이루어진다(?=[.!?…]*$)", "이루어집니다"),\n'
    + '    (r"사실(?=[.!?…]*$)", "사실입니다"),\n'
)


def main():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Script V2 observed formal-ending repairs already applied")
        return
    if text.count(NEEDLE) != 1:
        raise RuntimeError(
            "Script V2 formal-ending insertion marker mismatch: "
            f"{text.count(NEEDLE)}"
        )
    RUNNER_PATH.write_text(text.replace(NEEDLE, REPLACEMENT, 1), encoding="utf-8")
    print("✅ Script V2 observed formal endings repaired deterministically")


if __name__ == "__main__":
    main()
