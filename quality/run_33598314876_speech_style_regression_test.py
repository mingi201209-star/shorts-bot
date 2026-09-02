"""Exact speech-style counterexample from production Run 33598314876."""
from pathlib import Path

from content.script_formal_endings import formalize_script_text
from quality.korean_speech_style import validate_korean_speech_text, validate_script_speech_style


RUN_COUNTEREXAMPLE = "제트 엔진 노즐의 끝부분에 있는 치프론을 주목해 보세요."
EXPECTED = "제트 엔진 노즐의 끝부분에 있는 치프론을 확인할 수 있습니다."


def _normalize_narration(text: str) -> str:
    """Production shared deterministic formal-ending boundary."""
    return formalize_script_text(text)


def _assert_formal(text: str) -> None:
    valid, reason = validate_korean_speech_text(text)
    assert valid, reason


def main() -> None:
    # RUN_33598314876_COUNTEREXAMPLE: raw Writer/locked narration -> shared
    # deterministic normalization -> the same hard speech-style validator.
    normalized = _normalize_narration(RUN_COUNTEREXAMPLE)
    assert normalized == EXPECTED
    assert "보세요" not in normalized
    assert "제트 엔진" in normalized
    assert "노즐" in normalized
    assert "치프론" in normalized
    for unsupported in ("항력", "연료", "안정", "추력", "성능"):
        assert unsupported not in normalized
    _assert_formal(normalized)
    valid_script, reason = validate_script_speech_style(
        {"scenes": [{"text": normalized, "role": "phenomenon"}]}
    )
    assert valid_script, reason

    # CASE 1: narrow terminal visual-attention request is formalized.
    case1 = _normalize_narration("치프론을 주목해 보세요.")
    assert case1 == "치프론을 확인할 수 있습니다."
    _assert_formal(case1)

    # CASE 2: another visual-attention request preserves its object/meaning.
    case2 = _normalize_narration("이 장면을 한번 봐 주세요.")
    assert case2 == "이 장면을 확인할 수 있습니다."
    _assert_formal(case2)

    # CASE 3: already-formal narration is unchanged.
    already_formal = "치프론은 노즐 끝부분에 있습니다."
    assert _normalize_narration(already_formal) == already_formal

    # CASE 4: approved curiosity-question contract is not flattened.
    question = "왜 이런 모양일까요?"
    assert _normalize_narration(question) == question
    _assert_formal(question)

    # CASE 5: quoted dialogue/literal text is not rewritten.
    quoted = '정비사가 "치프론을 보세요"라고 말했습니다.'
    assert _normalize_narration(quoted) == quoted

    # CASE 6: metadata is not passed through narration normalization.
    metadata = {"cta": "구독해주세요", "visual_goal": "치프론을 보세요"}
    untouched_metadata = dict(metadata)
    _ = _normalize_narration("치프론은 노즐 끝부분에 있습니다.")
    assert metadata == untouched_metadata

    # CASE 7: unrelated polite forms are neither deleted nor converted to banmal.
    generic = "이 설명은 좋아요."
    assert _normalize_narration(generic) == generic
    valid_generic, _ = validate_korean_speech_text(generic)
    assert not valid_generic, "#237 must still reject unrelated 해요체"

    # Narrow ~해주세요 support only for visual-attention verbs.
    attention_request = _normalize_narration("치프론을 확인해 주세요.")
    assert attention_request == "치프론을 확인할 수 있습니다."
    _assert_formal(attention_request)
    unrelated_request = "원리를 설명해주세요."
    assert _normalize_narration(unrelated_request) == unrelated_request
    valid_unrelated, _ = validate_korean_speech_text(unrelated_request)
    assert not valid_unrelated, "arbitrary requests must fail closed"

    # CASE 8: subject/claim-loss guard.
    for token in ("제트 엔진", "노즐", "치프론"):
        assert token in normalized

    # Production composition invariants: #264 still installs the shared
    # deterministic corpus for locked/unlocked Script V2 paths, with no
    # call/retry expansion.
    hotfix_source = Path("ci_script_v2_gunggeum_formal_ending_hotfix.py").read_text(encoding="utf-8")
    engine_source = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
    assert "from content.script_formal_endings import formalize_script_text" in hotfix_source
    assert "return formalize_script_text(text)" in hotfix_source
    assert "from content.script_formal_endings import formalize_declarative_text" in hotfix_source
    assert "return formalize_declarative_text(value)" in hotfix_source
    assert "MAX_SCRIPT_API_CALLS = 3" in engine_source
    assert "MAX_LOCAL_REPAIR_CALLS = 2" in engine_source

    print("RUN 33598314876 SPEECH STYLE REGRESSION: PASS")


if __name__ == "__main__":
    main()
