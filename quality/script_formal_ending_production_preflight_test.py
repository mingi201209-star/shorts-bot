"""Deterministic Script production preflight for final speech-style contracts."""
from quality.script_formal_ending_production_corpus_regression_test import run_after_corpus
from quality.korean_speech_style import validate_korean_speech_text


def main():
    run_after_corpus()
    for text in (
        "유도항력이 감소합니다.",
        "왜 비행기 날개 끝이 위로 꺾여 있을까요?",
    ):
        ok, reason = validate_korean_speech_text(text, allow_nominal=False)
        assert ok, (text, reason)
    print("SCRIPT PRODUCTION PREFLIGHT V1: PASS")


if __name__ == "__main__":
    main()
