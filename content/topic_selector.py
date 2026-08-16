import json
import os
import random
from datetime import datetime

from config import (
    RECENT_TOPICS_FILE,
    MAX_RECENT_TOPICS,
)


# ============================================================
# 주제 방향 풀
# ============================================================

TOPIC_POOL = {

    "과학": [
        "일상에서 쉽게 지나치는 이상한 과학 현상",
        "사람들이 잘 모르는 자연의 작동 원리",
        "평범해 보이지만 이유가 있는 물리 현상",
        "실제로 관찰할 수 있는 놀라운 과학 현상",
        "환경에 적응하기 위해 생긴 특이한 자연 현상",
    ],

    "기술": [
        "매일 보지만 작동 원리를 모르는 기술",
        "평범해 보이는 기계의 숨은 설계",
        "기존 방법으로는 해결하기 어려웠던 기술 문제",
        "산업 현장에서 실제로 사용하는 의외의 기술",
        "크기나 구조 때문에 생긴 독특한 공학적 해결책",
    ],

    "생활": [
        "매일 보는 물건의 의외의 설계",
        "사람들이 이상하다고 생각하지만 이유가 있는 생활 속 구조",
        "평범한 행동 뒤에 숨어 있는 과학",
        "일상에서 잘 보이지 않는 안전 장치",
        "우리가 무심코 지나치는 생활 속 기술",
    ],

    "교통": [
        "도로에 숨겨진 의외의 설계",
        "기차와 자동차에 들어간 특이한 안전 기술",
        "교통시설의 잘 보이지 않는 구조",
        "속도와 안전 문제를 해결한 교통 기술",
        "평범한 도로 풍경에 숨어 있는 공학",
    ],

    "자연": [
        "동물의 특이한 생존 전략",
        "자연에서 일어나는 이상한 행동",
        "사람들이 잘 모르는 동물의 능력",
        "극한 환경에서 생물이 살아남는 방법",
        "겉보기와 실제 기능이 다른 자연의 구조",
    ],

    "지리": [
        "지도에서는 평범하지만 실제로는 특이한 장소",
        "사람이 살기 어려운 지역의 독특한 해결책",
        "세계 곳곳의 이상한 지형",
        "자연환경 때문에 생겨난 독특한 시설",
        "지형과 인간 생활이 충돌하면서 생긴 구조",
    ],

    "역사": [
        "역사 속에서 실제로 사용된 특이한 기술",
        "과거 사람들이 문제를 해결한 의외의 방법",
        "지금 보면 이상하지만 당시에는 합리적이었던 기술",
        "역사 속 사라진 생활 기술",
        "유명한 역사적 대상의 잘 알려지지 않은 기능",
    ],
}


# ============================================================
# 전체 방향 풀
# ============================================================

def flatten_topic_pool():

    result = []

    for category, topics in TOPIC_POOL.items():

        for topic in topics:

            result.append({
                "category": category,
                "topic": topic,
            })

    return result


ALL_TOPICS = flatten_topic_pool()


# ============================================================
# 최근 소재 불러오기
# ============================================================

def load_recent_topics():

    if not os.path.exists(RECENT_TOPICS_FILE):
        return []

    try:

        with open(
            RECENT_TOPICS_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:

        print(
            f"⚠️ 최근 소재 읽기 실패: {e}"
        )

    return []


# ============================================================
# 최근 소재 저장
# ============================================================

def save_recent_topics(topics):

    try:

        with open(
            RECENT_TOPICS_FILE,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                topics[-MAX_RECENT_TOPICS:],
                f,
                ensure_ascii=False,
                indent=2,
            )

    except Exception as e:

        print(
            f"⚠️ 최근 소재 저장 실패: {e}"
        )


# ============================================================
# 최근 소재 이름
# ============================================================

def get_recent_topic_names():

    recent = load_recent_topics()

    names = []

    for item in recent:

        if isinstance(item, dict):

            topic = item.get(
                "topic",
                "",
            )

            if topic:
                names.append(topic)

        elif isinstance(item, str):

            names.append(item)

    return names


# ============================================================
# 탐색 방향 선택
# ============================================================

def choose_topic_direction():

    recent_topics = get_recent_topic_names()

    candidates = [
        item
        for item in ALL_TOPICS
        if item["topic"] not in recent_topics
    ]

    if not candidates:
        candidates = ALL_TOPICS

    selected = random.choice(candidates)

    print(
        f"🎯 분야: {selected['category']}"
    )

    print(
        f"🎯 방향: {selected['topic']}"
    )

    return selected


# ============================================================
# 실제 사용 소재 기록
# ============================================================

def remember_used_topic(script_data):

    topic = script_data.get(
        "topic",
        "",
    )

    if not topic:
        return

    recent = load_recent_topics()

    recent.append({
        "topic": topic,
        "category": script_data.get(
            "category",
            "",
        ),
        "title": script_data.get(
            "title",
            "",
        ),
        "created_at": datetime.now().isoformat(),
    })

    save_recent_topics(recent)

    print(
        f"💾 최근 소재 저장: {topic}"
  )
