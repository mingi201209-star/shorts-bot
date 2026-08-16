# quality/hard_validator.py

import re
from collections import Counter


# ============================================================
# Hard Validator V3
# ============================================================
#
# AI 판단 금지 영역.
#
# 책임:
#   - JSON/데이터 구조
#   - 필수 필드
#   - 장면 개수
#   - 빈 대사
#   - 설명형 오프닝
#   - keyword 형식
#   - keyword 반복
#   - 장면 중복
#   - 기본적인 데이터 이상
#
# 반환:
#
# {
#     "passed": True,
#     "errors": [],
#     "warnings": [],
#     "repair_hints": []
# }
#
# errors:
#     반드시 수정해야 함.
#
# warnings:
#     AI Judge가 추가 검토할 사항.
#
# ============================================================


MIN_SCENES = 12
MAX_SCENES = 13

MIN_KEYWORD_WORDS = 2
MAX_KEYWORD_WORDS = 5

MAX_IDENTICAL_KEYWORD_COUNT = 2

MIN_SCENE_TEXT_LENGTH = 8
MAX_SCENE_TEXT_LENGTH = 120


# ============================================================
# 금지 오프닝
# ============================================================

BANNED_OPENING_PATTERNS = [
    "오늘은",
    "이번 영상",
    "이번 영상에서는",
    "알아보겠습니다",
    "살펴보겠습니다",
    "설명하겠습니다",
    "소개하겠습니다",
    "보이는 모습",
    "있는 모습",
    "하는 모습",
    "장면입니다",
    "모습입니다",
]


# ============================================================
# 지나치게 추상적인 keyword
# ============================================================

GENERIC_KEYWORDS = {
    "science",
    "technology",
    "nature",
    "interesting",
    "amazing",
    "documentary",
    "background",
    "concept",
    "innovation",
    "future",
    "information",
    "education",
}


# ============================================================
# 유틸
# ============================================================

def normalize_text(text):

    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip().lower(),
    )


def contains_korean(text):

    return bool(
        re.search(
            r"[가-힣]",
            str(text or ""),
        )
    )


def add_error(
    result,
    message,
    repair_hint=None,
):

    result["errors"].append(
        message
    )

    if repair_hint:

        result["repair_hints"].append(
            repair_hint
        )


def add_warning(
    result,
    message,
):

    result["warnings"].append(
        message
    )


# ============================================================
# 기본 구조 검사
# ============================================================

def validate_root_structure(
    script_data,
    result,
):

    if not isinstance(
        script_data,
        dict,
    ):

        add_error(
            result,
            "script_data가 dict가 아닙니다.",
            "JSON 객체 형식으로 다시 생성합니다.",
        )

        return False

    required_fields = [
        "title",
        "topic",
        "scenes",
    ]

    for field in required_fields:

        if field not in script_data:

            add_error(
                result,
                f"필수 필드 누락: {field}",
                f"{field} 필드를 생성합니다.",
            )

    return True


# ============================================================
# 제목 / 소재 검사
# ============================================================

def validate_metadata(
    script_data,
    result,
):

    title = normalize_text(
        script_data.get(
            "title",
            "",
        )
    )

    topic = normalize_text(
        script_data.get(
            "topic",
            "",
        )
    )

    if not title:

        add_error(
            result,
            "title이 비어 있습니다.",
            "영상 제목을 생성합니다.",
        )

    if not topic:

        add_error(
            result,
            "topic이 비어 있습니다.",
            "구체적인 실제 소재를 생성합니다.",
        )

    if title and len(title) > 100:

        add_warning(
            result,
            "title이 지나치게 깁니다.",
        )

    if topic and len(topic) > 150:

        add_warning(
            result,
            "topic이 지나치게 깁니다.",
        )


# ============================================================
# 첫 장면 검사
# ============================================================

def validate_opening(
    scenes,
    result,
):

    if not scenes:
        return

    first_scene = scenes[0]

    if not isinstance(
        first_scene,
        dict,
    ):
        return

    first_text = normalize_text(
        first_scene.get(
            "text",
            "",
        )
    )

    if not first_text:
        return

    for pattern in BANNED_OPENING_PATTERNS:

        if pattern in first_text:

            add_error(
                result,
                (
                    "설명형 오프닝 금지 표현 발견: "
                    f"'{pattern}'"
                ),
                (
                    "첫 장면을 장면 설명이 아니라 "
                    "질문, 반전, 위험, 이상 현상 또는 "
                    "즉시 궁금증을 만드는 문장으로 다시 작성합니다."
                ),
            )

            break


# ============================================================
# keyword 검사
# ============================================================

def validate_keyword(
    keyword,
    scene_number,
    result,
):

    keyword = normalize_text(
        keyword
    )

    if not keyword:

        add_error(
            result,
            f"{scene_number}번 장면 keyword 없음.",
            (
                f"{scene_number}번 장면에 "
                "구체적인 영어 시각 검색어를 생성합니다."
            ),
        )

        return

    if contains_korean(
        keyword
    ):

        add_error(
            result,
            (
                f"{scene_number}번 장면 keyword에 "
                "한글이 포함되어 있습니다."
            ),
            (
                f"{scene_number}번 keyword를 "
                "영어 검색어로 변경합니다."
            ),
        )

    words = keyword.split()

    if len(words) < MIN_KEYWORD_WORDS:

        add_error(
            result,
            (
                f"{scene_number}번 keyword가 "
                "너무 짧습니다: "
                f"{len(words)}단어"
            ),
            (
                "대상 + 상황이 드러나는 "
                "2~5단어 검색어로 변경합니다."
            ),
        )

    if len(words) > MAX_KEYWORD_WORDS:

        add_error(
            result,
            (
                f"{scene_number}번 keyword가 "
                "너무 깁니다: "
                f"{len(words)}단어"
            ),
            (
                "핵심 시각 요소만 남겨 "
                "2~5단어로 줄입니다."
            ),
        )

    meaningful_words = [
        word
        for word in words
        if word not in GENERIC_KEYWORDS
    ]

    if (
        words
        and len(meaningful_words) < 2
    ):

        add_error(
            result,
            (
                f"{scene_number}번 keyword가 "
                "지나치게 추상적입니다: "
                f"'{keyword}'"
            ),
            (
                "실제로 카메라에 찍힐 수 있는 "
                "대상과 상황 중심 검색어로 변경합니다."
            ),
        )


# ============================================================
# 장면 검사
# ============================================================

def validate_scenes(
    script_data,
    result,
):

    scenes = script_data.get(
        "scenes",
        [],
    )

    if not isinstance(
        scenes,
        list,
    ):

        add_error(
            result,
            "scenes가 list가 아닙니다.",
            "scenes를 JSON 배열로 다시 생성합니다.",
        )

        return []

    scene_count = len(
        scenes
    )

    if scene_count < MIN_SCENES:

        add_error(
            result,
            (
                f"장면 수 부족: "
                f"{scene_count}개"
            ),
            (
                f"장면을 최소 "
                f"{MIN_SCENES}개까지 늘립니다."
            ),
        )

    elif scene_count > MAX_SCENES:

        add_error(
            result,
            (
                f"장면 수 초과: "
                f"{scene_count}개"
            ),
            (
                f"장면을 최대 "
                f"{MAX_SCENES}개로 줄입니다."
            ),
        )

    for idx, scene in enumerate(
        scenes,
    ):

        number = idx + 1

        if not isinstance(
            scene,
            dict,
        ):

            add_error(
                result,
                (
                    f"{number}번 장면이 "
                    "dict가 아닙니다."
                ),
                (
                    f"{number}번 장면을 "
                    "text/keyword를 가진 객체로 "
                    "다시 생성합니다."
                ),
            )

            continue

        text = normalize_text(
            scene.get(
                "text",
                "",
            )
        )

        keyword = scene.get(
            "keyword",
            "",
        )

        if not text:

            add_error(
                result,
                (
                    f"{number}번 장면 "
                    "text가 비어 있습니다."
                ),
                (
                    f"{number}번 장면의 "
                    "내레이션을 생성합니다."
                ),
            )

        elif len(text) < MIN_SCENE_TEXT_LENGTH:

            add_warning(
                result,
                (
                    f"{number}번 장면 대사가 "
                    f"매우 짧습니다: {len(text)}자"
                ),
            )

        elif len(text) > MAX_SCENE_TEXT_LENGTH:

            add_warning(
                result,
                (
                    f"{number}번 장면 대사가 "
                    f"매우 깁니다: {len(text)}자"
                ),
            )

        validate_keyword(
            keyword,
            number,
            result,
        )

    return scenes


# ============================================================
# keyword 반복 검사
# ============================================================

def validate_keyword_repetition(
    scenes,
    result,
):

    keywords = []

    for scene in scenes:

        if not isinstance(
            scene,
            dict,
        ):
            continue

        keyword = normalize_text(
            scene.get(
                "keyword",
                "",
            )
        )

        if keyword:
            keywords.append(
                keyword
            )

    counts = Counter(
        keywords
    )

    for keyword, count in counts.items():

        if count > MAX_IDENTICAL_KEYWORD_COUNT:

            add_error(
                result,
                (
                    "동일 keyword 과다 반복: "
                    f"'{keyword}' = {count}회"
                ),
                (
                    "각 장면의 시각적 목적에 맞게 "
                    "서로 다른 검색어로 분리합니다."
                ),
            )


# ============================================================
# 대사 완전 중복 검사
# ============================================================

def validate_text_repetition(
    scenes,
    result,
):

    texts = []

    for scene in scenes:

        if not isinstance(
            scene,
            dict,
        ):
            continue

        text = normalize_text(
            scene.get(
                "text",
                "",
            )
        )

        if text:
            texts.append(
                text
            )

    counts = Counter(
        texts
    )

    for text, count in counts.items():

        if count > 1:

            preview = text[:40]

            add_error(
                result,
                (
                    "동일 장면 대사 반복 발견: "
                    f"'{preview}...' "
                    f"({count}회)"
                ),
                "중복 장면을 서로 다른 정보로 다시 작성합니다.",
            )


# ============================================================
# 전체 Hard Validation
# ============================================================

def validate_script_hard(
    script_data,
):

    result = {
        "passed": False,
        "errors": [],
        "warnings": [],
        "repair_hints": [],
    }

    root_ok = (
        validate_root_structure(
            script_data,
            result,
        )
    )

    if not root_ok:

        return result

    validate_metadata(
        script_data,
        result,
    )

    scenes = validate_scenes(
        script_data,
        result,
    )

    validate_opening(
        scenes,
        result,
    )

    validate_keyword_repetition(
        scenes,
        result,
    )

    validate_text_repetition(
        scenes,
        result,
    )

    # 중복 repair hint 제거
    result["repair_hints"] = list(
        dict.fromkeys(
            result["repair_hints"]
        )
    )

    result["passed"] = (
        len(result["errors"]) == 0
    )

    return result


# ============================================================
# 로그 출력
# ============================================================

def print_hard_validation_report(
    report,
):

    print("")
    print("=" * 52)
    print(
        "🛡️ V3 HARD VALIDATOR"
    )
    print("=" * 52)

    if report.get(
        "passed"
    ):

        print(
            "✅ HARD VALIDATION PASSED"
        )

    else:

        print(
            "❌ HARD VALIDATION FAILED"
        )

    errors = report.get(
        "errors",
        [],
    )

    if errors:

        print("")
        print(
            "🚫 ERRORS"
        )

        for error in errors:

            print(
                f" - {error}"
            )

    warnings = report.get(
        "warnings",
        [],
    )

    if warnings:

        print("")
        print(
            "⚠️ WARNINGS"
        )

        for warning in warnings:

            print(
                f" - {warning}"
            )

    repair_hints = report.get(
        "repair_hints",
        [],
    )

    if repair_hints:

        print("")
        print(
            "🔧 REPAIR HINTS"
        )

        for hint in repair_hints:

            print(
                f" - {hint}"
            )

    print("=" * 52)
