import re


# ============================================================
# Visual Selector V3.2
# ============================================================
#
# 책임:
# - 장면별 visual_goal 검증
# - Pexels용 구체적 keyword 검증
# - 너무 추상적인 검색어 차단
# - 장면 간 검색어 반복 최소화
#
# 핵심 변경:
# - visual_goal을 text 복사로 자동 대체하지 않는다.
# - Script Generator가 '무엇을 보여줄지' 직접 지정해야 한다.
# ============================================================


GENERIC_WORDS = {
    "science",
    "technology",
    "nature",
    "interesting",
    "amazing",
    "documentary",
    "background",
    "concept",
    "future",
    "innovation",
    "beautiful",
    "cool",
    "information",
    "education",
    "abstract",
}


# ============================================================
# 검색어 정리
# ============================================================

def normalize_keyword(keyword):

    keyword = str(
        keyword or ""
    ).strip().lower()

    keyword = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        keyword,
    )

    keyword = re.sub(
        r"\s+",
        " ",
        keyword,
    ).strip()

    return keyword


# ============================================================
# 검색어 품질 검사
# ============================================================

def is_good_visual_keyword(keyword):

    keyword = normalize_keyword(
        keyword
    )

    if not keyword:
        return False

    words = keyword.split()

    if len(words) < 2:
        return False

    if len(words) > 7:
        return False

    meaningful = [
        word
        for word in words
        if word not in GENERIC_WORDS
    ]

    # 적어도 두 개의 구체적인 검색 토큰이 필요하다.
    if len(meaningful) < 2:
        return False

    return True


# ============================================================
# Visual Goal 품질 검사
# ============================================================

def is_good_visual_goal(visual_goal):

    visual_goal = str(
        visual_goal or ""
    ).strip()

    if len(visual_goal) < 8:
        return False

    return True


# ============================================================
# 장면 검색어 검증
# ============================================================

def validate_scene_visual(scene):

    if not isinstance(scene, dict):
        return False, "scene이 dict가 아님"

    text = str(
        scene.get(
            "text",
            "",
        )
    ).strip()

    visual_goal = str(
        scene.get(
            "visual_goal",
            "",
        )
    ).strip()

    keyword = normalize_keyword(
        scene.get(
            "keyword",
            "",
        )
    )

    if not text:
        return False, "대사 없음"

    if not is_good_visual_goal(
        visual_goal
    ):
        return False, "visual_goal이 없거나 지나치게 추상적임"

    if not is_good_visual_keyword(
        keyword
    ):
        return False, (
            f"검색어 품질 부족: {keyword}"
        )

    return True, "통과"


# ============================================================
# 전체 장면 검색어 검증
# ============================================================

def validate_visual_plan(scenes):

    if not scenes:
        return False, "장면 없음"

    keywords = []

    for idx, scene in enumerate(scenes):

        valid, reason = (
            validate_scene_visual(
                scene
            )
        )

        if not valid:
            return (
                False,
                f"{idx + 1}번 장면: {reason}",
            )

        keyword = normalize_keyword(
            scene.get(
                "keyword",
                "",
            )
        )

        keywords.append(
            keyword
        )

    duplicate_count = (
        len(keywords)
        - len(set(keywords))
    )

    if duplicate_count >= 4:
        return (
            False,
            "동일 검색어 반복이 너무 많음",
        )

    # 같은 검색어가 세 번 이상 반복되는 것도 차단한다.
    for keyword in set(keywords):
        if keywords.count(keyword) >= 3:
            return (
                False,
                f"검색어 과다 반복: {keyword}",
            )

    return True, "통과"


# ============================================================
# 장면 메타데이터 정리
# ============================================================

def enrich_scene_visual_metadata(scene):

    if not isinstance(scene, dict):
        raise TypeError(
            "scene은 dict여야 합니다."
        )

    result = dict(scene)

    # visual_goal을 text로 자동 복사하지 않는다.
    # 누락되면 validate_visual_plan에서 실패시켜
    # Script/Rewrite 단계에서 바로잡도록 한다.
    result["visual_goal"] = str(
        result.get(
            "visual_goal",
            "",
        )
    ).strip()

    result["keyword"] = normalize_keyword(
        result.get(
            "keyword",
            "",
        )
    )

    if not result.get(
        "visual_type"
    ):
        result["visual_type"] = (
            "real_world_broll"
        )

    return result


# ============================================================
# 전체 장면 보강
# ============================================================

def enrich_visual_plan(scenes):

    return [
        enrich_scene_visual_metadata(
            scene
        )
        for scene in scenes
    ]
