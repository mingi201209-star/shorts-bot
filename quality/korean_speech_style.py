import re


# Production narration uses formal polite Korean (하십시오체). Casual polite
# 해요체 is deliberately excluded so a script cannot mix "~습니다" and "~요".
FORMAL_ENDINGS = (
    "니다",
    "니까",
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

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s*")
KOREAN_RE = re.compile(r"[가-힣]")
CASUAL_POLITE_RE = re.compile(
    r"(?:해요|돼요|되어요|이에요|예요|거예요|것이에요|나요|군요|네요|죠|세요|요)$"
)

# Speech-style validation is about finite sentence endings. A short title-like,
# nominal, or rhetorical fragment has no finite predicate ending to classify as
# 하십시오체 vs 반말. Keep common informal finite endings explicit so allowing
# fragments cannot admit ordinary plain declarative/imperative/question forms.
INFORMAL_FINITE_RE = re.compile(
    r"(?:한다|된다|인다|진다|간다|온다|난다|준다|둔다|본다|쓴다|"
    r"찾는다|줄인다|줄어든다|낮아진다|펼쳐진다|돌아간다|"
    r"있다|없다|같다|이다|아니다|한다|했다|됐다|된다|"
    r"일까|인가|는가|냐|니|자|라)$"
)


def _clean_sentence(text):
    return str(text or "").strip().strip('\"\'“”‘’()[]{}<>').strip()


def _terminal(text):
    return _clean_sentence(text).rstrip(" .!?…~")


def _is_nominal_hook(text):
    terminal = _terminal(text)
    return bool(terminal) and terminal.endswith(HOOK_NOMINAL_ENDINGS)


def _is_nonfinite_fragment(sentence):
    """Return True only when there is no finite speech-style ending to judge."""
    cleaned = _clean_sentence(sentence)
    terminal = _terminal(cleaned)
    if not terminal:
        return False

    if terminal.endswith(FORMAL_ENDINGS) or CASUAL_POLITE_RE.search(terminal):
        return False
    if INFORMAL_FINITE_RE.search(terminal):
        return False

    # Non-formal questions are still finite utterances, not fragments.
    if cleaned.rstrip().endswith("?"):
        return False

    # Any remaining terminal ending in plain-declarative ~다 is conservatively
    # treated as finite. This protects unseen 반말 predicates without a broad
    # morphology rewrite; fragments such as "..., 과연." do not end this way.
    if terminal.endswith("다"):
        return False

    return True


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

        # Natural formal curiosity questions such as "왜 꺾여 있을까요?" are
        # an explicit part of the narration contract. Check this before the
        # generic trailing-요 detector so ~까요 is not mistaken for 해요체.
        if terminal.endswith("까요"):
            continue

        # All other casual-polite 해요체 endings remain prohibited.
        if CASUAL_POLITE_RE.search(terminal):
            return False, f"해요체 종결 감지: {sentence}"

        if terminal.endswith(FORMAL_ENDINGS):
            continue

        if allow_nominal and _is_nominal_hook(sentence):
            continue

        # A fragment has no finite predicate ending, so there is no speech-style
        # ending to reject. This is distinct from allowing an informal sentence.
        if _is_nonfinite_fragment(sentence):
            continue

        return False, f"격식체(하십시오체) 이외 종결 감지: {sentence}"

    return True, "격식체 한국어 narration 종결"


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

    return True, "전체 narration 격식체 검사 통과"


def validate_script_speech_style(script_data):
    if not isinstance(script_data, dict):
        return False, "script_data가 객체가 아닙니다."
    return validate_scenes_speech_style(script_data.get("scenes", []))
