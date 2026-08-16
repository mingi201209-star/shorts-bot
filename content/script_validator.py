# content/script_validator.py

import re


# ============================================================
# Script Validator V3
# ============================================================
#
# 책임:
#   1. 소재 신선도 검사
#   2. 대중성 검사
#   3. 첫 3초 후킹 검사
#   4. 설명조 오프닝 차단
#   5. 장면 구조 검사
#   6. 검색어 품질 검사
#   7. 개선 피드백 생성
#
# 핵심:
#
#   PASS / FAIL만 반환하지 않는다.
#
#   "왜 실패했는가?"
#   "무엇을 고쳐야 하는가?"
#
#   를 같이 반환한다.
#
# ============================================================


# ============================================================
# 기준값
# ============================================================

MIN_NOVELTY_SCORE = 7
MIN_TRAFFIC_SCORE = 7
MIN_HOOK_SCORE = 8

MIN_SCENES = 12
MAX_SCENES = 13


# ============================================================
# 금지 오프닝
# ============================================================

BANNED_OPENINGS = [
    "오늘은",
    "이번 영상에서는",
    "알아보겠습니다",
    "설명하겠습니다",
    "살펴보겠습니다",
    "있는 모습",
    "하는 모습",
    "보이는 모습",
    "장면입니다",
    "모습입니다",
    "라고 합니다",
]


# ============================================================
# Hook 신호
# ============================================================

HOOK_SIGNALS = [
    "왜",
    "사실",
    "그런데",
    "진짜 이유",
    "비밀",
    "위험",
    "절대",
    "의외",
    "놀랍게도",
    "생각과 다",
    "숨겨",
    "반대",
    "몰랐",
]


# ============================================================
# 대중성 신호
# ============================================================

TRAFFIC_SIGNALS = [
    "왜",
    "위험",
    "비밀",
    "진짜 이유",
    "의외",
    "충격",
    "숨겨",
    "몰랐",
    "이상",
    "반전",
]


# ============================================================
# 너무 흔한 소재
# ============================================================

COMMON_KNOWLEDGE = [
    "지구는 둥글",
    "태양은 동쪽",
    "물은 100도",
    "하늘은 파란",
    "식물은 광합성",
    "사람은 산소",
    "비는 구름",
    "번개는 전기",
    "무지개는 빛",
]


# ============================================================
# 추상적인 영상 검색어
# ============================================================

GENERIC_VISUAL_WORDS = {
    "science",
    "technology",
    "nature",
    "interesting",
    "amazing",
    "background",
    "concept",
    "documentary",
    "future",
    "innovation",
}


# ============================================================
# 소재 상식성 검사
# ============================================================

def is_too_common(topic):

    topic = str(
        topic or ""
    ).replace(
        " ",
        ""
    ).lower()

    if not topic:
        return True

    for item in COMMON_KNOWLEDGE:

        normalized = item.replace(
            " ",
            ""
        ).lower()

        if normalized in topic:
            return True

    return False


# ============================================================
# 첫 장면 Hook 점수
# ============================================================

def score_hook(text):

    text = str(
        text or ""
    ).strip()

    if not text:
        return 0

    # 설명조 시작이면 강한 감점
    for banned in BANNED_OPENINGS:

        if banned in text:
            return 1

    score = 2

    for signal in HOOK_SIGNALS:

        if signal in text:
            score += 2

    if "?" in text:
        score += 2

    # 너무 긴 첫 문장은 훅이 흐려질 가능성
    if len(text) > 45:
        score -= 1

    # 너무 짧아 의미가 없는 경우
    if len(text) < 8:
        score -= 2

    return max(
        0,
        min(
            score,
            10,
        )
    )


# ============================================================
# Traffic 점수
# ============================================================

def score_traffic(
    title,
    topic,
    first_scene_text,
):

    combined = " ".join([
        str(title or ""),
        str(topic or ""),
        str(first_scene_text or ""),
    ])

    score = 3

    for signal in TRAFFIC_SIGNALS:

        if signal in combined:
            score += 1

    if "?" in combined:
        score += 1

    return max(
        0,
        min(
            score,
            10,
        )
    )


# ============================================================
# 검색어 검사
# ============================================================

def validate_visual_keyword(keyword):

    keyword = str(
        keyword or ""
    ).strip().lower()

    if not keyword:

        return False, (
            "검색어가 비어 있음"
        )

    if re.search(
        r"[가-힣]",
        keyword,
    ):

        return False, (
            "검색어에 한글 포함"
        )

    words = keyword.split()

    if len(words) < 2:

        return False, (
            "검색어가 너무 짧음"
        )

    if len(words) > 6:

        return False, (
            "검색어가 너무 김"
        )

    meaningful = [
        word
        for word in words
        if word not in GENERIC_VISUAL_WORDS
    ]

    if len(meaningful) < 2:

        return False, (
            "검색어가 지나치게 추상적"
        )

    return True, "통과"


# ============================================================
# 장면 검사
# ============================================================

def validate_scenes(scenes):

    problems = []

    if not isinstance(
        scenes,
        list,
    ):

        return [
            "scenes가 배열이 아님"
        ]

    if len(scenes) < MIN_SCENES:

        problems.append(
            f"장면 수 부족: {len(scenes)}"
        )

    if len(scenes) > MAX_SCENES:

        problems.append(
            f"장면 수 초과: {len(scenes)}"
        )

    keywords = []

    for idx, scene in enumerate(
        scenes,
    ):

        if not isinstance(
            scene,
            dict,
        ):

            problems.append(
                f"{idx + 1}번 장면 형식 오류"
            )

            continue

        text = str(
            scene.get(
                "text",
                "",
            )
        ).strip()

        keyword = str(
            scene.get(
                "keyword",
                "",
            )
        ).strip()

        if not text:

            problems.append(
                f"{idx + 1}번 장면 대사 없음"
            )

        valid_keyword, reason = (
            validate_visual_keyword(
                keyword
            )
        )

        if not valid_keyword:

            problems.append(
                f"{idx + 1}번 장면 검색어 실패: "
                f"{reason}"
            )

        if keyword:
            keywords.append(
                keyword.lower()
            )

    # --------------------------------------------------------
    # 검색어 반복
    # --------------------------------------------------------

    duplicate_count = (
        len(keywords)
        - len(set(keywords))
    )

    if duplicate_count >= 4:

        problems.append(
            "동일/유사 검색어 반복이 너무 많음"
        )

    return problems


# ============================================================
# V3 전체 검증
# ============================================================

def validate_script(
    script_data,
):

    """
    반환 형식:

    {
        "passed": True/False,

        "scores": {
            "novelty": 8,
            "traffic": 8,
            "hook": 9
        },

        "problems": [],

        "rewrite_instructions": []
    }
    """

    problems = []
    rewrite_instructions = []

    if not isinstance(
        script_data,
        dict,
    ):

        return {
            "passed": False,

            "scores": {
                "novelty": 0,
                "traffic": 0,
                "hook": 0,
            },

            "problems": [
                "script_data가 dict가 아님"
            ],

            "rewrite_instructions": [
                "JSON 객체 형식으로 다시 생성한다."
            ],
        }

    title = str(
        script_data.get(
            "title",
            "",
        )
    ).strip()

    topic = str(
        script_data.get(
            "topic",
            "",
        )
    ).strip()

    scenes = script_data.get(
        "scenes",
        [],
    )

    novelty = script_data.get(
        "novelty_score",
        0,
    )

    try:

        novelty = int(
            novelty
        )

    except Exception:

        novelty = 0

    # ========================================================
    # 기본 필드
    # ========================================================

    if not title:

        problems.append(
            "제목 없음"
        )

        rewrite_instructions.append(
            "호기심을 만드는 제목을 추가한다."
        )

    if not topic:

        problems.append(
            "구체적인 소재 없음"
        )

        rewrite_instructions.append(
            "큰 주제가 아니라 하나의 구체적인 실제 소재로 좁힌다."
        )

    # ========================================================
    # 너무 흔한 소재
    # ========================================================

    if is_too_common(
        topic
    ):

        problems.append(
            "대부분 이미 아는 소재"
        )

        rewrite_instructions.append(
            "같은 분야에서 더 의외성이 높은 실제 사례로 소재 자체를 교체한다."
        )

    # ========================================================
    # 신선도
    # ========================================================

    if novelty < MIN_NOVELTY_SCORE:

        problems.append(
            f"신선도 부족: {novelty}/10"
        )

        rewrite_instructions.append(
            "답을 제목만 보고 예상하기 어려운 소재로 바꾼다."
        )

    # ========================================================
    # Scenes
    # ========================================================

    scene_problems = (
        validate_scenes(
            scenes
        )
    )

    problems.extend(
        scene_problems
    )

    # ========================================================
    # 첫 3초
    # ========================================================

    first_text = ""

    if scenes and isinstance(
        scenes[0],
        dict,
    ):

        first_text = str(
            scenes[0].get(
                "text",
                "",
            )
        ).strip()

    hook_score = score_hook(
        first_text
    )

    if hook_score < MIN_HOOK_SCORE:

        problems.append(
            f"첫 3초 후킹 부족: "
            f"{hook_score}/10"
        )

        rewrite_instructions.append(
            "첫 장면을 설명형 문장이 아니라 질문·위험·반전·의외의 장면 중 하나로 다시 작성한다."
        )

    # ========================================================
    # Traffic
    # ========================================================

    traffic_score = score_traffic(
        title,
        topic,
        first_text,
    )

    if traffic_score < MIN_TRAFFIC_SCORE:

        problems.append(
            f"대중성 부족: "
            f"{traffic_score}/10"
        )

        rewrite_instructions.append(
            "일반 시청자가 바로 궁금해할 위험·비밀·의외성 요소를 강화한다."
        )

    # ========================================================
    # 설명조 오프닝 별도 체크
    # ========================================================

    for banned in BANNED_OPENINGS:

        if banned in first_text:

            rewrite_instructions.append(
                f"첫 장면의 '{banned}' 표현을 제거한다."
            )

    # ========================================================
    # 검색어 오류에 대한 공통 개선 지시
    # ========================================================

    if any(
        "검색어" in problem
        for problem in problems
    ):

        rewrite_instructions.append(
            "각 장면의 keyword를 대사의 단어가 아니라 실제 화면에서 보여줘야 하는 상황 중심의 2~5단어 영어 검색어로 다시 작성한다."
        )

    # ========================================================
    # 중복 제거
    # ========================================================

    rewrite_instructions = list(
        dict.fromkeys(
            rewrite_instructions
        )
    )

    passed = (
        len(problems) == 0
    )

    return {

        "passed": passed,

        "scores": {
            "novelty": novelty,
            "traffic": traffic_score,
            "hook": hook_score,
        },

        "problems": problems,

        "rewrite_instructions": (
            rewrite_instructions
        ),
    }


# ============================================================
# 로그 출력
# ============================================================

def print_validation_report(
    report,
):

    print("")
    print("=" * 48)
    print(
        "🧪 V3 SCRIPT VALIDATION"
    )
    print("=" * 48)

    scores = report.get(
        "scores",
        {},
    )

    print(
        f"✨ Novelty: "
        f"{scores.get('novelty', 0)}/10"
    )

    print(
        f"📈 Traffic: "
        f"{scores.get('traffic', 0)}/10"
    )

    print(
        f"🪝 Hook: "
        f"{scores.get('hook', 0)}/10"
    )

    if report.get(
        "passed"
    ):

        print("")
        print(
            "✅ SCRIPT PASSED"
        )

    else:

        print("")
        print(
            "❌ SCRIPT REJECTED"
        )

        for problem in report.get(
            "problems",
            [],
        ):

            print(
                f" - {problem}"
            )

        print("")
        print(
            "🔧 REWRITE:"
        )

        for instruction in report.get(
            "rewrite_instructions",
            [],
        ):

            print(
                f" - {instruction}"
            )

    print("=" * 48)
