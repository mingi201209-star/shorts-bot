import os
import re
import json
import asyncio
import requests
import random
import time
from datetime import datetime

import openai
import edge_tts

from video.video_engine import create_scene


# ============================================================
# SHORTS GENERATOR V3
# ============================================================
#
# V3 핵심 변경
#
# 1. 후킹 강제 필터
# 2. 소재 트래픽 필터
# 3. 감정 트리거 검사
# 4. 첫 3초 킬러 오프닝 강제
# 5. B-roll 무작위 키워드 매칭 방지
# 6. 장면 간 맥락 일관성 검사
# 7. 작업 상태 자동 저장
# 8. 실패/중단 시 이전 작업 복구 가능
#
# 현재 구조:
#
# .github/workflows/main.yml
# video/
#   video_downloader.py
#   video_engine.py
#   video_utils.py
# main.py
# requirements.txt
# bot_listener.py
#
# ============================================================


# ============================================================
# 1. 환경 변수
# ============================================================

OPENAI_KEY = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

openai.api_key = OPENAI_KEY


# ============================================================
# 2. 기본 설정
# ============================================================

FPS = 30

MIN_SCENES = 12
MAX_SCENES = 13

TARGET_MIN_SECONDS = 75
TARGET_MAX_SECONDS = 90

VIDEO_BITRATE = "5000k"

TTS_VOICE = "ko-KR-InJoonNeural"

OUTPUT_VIDEO = "final_shorts.mp4"

RECENT_TOPICS_FILE = "recent_topics.json"

WORK_STATE_FILE = "shorts_work_state.json"

MAX_RECENT_TOPICS = 20

# ------------------------------------------------------------
# V3 품질 기준
# ------------------------------------------------------------

MIN_NOVELTY_SCORE = 7

MIN_TRAFFIC_SCORE = 7

MIN_HOOK_SCORE = 8

MIN_BROLL_SCORE = 8

MAX_SCRIPT_ATTEMPTS = 5


# ============================================================
# 3. V3 감정 트리거
# ============================================================

EMOTIONAL_TRIGGERS = [
    "위험",
    "소름",
    "충격",
    "비밀",
    "의외",
    "진짜 이유",
    "몰랐",
    "왜",
    "이상",
    "믿기",
    "놀라",
    "숨겨",
    "반전",
    "주의",
    "생각보다",
    "사실"
]


# ============================================================
# 4. 금지되는 지루한 오프닝
# ============================================================

BANNED_OPENING_PATTERNS = [

    r"오늘은 .* 알아보겠습니다",
    r"오늘은 .* 알아봅니다",
    r".*있는 모습을.*",
    r".*하는 장면.*",
    r".*모습입니다",
    r".*모습을 볼 수 있습니다",
    r".*대해 알아보겠습니다",
    r".*에 대해 알아봅니다",
    r"지금부터 .* 설명하겠습니다",
    r"이번 영상에서는",
    r"이번에는 .* 알아보겠습니다",
    r"이 영상에서는",
    r"먼저 .* 살펴보겠습니다",
    r".*라는 것이 있습니다",
    r".*라고 합니다",
]


# ============================================================
# 5. 너무 평범한 소재 키워드
# ============================================================

COMMON_KNOWLEDGE_KEYWORDS = [

    "지구는 둥글",
    "태양은 동쪽",
    "물은 100도",
    "물은 섭씨 100도",
    "하늘은 파란",
    "중력 때문에 떨어",
    "심장은 피",
    "지구가 태양",
    "달은 지구",
    "식물은 광합성",
    "사람은 산소",
    "얼음은 물",
    "비는 구름",
    "무지개는 빛",
    "번개는 전기",
    "겨울에는 춥",
    "여름에는 덥",
    "물은 얼면",
    "소리는 진동",
]


# ============================================================
# 6. 로그
# ============================================================

def log(message):

    now = datetime.now().strftime("%H:%M:%S")

    print(
        f"[{now}] {message}",
        flush=True
    )


# ============================================================
# 7. 작업 상태 저장
# ============================================================

def save_work_state(
    phase,
    script_data=None,
    completed_scenes=None
):

    state = {
        "phase": phase,
        "updated_at": datetime.now().isoformat(),
        "script_data": script_data or {},
        "completed_scenes": completed_scenes or []
    }

    try:

        with open(
            WORK_STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2
            )

        log(
            f"💾 작업 상태 저장: {phase}"
        )

    except Exception as e:

        log(
            f"⚠️ 작업 상태 저장 실패: {e}"
        )


# ============================================================
# 8. 작업 상태 불러오기
# ============================================================

def load_work_state():

    if not os.path.exists(
        WORK_STATE_FILE
    ):

        return None

    try:

        with open(
            WORK_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            state = json.load(f)

        if not isinstance(
            state,
            dict
        ):

            return None

        return state

    except Exception as e:

        log(
            f"⚠️ 작업 상태 읽기 실패: {e}"
        )

        return None


# ============================================================
# 9. 작업 상태 삭제
# ============================================================

def clear_work_state():

    if not os.path.exists(
        WORK_STATE_FILE
    ):

        return

    try:

        os.remove(
            WORK_STATE_FILE
        )

        log(
            "🧹 완료된 작업 상태 삭제"
        )

    except Exception as e:

        log(
            f"⚠️ 작업 상태 삭제 실패: {e}"
        )


# ============================================================
# 10. Telegram 메시지
# ============================================================

def send_telegram_message(message):

    if not TELEGRAM_BOT_TOKEN:

        log(
            "⚠️ TELEGRAM_BOT_TOKEN 없음"
        )

        return

    if not TELEGRAM_CHAT_ID:

        log(
            "⚠️ TELEGRAM_CHAT_ID 없음"
        )

        return

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    try:

        response = requests.post(

            url,

            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": str(message)
            },

            timeout=20
        )

        if response.ok:

            log(
                "📨 Telegram 메시지 전송 완료"
            )

        else:

            log(
                "⚠️ Telegram 메시지 전송 실패: "
                f"HTTP {response.status_code}"
            )

    except Exception as e:

        log(
            f"⚠️ Telegram 메시지 에러: {e}"
        )


# ============================================================
# 11. Telegram 영상 전송
# ============================================================

def send_telegram_video(video_path):

    if not TELEGRAM_BOT_TOKEN:

        log(
            "⚠️ TELEGRAM_BOT_TOKEN 없음"
        )

        return

    if not TELEGRAM_CHAT_ID:

        log(
            "⚠️ TELEGRAM_CHAT_ID 없음"
        )

        return

    if not os.path.exists(
        video_path
    ):

        log(
            "⚠️ 전송할 영상이 없습니다: "
            f"{video_path}"
        )

        return

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    )

    try:

        with open(
            video_path,
            "rb"
        ) as video_file:

            response = requests.post(

                url,

                data={
                    "chat_id": TELEGRAM_CHAT_ID
                },

                files={
                    "video": video_file
                },

                timeout=300
            )

        if response.ok:

            log(
                "📤 Telegram 영상 전송 완료"
            )

        else:

            log(
                "⚠️ Telegram 영상 전송 실패: "
                f"HTTP {response.status_code}"
            )

            send_telegram_message(
                "⚠️ 영상 전송 실패\n"
                f"HTTP {response.status_code}"
            )

    except Exception as e:

        log(
            f"⚠️ Telegram 영상 전송 에러: {e}"
        )

        send_telegram_message(
            "⚠️ 영상 전송 에러\n"
            f"{str(e)[:300]}"
        )


# ============================================================
# 12. 환경변수 검사
# ============================================================

def validate_environment():

    missing = []

    if not OPENAI_KEY:
        missing.append("OPENAI_KEY")

    if not PEXELS_API_KEY:
        missing.append("PEXELS_API_KEY")

    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:

        error_message = (
            "필수 환경변수가 없습니다:\n"
            + "\n".join(
                f"- {item}"
                for item in missing
            )
        )

        log(
            f"❌ {error_message}"
        )

        send_telegram_message(
            "🚨 Shorts Generator 환경변수 오류\n\n"
            + error_message
        )

        raise RuntimeError(
            error_message
        )

    log(
        "✅ 환경변수 검사 완료"
    )


# ============================================================
# 13. TOPIC POOL
# ============================================================

TOPIC_POOL = {

    "과학": [
        "일상에서 쉽게 지나치는 이상한 과학 현상",
        "사람들이 잘 모르는 자연의 작동 원리",
        "평범해 보이지만 이유가 있는 물리 현상",
        "실제로 관찰할 수 있는 놀라운 과학 현상",
        "환경에 적응하기 위해 생긴 특이한 자연 현상"
    ],

    "기술": [
        "매일 보지만 작동 원리를 모르는 기술",
        "평범해 보이는 기계의 숨은 설계",
        "기존 방법으로는 해결하기 어려웠던 기술 문제",
        "산업 현장에서 실제로 사용하는 의외의 기술",
        "크기나 구조 때문에 생긴 독특한 공학적 해결책"
    ],

    "생활": [
        "매일 보는 물건의 의외의 설계",
        "사람들이 이상하다고 생각하지만 이유가 있는 생활 속 구조",
        "평범한 행동 뒤에 숨어 있는 과학",
        "일상에서 잘 보이지 않는 안전 장치",
        "우리가 무심코 지나치는 생활 속 기술"
    ],

    "교통": [
        "도로에 숨겨진 의외의 설계",
        "기차와 자동차에 들어간 특이한 안전 기술",
        "교통시설의 잘 보이지 않는 구조",
        "속도와 안전 문제를 해결한 교통 기술",
        "평범한 도로 풍경에 숨어 있는 공학"
    ],

    "자연": [
        "동물의 특이한 생존 전략",
        "자연에서 일어나는 이상한 행동",
        "사람들이 잘 모르는 동물의 능력",
        "극한 환경에서 생물이 살아남는 방법",
        "겉보기와 실제 기능이 다른 자연의 구조"
    ],

    "지리": [
        "지도에서는 평범하지만 실제로는 특이한 장소",
        "사람이 살기 어려운 지역의 독특한 해결책",
        "세계 곳곳의 이상한 지형",
        "자연환경 때문에 생겨난 독특한 시설",
        "지형과 인간 생활이 충돌하면서 생긴 구조"
    ],

    "역사": [
        "역사 속에서 실제로 사용된 특이한 기술",
        "과거 사람들이 문제를 해결한 의외의 방법",
        "지금 보면 이상하지만 당시에는 합리적이었던 기술",
        "역사 속 사라진 생활 기술",
        "유명한 역사적 대상의 잘 알려지지 않은 기능"
    ]
}


# ============================================================
# 14. 전체 방향
# ============================================================

def flatten_topic_pool():

    result = []

    for category, topics in TOPIC_POOL.items():

        for topic in topics:

            result.append(
                {
                    "category": category,
                    "topic": topic
                }
            )

    return result


ALL_TOPICS = flatten_topic_pool()


# ============================================================
# 15. 최근 소재
# ============================================================

def load_recent_topics():

    if not os.path.exists(
        RECENT_TOPICS_FILE
    ):

        return []

    try:

        with open(
            RECENT_TOPICS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(
            data,
            list
        ):

            return data

    except Exception as e:

        log(
            f"⚠️ 최근 소재 읽기 실패: {e}"
        )

    return []


def save_recent_topics(topics):

    try:

        with open(
            RECENT_TOPICS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                topics[-MAX_RECENT_TOPICS:],
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        log(
            f"⚠️ 최근 소재 저장 실패: {e}"
        )


def get_recent_topic_names():

    recent = load_recent_topics()

    names = []

    for item in recent:

        if isinstance(
            item,
            dict
        ):

            topic = item.get(
                "topic",
                ""
            )

            if topic:
                names.append(topic)

        elif isinstance(
            item,
            str
        ):

            names.append(item)

    return names


# ============================================================
# 16. 방향 선택
# ============================================================

def choose_topic_direction():

    recent_topics = get_recent_topic_names()

    candidates = []

    for item in ALL_TOPICS:

        if item["topic"] in recent_topics:
            continue

        candidates.append(item)

    if not candidates:

        candidates = ALL_TOPICS

    selected = random.choice(
        candidates
    )

    log(
        f"🎯 분야: {selected['category']}"
    )

    log(
        f"🎯 방향: {selected['topic']}"
    )

    return selected


# ============================================================
# 17. JSON 추출
# ============================================================

def extract_json(text):

    if not text:

        raise ValueError(
            "AI 응답이 비어 있습니다."
        )

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    text = text.strip()

    try:

        return json.loads(text)

    except Exception:
        pass

    start = text.find("[")
    end = text.rfind("]")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(candidate)

        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(candidate)

        except Exception:
            pass

    raise ValueError(
        "AI 응답에서 JSON을 찾지 못했습니다."
    )


# ============================================================
# 18. 흔한 소재 검사
# ============================================================

def looks_too_common(topic):

    if not topic:

        return True

    normalized = (
        topic
        .replace(" ", "")
        .lower()
    )

    for keyword in COMMON_KNOWLEDGE_KEYWORDS:

        normalized_keyword = (
            keyword
            .replace(" ", "")
            .lower()
        )

        if normalized_keyword in normalized:

            return True

    return False


# ============================================================
# 19. 오프닝 금지 패턴 검사
# ============================================================

def is_banned_opening(text):

    if not text:

        return True

    for pattern in BANNED_OPENING_PATTERNS:

        if re.search(
            pattern,
            text
        ):

            return True

    return False


# ============================================================
# 20. 감정 트리거 검사
# ============================================================

def count_emotional_triggers(text):

    if not text:

        return 0

    count = 0

    for trigger in EMOTIONAL_TRIGGERS:

        if trigger in text:

            count += 1

    return count


# ============================================================
# 21. 검색어 품질 검사
# ============================================================

def validate_keyword(keyword):

    if not keyword:

        return False

    words = keyword.strip().split()

    if len(words) < 2:
        return False

    if len(words) > 6:
        return False

    # 한국어 검색어 방지
    if re.search(
        r"[가-힣]",
        keyword
    ):

        return False

    banned = [
        "interesting",
        "amazing",
        "science",
        "technology",
        "nature",
        "cool",
        "awesome",
        "random",
        "beautiful"
    ]

    normalized = keyword.lower()

    for item in banned:

        if normalized == item:
            return False

    return True


# ============================================================
# 22. B-roll 전체 검사
# ============================================================

def validate_broll_integrity(scenes):

    if not scenes:

        return False, 0

    valid = 0
    keywords = []

    for scene in scenes:

        keyword = str(
            scene.get(
                "keyword",
                ""
            )
        ).strip()

        if validate_keyword(
            keyword
        ):

            valid += 1

            keywords.append(
                keyword.lower()
            )

    if not scenes:

        return False, 0

    score = int(
        valid
        / len(scenes)
        * 10
    )

    # 같은 검색어 반복을 감점
    unique_ratio = (
        len(set(keywords))
        / max(
            len(keywords),
            1
        )
    )

    if unique_ratio < 0.6:

        score -= 2

    score = max(
        0,
        min(
            score,
            10
        )
    )

    return (
        score >= MIN_BROLL_SCORE,
        score
    )


# ============================================================
# 23. V3 대본 품질 검사
# ============================================================

def validate_script_v3(result):

    if not isinstance(
        result,
        dict
    ):

        return False, "결과가 객체가 아님"

    title = str(
        result.get(
            "title",
            ""
        )
    ).strip()

    topic = str(
        result.get(
            "topic",
            ""
        )
    ).strip()

    scenes = result.get(
        "scenes",
        []
    )

    novelty = result.get(
        "novelty_score",
        0
    )

    traffic = result.get(
        "traffic_score",
        0
    )

    hook_score = result.get(
        "hook_score",
        0
    )

    try:
        novelty = int(novelty)
    except Exception:
        novelty = 0

    try:
        traffic = int(traffic)
    except Exception:
        traffic = 0

    try:
        hook_score = int(hook_score)
    except Exception:
        hook_score = 0

    if not title:
        return False, "제목 없음"

    if not topic:
        return False, "소재 없음"

    if looks_too_common(topic):

        return False, "너무 흔한 소재"

    if novelty < MIN_NOVELTY_SCORE:

        return False, (
            f"신선도 부족: {novelty}/10"
        )

    if traffic < MIN_TRAFFIC_SCORE:

        return False, (
            f"트래픽 점수 부족: {traffic}/10"
        )

    if hook_score < MIN_HOOK_SCORE:

        return False, (
            f"후킹 점수 부족: {hook_score}/10"
        )

    if not isinstance(
        scenes,
        list
    ):

        return False, "scenes가 배열이 아님"

    if len(scenes) < MIN_SCENES:

        return False, (
            f"장면 부족: {len(scenes)}개"
        )

    first_scene = scenes[0]

    first_text = str(
        first_scene.get(
            "text",
            ""
        )
    ).strip()

    if is_banned_opening(
        first_text
    ):

        return False, (
            "설명조 오프닝 차단"
        )

    if count_emotional_triggers(
        first_text
    ) < 1:

        return False, (
            "첫 장면 감정 트리거 없음"
        )

    broll_ok, broll_score = (
        validate_broll_integrity(
            scenes
        )
    )

    if not broll_ok:

        return False, (
            f"B-roll 품질 부족: "
            f"{broll_score}/10"
        )

    # 장면 텍스트 존재 검사
    for index, scene in enumerate(
        scenes
    ):

        text = str(
            scene.get(
                "text",
                ""
            )
        ).strip()

        keyword = str(
            scene.get(
                "keyword",
                ""
            )
        ).strip()

        if not text:

            return False, (
                f"{index + 1}번 장면 대사 없음"
            )

        if not validate_keyword(
            keyword
        ):

            return False, (
                f"{index + 1}번 장면 "
                f"검색어 품질 부족"
            )

    return True, "V3 통과"


# ============================================================
# 24. AI 대본 생성
# ============================================================

def generate_script(topic_info):

    category = topic_info["category"]
    direction = topic_info["topic"]

    recent_topics = get_recent_topic_names()

    recent_text = "\n".join(
        f"- {item}"
        for item in recent_topics[-20:]
    )

    log(
        "🧠 V3 AI 소재 + 대본 생성 시작..."
    )

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1
    ):

        log(
            f"🔎 V3 소재 탐색 "
            f"{attempt}/{MAX_SCRIPT_ATTEMPTS}"
        )

        prompt = f"""
너는 유튜브 Shorts 전문 콘텐츠 디렉터다.

현재 엔진 버전: V3.0

콘텐츠 방향:
{direction}

분야:
{category}


============================================================
[절대 규칙 1 — 첫 3초]
============================================================

첫 장면은 설명으로 시작하면 안 된다.

다음 유형은 금지:

"오늘은..."
"이번 영상에서는..."
"~있는 모습입니다."
"~하는 장면입니다."
"~에 대해 알아보겠습니다."

첫 장면부터

위험,
의외의 상황,
강한 질문,
충격적인 사실,
이상한 장면,
숨겨진 비밀

중 하나를 던져라.

시청자가 바로

"뭐야?"
"왜?"
"저게 왜 저래?"

라고 생각해야 한다.

첫 장면은 시각적으로 표현 가능한
구체적인 상황이어야 한다.


============================================================
[절대 규칙 2 — 대중성]
============================================================

단순한 기술 설명을 만들지 마라.

"전선에 절연이 필요한 이유"
"물이 끓는 이유"
"하늘이 파란 이유"

같은 누구나 어느 정도 아는 주제는 탈락이다.

일반 시청자가 처음 접했을 가능성이 높은
구체적인 실제 사례를 선택하라.

공포,
호기심,
충격,
의외성

중 최소 하나가 강하게 작동해야 한다.


============================================================
[절대 규칙 3 — 스토리]
============================================================

단순한 정보 나열 금지.

다음 구조를 사용한다.

1. 이상한 상황
2. 왜 그런지 질문
3. 실제 문제
4. 일반적인 해결법
5. 그 방법의 한계
6. 의외의 해결법
7. 핵심 원리
8. 실제 구조
9. 실제 사례
10. 예상 밖의 사실
11. 다른 사례
12. 결론


============================================================
[절대 규칙 4 — B-ROLL]
============================================================

키워드 단어 하나만 맞추는 식의 검색 금지.

예:

대사:
"기차가 커브에서 바깥쪽 레일을 높입니다."

나쁜 검색어:
"train"

좋은 검색어:
"train railway curve"

대사:
"거대한 타이어에 액체를 넣습니다."

나쁜 검색어:
"tractor"

좋은 검색어:
"tractor tire liquid ballast"

각 검색어는 반드시
실제 화면에서 대사를 설명할 수 있어야 한다.


============================================================
[절대 규칙 5 — 시각적 일관성]
============================================================

장면마다 완전히 다른 장소를 랜덤하게 넣지 마라.

한 영상 안에서

장소,
시간대,
분위기,
주요 대상

이 최대한 연결되어야 한다.

필요하면 실제 영상 대신
구조 설명용 다이어그램,
클로즈업,
공정 영상,
디테일 영상

등을 사용한다.


============================================================
[신선도]
============================================================

novelty_score:
1~10

7 미만이면 실패.

가능하면 8~10.


============================================================
[트래픽]
============================================================

traffic_score:
1~10

일반 시청자가 제목만 보고
궁금해서 클릭할 가능성을 평가한다.

7 미만이면 실패.


============================================================
[후킹]
============================================================

hook_score:
1~10

첫 3초만 보고
스크롤을 멈출 가능성을 평가한다.

8 미만이면 실패.


============================================================
[이전 소재]
============================================================

다음과 같거나 사실상 같은 소재는 금지:

{recent_text}


============================================================
[영상 길이]
============================================================

75~90초

12~13 scenes

전체 대사는 TTS 기준으로
충분한 길이가 되도록 작성한다.


============================================================
[제목]
============================================================

낚시성 과장 금지.

하지만 호기심은 강해야 한다.

예:

"왜 거대한 트랙터 타이어에 물을 넣을까?"

"기차 선로가 일부러 기울어진 진짜 이유"

"평범한 도로에 이 구조가 있는 이유"


============================================================
[사실성]
============================================================

확실하지 않은 숫자를 만들지 마라.

가짜 연구 결과 금지.

인터넷 괴담 금지.

사실과 추측을 섞지 마라.


============================================================
[JSON 출력]
============================================================

JSON 객체 하나만 출력한다.

설명 금지.

형식:

{{
  "title": "영상 제목",
  "topic": "구체적인 실제 소재",
  "category": "{category}",
  "novelty_score": 9,
  "traffic_score": 8,
  "hook_score": 9,
  "scenes": [
    {{
      "text": "첫 장면의 강력한 대사",
      "keyword": "specific visual keyword"
    }}
  ]
}}

반드시 12~13개 scenes.

첫 장면은 가장 강력해야 한다.

모든 keyword는 영어.

keyword는 2~5개의 구체적인 단어.

일반 단어:

science
technology
nature
interesting
amazing
space

등은 사용하지 마라.
"""

        try:

            response = openai.chat.completions.create(

                model="gpt-4o-mini",

                messages=[

                    {
                        "role": "system",
                        "content": (
                            "너는 Shorts V3 콘텐츠 디렉터다. "
                            "평범한 상식이 아니라 "
                            "높은 호기심과 시각적 설명이 가능한 "
                            "실제 소재를 찾아야 한다."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=1.0
            )

            content = (
                response
                .choices[0]
                .message
                .content
                .strip()
            )

            result = extract_json(
                content
            )

            actual_topic = str(
                result.get(
                    "topic",
                    ""
                )
            ).strip()

            novelty = result.get(
                "novelty_score",
                0
            )

            traffic = result.get(
                "traffic_score",
                0
            )

            hook = result.get(
                "hook_score",
                0
            )

            try:
                novelty = int(novelty)
            except Exception:
                novelty = 0

            try:
                traffic = int(traffic)
            except Exception:
                traffic = 0

            try:
                hook = int(hook)
            except Exception:
                hook = 0

            log(
                f"🧠 소재: {actual_topic}"
            )

            log(
                f"✨ 신선도: {novelty}/10"
            )

            log(
                f"📈 트래픽: {traffic}/10"
            )

            log(
                f"🪝 후킹: {hook}/10"
            )

            if actual_topic in recent_topics:

                log(
                    "🚫 최근 사용 소재 → 폐기"
                )

                continue

            valid, reason = (
                validate_script_v3(
                    result
                )
            )

            if not valid:

                log(
                    f"🚫 V3 필터 탈락: {reason}"
                )

                continue

            scenes = result[
                "scenes"
            ]

            cleaned_scenes = []

            for scene in scenes:

                text = str(
                    scene.get(
                        "text",
                        ""
                    )
                ).strip()

                keyword = str(
                    scene.get(
                        "keyword",
                        ""
                    )
                ).strip()

                if not text:
                    continue

                cleaned_scenes.append(
                    {
                        "text": text,
                        "keyword": keyword
                    }
                )

            result["scenes"] = (
                cleaned_scenes[:MAX_SCENES]
            )

            result["title"] = str(
                result.get(
                    "title",
                    actual_topic
                )
            ).strip()

            result["topic"] = actual_topic

            result["category"] = category

            result["novelty_score"] = novelty

            result["traffic_score"] = traffic

            result["hook_score"] = hook

            log(
                "======================================"
            )

            log(
                "🎯 V3 소재 선정 성공"
            )

            log(
                f"🧠 소재: {actual_topic}"
            )

            log(
                f"✨ 신선도: {novelty}/10"
            )

            log(
                f"📈 트래픽: {traffic}/10"
            )

            log(
                f"🪝 후킹: {hook}/10"
            )

            log(
                f"📝 제목: {result['title']}"
            )

            log(
                f"🎬 장면: {len(result['scenes'])}개"
            )

            log(
                "======================================"
            )

            for idx, scene in enumerate(
                result["scenes"]
            ):

                log(
                    f"   {idx + 1}. "
                    f"{scene['keyword']}"
                )

            return result

        except Exception as e:

            log(
                f"⚠️ V3 대본 생성 실패: {e}"
            )

    raise RuntimeError(
        "V3 품질 기준을 통과하는 "
        "소재를 찾지 못했습니다."
    )


# ============================================================
# 25. TTS
# ============================================================

async def generate_voice(
    text,
    output_path
):

    communicate = edge_tts.Communicate(
        text,
        TTS_VOICE
    )

    await communicate.save(
        output_path
    )


def create_voice(
    text,
    output_path
):

    log(
        f"🎙️ TTS: {text}"
    )

    asyncio.run(
        generate_voice(
            text,
            output_path
        )
    )

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "TTS 파일 생성 실패"
        )


# ============================================================
# 26. 총 길이 검사
# ============================================================

def check_total_duration(
    scene_clips
):

    if not scene_clips:

        raise RuntimeError(
            "장면이 없습니다."
        )

    total = 0.0

    for clip in scene_clips:

        try:

            duration = float(
                clip.duration or 0
            )

        except Exception:

            duration = 0.0

        total += duration

    log(
        f"⏱️ 장면 합산 길이: "
        f"{total:.2f}초"
    )

    if total < TARGET_MIN_SECONDS:

        log(
            f"⚠️ 목표보다 짧음: "
            f"{TARGET_MIN_SECONDS}초 미만"
        )

    elif total > TARGET_MAX_SECONDS:

        log(
            f"⚠️ 목표보다 김: "
            f"{TARGET_MAX_SECONDS}초 초과"
        )

    else:

        log(
            "✅ Shorts 목표 길이 통과"
        )

    return total


# ============================================================
# 27. 최종 영상 렌더링
# ============================================================

def render_final_video(
    scene_clips
):

    if not scene_clips:

        raise RuntimeError(
            "생성된 장면이 없습니다."
        )

    from moviepy.editor import (
        concatenate_videoclips
    )

    log("")
    log(
        "🎞️ 모든 장면을 합치는 중..."
    )

    final_video = concatenate_videoclips(
        scene_clips,
        method="compose"
    )

    total_duration = (
        final_video.duration
    )

    log(
        f"🎬 최종 영상 길이: "
        f"{total_duration:.2f}초"
    )

    log(
        "🎥 FFmpeg 렌더링 시작..."
    )

    final_video.write_videofile(

        OUTPUT_VIDEO,

        fps=FPS,

        codec="libx264",

        audio_codec="aac",

        bitrate=VIDEO_BITRATE,

        threads=2,

        preset="medium"
    )

    final_video.close()

    log(
        "✅ 최종 영상 렌더링 완료"
    )

    return OUTPUT_VIDEO


# ============================================================
# 28. 소재 저장
# ============================================================

def remember_used_topic(
    script_data
):

    topic = script_data.get(
        "topic",
        ""
    )

    if not topic:
        return

    recent = load_recent_topics()

    recent.append(
        {
            "topic": topic,
            "category": script_data.get(
                "category",
                ""
            ),
            "title": script_data.get(
                "title",
                ""
            ),
            "novelty_score": script_data.get(
                "novelty_score",
                0
            ),
            "traffic_score": script_data.get(
                "traffic_score",
                0
            ),
            "hook_score": script_data.get(
                "hook_score",
                0
            ),
            "created_at": datetime.now().isoformat()
        }
    )

    save_recent_topics(
        recent
    )

    log(
        f"💾 최근 소재 저장: {topic}"
    )


# ============================================================
# 29. 결과 요약
# ============================================================

def send_result_summary(
    script_data,
    duration
):

    title = script_data.get(
        "title",
        "제목 없음"
    )

    topic = script_data.get(
        "topic",
        "소재 없음"
    )

    category = script_data.get(
        "category",
        "분야 없음"
    )

    novelty = script_data.get(
        "novelty_score",
        "?"
    )

    traffic = script_data.get(
        "traffic_score",
        "?"
    )

    hook = script_data.get(
        "hook_score",
        "?"
    )

    scenes = script_data.get(
        "scenes",
        []
    )

    message = (
        "🎬 Shorts V3 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"✨ 신선도: {novelty}/10\n"
        f"📈 트래픽: {traffic}/10\n"
        f"🪝 후킹: {hook}/10\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: {len(scenes)}개\n\n"
        "📦 영상 전송 중..."
    )

    send_telegram_message(
        message
    )


# ============================================================
# 30. 임시 파일 정리
# ============================================================

def cleanup_temp_files():

    log(
        "🧹 임시 파일 정리 시작"
    )

    for filename in os.listdir("."):

        should_delete = False

        if (
            filename.startswith("scene_")
            and filename.endswith(".mp3")
        ):

            should_delete = True

        elif (
            filename.startswith("video_")
            and filename.endswith(".mp4")
        ):

            should_delete = True

        if not should_delete:
            continue

        try:

            os.remove(filename)

            log(
                f"삭제: {filename}"
            )

        except Exception as e:

            log(
                f"⚠️ 삭제 실패 "
                f"{filename}: {e}"
            )


# ============================================================
# 31. 메인
# ============================================================

def main():

    start_time = time.time()

    scene_clips = []

    script_data = None

    try:

        log(
            "======================================"
        )

        log(
            "🚀 SHORTS GENERATOR V3 START"
        )

        log(
            "======================================"
        )

        # ----------------------------------------------------
        # 환경변수
        # ----------------------------------------------------

        validate_environment()

        save_work_state(
            "environment_checked"
        )

        # ----------------------------------------------------
        # 기존 작업 확인
        # ----------------------------------------------------

        previous_state = (
            load_work_state()
        )

        if previous_state:

            previous_phase = (
                previous_state.get(
                    "phase",
                    ""
                )
            )

            previous_script = (
                previous_state.get(
                    "script_data",
                    {}
                )
            )

            if previous_script:

                log(
                    "🔄 이전 작업 상태 발견"
                )

                log(
                    f"📌 이전 단계: "
                    f"{previous_phase}"
                )

                # 완전히 끝난 작업이 아니라면
                # 대본을 다시 활용한다.
                script_data = previous_script

                save_work_state(
                    "resume_script",
                    script_data
                )

        # ----------------------------------------------------
        # 새 작업
        # ----------------------------------------------------

        if not script_data:

            topic_info = (
                choose_topic_direction()
            )

            save_work_state(
                "topic_selected",
                {
                    "category": topic_info[
                        "category"
                    ],
                    "direction": topic_info[
                        "topic"
                    ]
                }
            )

            script_data = (
                generate_script(
                    topic_info
                )
            )

            save_work_state(
                "script_created",
                script_data
            )

        # ----------------------------------------------------
        # 장면
        # ----------------------------------------------------

        scenes = script_data.get(
            "scenes",
            []
        )

        if not scenes:

            raise RuntimeError(
                "AI가 장면을 생성하지 않았습니다."
            )

        log(
            f"📚 총 {len(scenes)}개 장면 처리"
        )

        # ----------------------------------------------------
        # 장면 생성
        # ----------------------------------------------------

        completed_scene_indexes = []

        for idx, item in enumerate(
            scenes[:MAX_SCENES]
        ):

            try:

                scene = create_scene(
                    idx,
                    item,
                    create_voice,
                    requests
                )

                scene_clips.append(
                    scene
                )

                completed_scene_indexes.append(
                    idx
                )

                save_work_state(
                    "scene_progress",
                    script_data,
                    completed_scene_indexes
                )

                log(
                    f"✅ SCENE {idx + 1} 완료"
                )

            except Exception as e:

                log(
                    f"❌ SCENE {idx + 1} 실패: {e}"
                )

                save_work_state(
                    "scene_failed",
                    script_data,
                    completed_scene_indexes
                )

                raise

        # ----------------------------------------------------
        # 총 길이
        # ----------------------------------------------------

        save_work_state(
            "all_scenes_completed",
            script_data,
            completed_scene_indexes
        )

        total_duration = (
            check_total_duration(
                scene_clips
            )
        )

        # ----------------------------------------------------
        # 최종 영상
        # ----------------------------------------------------

        save_work_state(
            "rendering",
            script_data,
            completed_scene_indexes
        )

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ----------------------------------------------------
        # 실제 소재 기록
        #
        # 중요:
        # 렌더링 성공 후에만 저장한다.
        # ----------------------------------------------------

        remember_used_topic(
            script_data
        )

        # ----------------------------------------------------
        # Telegram 결과
        # ----------------------------------------------------

        send_result_summary(
            script_data,
            total_duration
        )

        # ----------------------------------------------------
        # Telegram 영상
        # ----------------------------------------------------

        send_telegram_video(
            final_path
        )

        # ----------------------------------------------------
        # 완료
        # ----------------------------------------------------

        elapsed = (
            time.time()
            - start_time
        )

        clear_work_state()

        log(
            "======================================"
        )

        log(
            "🎉 SHORTS GENERATOR V3 COMPLETE"
        )

        log(
            f"⏱️ 전체 소요시간: "
            f"{elapsed / 60:.1f}분"
        )

        log(
            "======================================"
        )

    except Exception as e:

        log(
            "======================================"
        )

        log(
            f"💀 SHORTS GENERATOR V3 ERROR: {e}"
        )

        log(
            "======================================"
        )

        send_telegram_message(
            "🚨 Shorts V3 생성 실패\n\n"
            f"{str(e)[:500]}"
        )

        raise

    finally:

        # ----------------------------------------------------
        # MoviePy 객체 닫기
        # ----------------------------------------------------

        for clip in scene_clips:

            try:

                clip.close()

            except Exception:
                pass

        # ----------------------------------------------------
        # 임시 파일
        # ----------------------------------------------------

        cleanup_temp_files()


# ============================================================
# 32. 실행
# ============================================================

if __name__ == "__main__":

    main()
