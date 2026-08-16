# video/visual_selector.py

import re


# ============================================================
# Visual Selector V3
# ============================================================
#
# 책임:
#   - 장면 대사의 시각적 목적 해석
#   - Pexels 검색용 구체적 keyword 생성 보조
#   - 너무 추상적인 검색어 차단
#   - 장면 간 검색어 반복/랜덤 믹스 최소화
#
# 하지 않는 것:
#   - 실제 Pexels 다운로드
#   - 영상 합성
#   - 자막
#
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

    if len(words) > 6:
        return False

    # 너무 추상적인 단어만 있는 검색어 차단
    meaningful = [
        word
        for word in words
        if word not in GENERIC_WORDS
    ]

    if len(meaningful) < 2:
        return False

    return True


# ============================================================
# 장면 검색어 검증
# ============================================================

def validate_scene_visual(scene):

    if not isinstance(
        scene,
        dict,
    ):
        return False, "scene이 dict가 아님"

    text = str(
        scene.get(
            "text",
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

def validate_visual_plan(
    scenes
):

    if not scenes:
        return False, "장면 없음"

    keywords = []

    for idx, scene in enumerate(
        scenes
    ):

        valid, reason = (
            validate_scene_visual(
                scene
            )
        )

        if not valid:
            return (
                False,
                f"{idx + 1}번 장면: {reason}"
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

    # --------------------------------------------------------
    # 완전히 같은 검색어 반복 차단
    # --------------------------------------------------------

    duplicate_count = (
        len(keywords)
        - len(set(keywords))
    )

    if duplicate_count >= 4:

        return (
            False,
            "동일 검색어 반복이 너무 많음"
        )

    return True, "통과"


# ============================================================
# 시각적 의도 필드 추가
# ============================================================

def enrich_scene_visual_metadata(
    scene
):

    """
    script_generator가 만든 scene에
    visual_goal / visual_type 필드가 없을 경우
    기본값을 보완한다.

    지금 V3에서는 AI가 이 필드를 직접 만드는 방향으로
    확장할 수 있도록 인터페이스만 준비한다.
    """

    if not isinstance(
        scene,
        dict,
    ):
        raise TypeError(
            "scene은 dict여야 합니다."
        )

    result = dict(
        scene
    )

    if not result.get(
        "visual_goal"
    ):

        result["visual_goal"] = (
            result.get(
                "text",
                "",
            )
        )

    if not result.get(
        "visual_type"
    ):

        result["visual_type"] = (
            "real_world_broll"
        )

    if not result.get(
        "keyword"
    ):

        result["keyword"] = (
            "real world closeup"
        )

    return result


# ============================================================
# 전체 장면 보강
# ============================================================

def enrich_visual_plan(
    scenes
):

    return [
        enrich_scene_visual_metadata(
            scene
        )
        for scene in scenes
      ]
