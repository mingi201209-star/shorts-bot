import re


POLITE_ENDINGS = (
    "요",
    "죠",
    "니다",
    "니까",
    "세요",
    "십시오",
)

# Hook에서만 허용하는 자연스러운 제목형/명사형 끝맺음.
# 실제 narration Scene에는 적용하지 않는다.
HOOK_NOMINAL_ENDINGS = (
    "이유",
    "비밀",
    "원리",
    "방법",
    "구조",
    "차이",
    "정체",
    "현상",
    "설계",
    "장치",
    "전략",
    "순간",
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")
KOREAN_RE = re.compile(r"[가-힣]")


def _clean_sentence(text):
    return str(text or "").strip().strip('"\'“”‘’()[]{}<>').strip()


def _terminal(text):
    return _clean_sentence(text).rstrip(" .!?…~")


def _is_nominal_hook(text):
    terminal = _terminal(text)
    return bool(terminal) and terminal.endswith(HOOK_NOMINAL_ENDINGS)


def validate_korean_speech_text(text, *, allow_nominal=False):
    raw = str(text or "").strip()
    if not raw:
        return False, "대사가 비어 있습니다."

    sentences = [
        _clean_sentence(part)
        for part in SENTENCE_SPLIT_RE.split(raw)
        if _clean_sentence(part)
    ]
    if not sentences:
        sentences = [_clean_sentence(raw)]

    for sentence in sentences:
        if not KOREAN_RE.search(sentence):
            continue

        terminal = _terminal(sentence)
        if not terminal:
            continue

        if terminal.endswith(POLITE_ENDINGS):
            continue

        if allow_nominal and _is_nominal_hook(sentence):
            continue

        return False, f"비격식/비존댓말 종결 감지: {sentence}"

    return True, "자연스러운 한국어 존댓말 종결"


def validate_scenes_speech_style(scenes):
    if not isinstance(scenes, list):
        return False, "scenes가 배열이 아닙니다."

    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            return False, f"{index}번 scene이 객체가 아닙니다."

        valid, reason = validate_korean_speech_text(
            scene.get("text", ""),
            allow_nominal=False,
        )
        if not valid:
            return False, f"{index}번 Scene speech-style 실패: {reason}"

    return True, "전체 narration 존댓말 검사 통과"


def validate_script_speech_style(script_data):
    if not isinstance(script_data, dict):
        return False, "script_data가 객체가 아닙니다."
    return validate_scenes_speech_style(script_data.get("scenes", []))
