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
# Shorts Generator
# ============================================================
#
# 제작 엔진
#
# 1. 소재 방향 선택
# 2. "이미 다 아는 거 아님?" 1차 필터
# 3. AI가 구체적인 실제 소재 발굴
# 4. 대본 생성
# 5. 시각 검색어 생성
# 6. TTS
# 7. 장면 생성
# 8. 75~90초 검증
# 9. 최종 합성
# 10. Telegram 전송
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

MAX_RECENT_TOPICS = 20


# ============================================================
# 3. 로그
# ============================================================

def log(message):

    now = datetime.now().strftime("%H:%M:%S")

    print(
        f"[{now}] {message}",
        flush=True
    )


# ============================================================
# 4. Telegram 메시지
# ============================================================

def send_telegram_message(message):

    if not TELEGRAM_BOT_TOKEN:
        log("⚠️ TELEGRAM_BOT_TOKEN 없음")
        return

    if not TELEGRAM_CHAT_ID:
        log("⚠️ TELEGRAM_CHAT_ID 없음")
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

            log("📨 Telegram 메시지 전송 완료")

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
# 5. Telegram 영상 전송
# ============================================================

def send_telegram_video(video_path):

    if not TELEGRAM_BOT_TOKEN:
        log("⚠️ TELEGRAM_BOT_TOKEN 없음")
        return

    if not TELEGRAM_CHAT_ID:
        log("⚠️ TELEGRAM_CHAT_ID 없음")
        return

    if not os.path.exists(video_path):

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
# 6. 환경변수 검사
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
# 7. 소재 방향 풀
# ============================================================
#
# 중요한 변경:
#
# 예전처럼
#
# "우주에서 일어나는 이상한 현상"
#
# 같은 너무 넓은 주제를 바로 영상 소재로 사용하지 않는다.
#
# 이건 "탐색 방향"일 뿐이다.
#
# 실제 영상 소재는 AI가 별도로 발굴한다.
#
# ============================================================

TOPIC_POOL = {

    "과학": [
        "사람들이 원리를 잘 모르는 일상 속 물리 현상",
        "눈앞에서 볼 수 있지만 이유를 모르는 자연 현상",
        "작은 장치 하나가 큰 문제를 해결하는 과학",
        "겉보기와 실제 작동 방식이 완전히 다른 현상",
        "자연이 스스로 문제를 해결하는 방식",
        "극한 환경에서 생기는 의외의 물리 현상",
        "평범한 물건에 숨어 있는 과학적 설계"
    ],

    "역사": [
        "현재는 사라졌지만 당시에는 실제로 사용되던 기술",
        "역사적으로 사람들이 문제를 해결했던 의외의 방법",
        "유명한 사건보다 그 뒤에 숨어 있는 기술",
        "과거의 생활에서 지금과 완전히 달랐던 방식",
        "실제로 존재했던 기묘한 시설과 그 용도",
        "전쟁이나 재난에서 탄생한 의외의 기술"
    ],

    "지리": [
        "지도에서 보면 이상하지만 실제 이유가 있는 장소",
        "사람들이 자주 지나치지만 이유를 모르는 지형",
        "세계의 극단적인 환경에 적응한 시설",
        "국경이나 도시의 위치가 특이하게 결정된 이유",
        "자연환경 때문에 만들어진 독특한 시설",
        "일반적인 상식과 다른 세계의 지리 현상"
    ],

    "기술": [
        "매일 보지만 작동 원리를 모르는 기술",
        "거대한 시설이 의외로 단순한 원리로 움직이는 사례",
        "고장처럼 보이지만 사실 정상적으로 작동하는 기술",
        "사람 대신 기계가 반복적인 문제를 해결하는 기술",
        "극한 환경에서 사용되는 특수 기술",
        "평범한 물건 속에 숨겨진 의외의 기술"
    ],

    "자연": [
        "동물이 인간이 예상하지 못한 방식으로 살아남는 사례",
        "생물이 극한 환경에 적응한 독특한 방법",
        "겉보기에는 이상하지만 생존에 도움이 되는 행동",
        "자연에서 실제로 일어나는 이상한 현상",
        "사람들이 잘 모르는 생태계의 숨은 관계",
        "동물이나 식물의 독특한 문제 해결 방식"
    ],

    "생활": [
        "매일 보지만 이유를 모르는 생활 속 장치",
        "고장처럼 보이지만 사실 정상인 물건",
        "평범한 제품에 숨겨진 의외의 설계",
        "도시에서 사람들이 무심코 지나치는 시설",
        "일상에서 반복되지만 아무도 이유를 묻지 않는 현상",
        "생활 속에서 실제로 유용한 의외의 과학"
    ],

    "산업_공학": [
        "도로와 철도에 숨어 있는 의외의 설계",
        "건설 현장에서 일부러 이상하게 만든 구조",
        "거대한 산업시설이 작동하는 의외의 방식",
        "농기계에 들어간 예상 밖의 기술",
        "배와 항공기에 숨겨진 특수 설계",
        "물이거나 바람이거나 중력을 이용해 문제를 해결하는 구조"
    ]
}


# ============================================================
# 8. 전체 방향 풀
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
# 9. 너무 흔한 소재 차단 목록
# ============================================================
#
# AI가 "놀랍다"고 착각하기 쉬운 소재를 차단한다.
#
# 완벽한 필터가 아니라 1차 방어선이다.
#
# ============================================================

COMMON_KNOWLEDGE_PATTERNS = [

    "하늘이 파란 이유",

    "무지개가 생기는 이유",

    "비가 오는 이유",

    "번개가 치는 이유",

    "구름이 생기는 이유",

    "지구가 둥근 이유",

    "중력이 존재하는 이유",

    "태양이 뜨고 지는 이유",

    "달의 위상",

    "물은 100도에서 끓는다",

    "얼음이 물에 뜨는 이유",

    "소리가 진공에서 전달되지 않는 이유",

    "비행기가 뜨는 기본 원리",

    "자동차 안전벨트의 기본 원리",

    "전자레인지가 음식을 데우는 원리",

    "냉장고가 차가워지는 원리",

    "세탁기가 돌아가는 원리",

    "휴대폰이 인터넷에 연결되는 기본 원리",

    "GPS의 기본 원리",

    "신호등의 기본 원리",

    "지하철이 달리는 원리",

    "기차가 레일 위를 달리는 이유",

    "트랙터 바퀴에 물을 넣는 이유",

    "자전거가 넘어지지 않는 기본 원리",

    "비행기 날개가 양력을 만드는 기본 원리"
]


# ============================================================
# 10. 최근 소재 불러오기
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

        if isinstance(data, list):

            return data

    except Exception as e:

        log(
            f"⚠️ 최근 소재 읽기 실패: {e}"
        )

    return []


# ============================================================
# 11. 최근 소재 저장
# ============================================================

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


# ============================================================
# 12. 방향 선택
# ============================================================

def choose_topic():

    recent_topics = load_recent_topics()

    recent_names = []

    for item in recent_topics:

        if isinstance(item, dict):

            topic = item.get(
                "topic",
                ""
            )

            if topic:
                recent_names.append(topic)

    candidates = [
        item
        for item in ALL_TOPICS
        if item["topic"] not in recent_names
    ]

    if not candidates:

        candidates = ALL_TOPICS

    selected = random.choice(
        candidates
    )

    log(
        f"🎯 탐색 분야: {selected['category']}"
    )

    log(
        f"🎯 탐색 방향: {selected['topic']}"
    )

    return selected


# ============================================================
# 13. JSON 추출
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

        try:

            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:

            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    raise ValueError(
        "AI 응답에서 JSON을 찾지 못했습니다."
    )


# ============================================================
# 14. AI 대본 생성
# ============================================================

def generate_script(topic_info):

    category = topic_info["category"]
    direction = topic_info["topic"]

    recent_topics = load_recent_topics()

    recent_text = "\n".join(
        [
            str(item.get("topic", ""))
            for item in recent_topics
            if isinstance(item, dict)
        ]
    )

    log(
        "🧠 AI 소재 발굴 + 대본 생성 시작..."
    )

    prompt = f"""
너는 유튜브 Shorts의
'숨겨진 이유를 찾아주는 지식 콘텐츠'
전문 작가다.

이번 탐색 분야:
{category}

이번 탐색 방향:
{direction}


============================================================
[최우선 규칙 — 이미 다 아는 거 필터]
============================================================

이번 작업에서 가장 중요한 것은
'사람들이 이미 너무 많이 알고 있는 소재를 피하는 것'이다.

시청자가 제목을 보는 순간
"그거 나도 아는데?"
라고 말할 가능성이 높은 소재는 탈락시킨다.

예:

- 하늘이 파란 이유
- 무지개가 생기는 이유
- 비행기가 나는 기본 원리
- 전자레인지가 작동하는 기본 원리
- 냉장고가 차가워지는 원리
- 지구가 둥근 이유
- 중력의 기본 원리

이런 소재는 사용하지 마라.

대신

'매일 볼 수 있지만 왜 그런지 모르는 것'

'이상하게 생겼지만 실제로는 이유가 있는 것'

'고장처럼 보이지만 정상적인 것'

'일부러 불편하거나 이상하게 만들어진 것'

'사람들이 기능을 다른 이유로 착각하는 것'

'시설물이나 기계의 숨겨진 구조'

같은 소재를 우선한다.


============================================================
[콘텐츠 엔진]
============================================================

다음 구조를 사용한다.

1. 이상한 장면
2. "왜 이렇게 하지?"라는 질문
3. 사람들이 예상하는 일반적인 이유
4. 그런데 실제 문제는 따로 있음
5. 기술/자연/역사적 해결책 등장
6. 원리 설명
7. 예상 밖의 디테일
8. 마지막에 의미를 다시 뒤집음

핵심은 단순한 정보 전달이 아니라

"아, 그래서 저렇게 생긴 거였구나."

라는 인식 전환이다.


============================================================
[소재 선정]
============================================================

반드시 하나의 구체적인 실제 소재를 선택한다.

추상적인 주제는 안 된다.

나쁜 예:

"자동차 기술"

"우주의 신비"

"동물의 놀라운 능력"

좋은 예:

"도로 옆에 일부러 만들어 놓은 작은 계단 구조"

"농기계가 먼지를 스스로 털어내는 방식"

"배를 만들 때 거대한 구덩이에 물을 넣는 이유"

처럼 하나의 실제 대상을 선택한다.


============================================================
[기존 영상과 중복 금지]
============================================================

다음은 이미 분석/제작했던 소재이므로
절대 반복하지 않는다.

- 기차 커브의 캔트
- 한강 교각 세굴
- 고속도로 비탈면 소단
- 조선소 드라이 도크
- 트랙터 바퀴 물 채우기
- 농기계 라디에이터 자동 청소
- 레오파드 물범
- 헤어리 크로아상
- 초대형 에어 시더


============================================================
[최근 제작 소재]
============================================================

{recent_text}


============================================================
[사실성]
============================================================

실제로 존재하는 현상, 시설, 기술, 생물 또는 사건만 사용한다.

확인되지 않은 인터넷 괴담을 사실처럼 말하지 않는다.

가짜 통계와 가짜 연구 결과를 만들지 않는다.

정확한 숫자를 확신할 수 없다면
숫자를 억지로 만들지 않는다.


============================================================
[영상 길이]
============================================================

목표:

75~90초

장면:

12~13개

각 장면은 짧고 강하게 작성한다.

한 장면에 너무 많은 정보를 넣지 않는다.


============================================================
[대본 구조]
============================================================

SCENE 1
가장 이상하거나 충격적인 장면.

SCENE 2
"그런데 왜?"라는 질문.

SCENE 3~5
문제와 배경.

SCENE 6~9
해결 방법과 원리.

SCENE 10~11
가장 의외인 사실.

SCENE 12~13
전체 의미를 정리하면서
시청자가 처음 장면을 다시 생각하게 만든다.


============================================================
[후킹]
============================================================

첫 문장은 설명하지 말고
호기심을 만들어라.

좋은 방향:

"이건 고장 난 게 아닙니다."

"일부러 이렇게 만들어 놓은 겁니다."

"사실 이 구조물은 무너지는 걸 전제로 합니다."

"여기에는 이상한 이유가 하나 있습니다."

단, 소재와 맞지 않는 억지 후킹은 금지한다.


============================================================
[Pexels 검색어]
============================================================

각 장면마다 영어 검색어를 만든다.

2~5개의 영어 단어.

반드시 실제로 화면에 보여줄 수 있는
구체적인 장면이어야 한다.

좋은 예:

"tractor radiator cleaning"

"railway curved track"

"bridge concrete pillar"

"construction slope road"

"dry dock shipyard"

"farm tractor field"

나쁜 예:

"technology"

"science"

"interesting"

"amazing"

"nature"

"history"

"space"


============================================================
[대사와 화면의 1:1 대응]
============================================================

text가

"기둥 앞에서 물살이 갈라집니다."

라면

keyword는

"river bridge pillar"

처럼 실제 화면에
기둥과 물이 나와야 한다.

대사와 관계없는 영상을 검색하지 않는다.


============================================================
[제목]
============================================================

제목은 Shorts 스타일로 만든다.

좋은 제목:

"무너질 걸 알고 만든 계단"

"왜 이 기계는 먼지를 반대로 뿜을까?"

"배를 만들려고 거대한 구덩이를 판 이유"

나쁜 제목:

"놀라운 과학 이야기"

"신기한 기술"

"재미있는 사실"


============================================================
[출력]
============================================================

반드시 JSON 객체 하나만 출력한다.

{{
  "title": "영상 제목",
  "topic": "실제 선택한 구체적 소재",
  "category": "{category}",
  "novelty_reason": "왜 사람들이 잘 모를 만한지",
  "scenes": [
    {{
      "text": "짧은 대사",
      "keyword": "specific visual English search query"
    }}
  ]
}}

반드시 12~13개의 scenes를 만든다.

JSON 외의 설명은 출력하지 않는다.
"""

    response = openai.chat.completions.create(

        model="gpt-4o-mini",

        messages=[
            {
                "role": "system",
                "content": (
                    "너는 사실 기반 "
                    "유튜브 Shorts 소재 발굴 및 "
                    "대본 전문가다. "
                    "가장 중요한 목표는 "
                    "'이미 다 아는 상식'을 피하고 "
                    "'일상에서 보지만 이유를 모르는 "
                    "구체적인 소재'를 찾는 것이다."
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

    if not isinstance(
        result,
        dict
    ):

        raise ValueError(
            "AI 결과가 객체가 아닙니다."
        )

    scenes = result.get(
        "scenes",
        []
    )

    if not isinstance(
        scenes,
        list
    ):

        raise ValueError(
            "scenes가 배열이 아닙니다."
        )

    cleaned = []

    for scene in scenes:

        if not isinstance(
            scene,
            dict
        ):

            continue

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

        if not keyword:
            raise ValueError(
                "검색어가 없는 장면이 있습니다."
            )

        cleaned.append(
            {
                "text": text,
                "keyword": keyword
            }
        )

    if len(cleaned) < MIN_SCENES:

        raise ValueError(
            f"장면 수 부족: "
            f"{len(cleaned)}개"
        )

    result["scenes"] = cleaned[
        :MAX_SCENES
    ]

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

    if not title:
        raise ValueError(
            "AI가 제목을 만들지 않았습니다."
        )

    if not topic:
        raise ValueError(
            "AI가 실제 소재를 만들지 않았습니다."
        )

    # --------------------------------------------------------
    # 흔한 소재 필터
    # --------------------------------------------------------

    topic_lower = topic.lower()

    for banned in COMMON_KNOWLEDGE_PATTERNS:

        if banned.lower() in topic_lower:

            raise ValueError(
                "🚫 이미 너무 잘 알려진 소재로 판단됨: "
                f"{topic}"
            )

    # --------------------------------------------------------
    # 최근 소재 중복 검사
    # --------------------------------------------------------

    for item in load_recent_topics():

        if not isinstance(
            item,
            dict
        ):
            continue

        old_topic = str(
            item.get(
                "topic",
                ""
            )
        ).strip()

        if not old_topic:
            continue

        if (
            topic == old_topic
            or topic in old_topic
            or old_topic in topic
        ):

            raise ValueError(
                "🚫 최근 소재와 중복됨: "
                f"{topic}"
            )

    result["category"] = category

    log("")
    log("======================================")
    log("🧠 AI 소재 발굴 결과")
    log("======================================")

    log(
        f"📌 제목: {title}"
    )

    log(
        f"🔎 실제 소재: {topic}"
    )

    log(
        "💡 신규성 이유: "
        f"{result.get('novelty_reason', '없음')}"
    )

    log(
        f"🎬 장면 수: "
        f"{len(result['scenes'])}"
    )

    log("")

    for idx, scene in enumerate(
        result["scenes"]
    ):

        log(
            f"{idx + 1:02d}. "
            f"{scene['keyword']}"
        )

    log("")

    # --------------------------------------------------------
    # 최근 소재 기록
    # --------------------------------------------------------

    recent = load_recent_topics()

    recent.append(
        {
            "topic": topic,
            "title": title,
            "category": category,
            "created_at": datetime.now().isoformat()
        }
    )

    save_recent_topics(
        recent
    )

    return result


# ============================================================
# 15. TTS
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
# 16. 총 영상 길이 확인
# ============================================================

def check_total_duration(
    scene_clips
):

    if not scene_clips:

        raise RuntimeError(
            "장면이 없습니다."
        )

    total_duration = sum(
        float(
            clip.duration or 0
        )
        for clip in scene_clips
    )

    log(
        f"⏱️ 현재 총 영상 길이: "
        f"{total_duration:.2f}초"
    )

    if total_duration < TARGET_MIN_SECONDS:

        raise RuntimeError(
            f"영상이 너무 짧습니다: "
            f"{total_duration:.2f}초 "
            f"(최소 {TARGET_MIN_SECONDS}초)"
        )

    if total_duration > TARGET_MAX_SECONDS:

        raise RuntimeError(
            f"영상이 너무 깁니다: "
            f"{total_duration:.2f}초 "
            f"(최대 {TARGET_MAX_SECONDS}초)"
        )

    log(
        "✅ 영상 길이 조건 통과"
    )

    return total_duration


# ============================================================
# 17. 최종 영상 렌더링
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
# 18. 결과 요약
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

    scenes = script_data.get(
        "scenes",
        []
    )

    novelty = script_data.get(
        "novelty_reason",
        ""
    )

    message = (
        "🎬 Shorts 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: {len(scenes)}개\n\n"
        f"💡 신규성: {novelty}\n\n"
        "📦 영상 전송 중..."
    )

    send_telegram_message(
        message
    )


# ============================================================
# 19. 임시 파일 정리
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
# 20. 메인
# ============================================================

def main():

    start_time = time.time()

    scene_clips = []

    try:

        log(
            "======================================"
        )

        log(
            "🚀 SHORTS GENERATOR START"
        )

        log(
            "======================================"
        )

        # ----------------------------------------------------
        # 환경변수
        # ----------------------------------------------------

        validate_environment()

        # ----------------------------------------------------
        # 탐색 방향
        # ----------------------------------------------------

        topic_info = choose_topic()

        # ----------------------------------------------------
        # AI 소재 + 대본
        # ----------------------------------------------------

        script_data = generate_script(
            topic_info
        )

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

                if scene is None:

                    raise RuntimeError(
                        "create_scene()가 "
                        "None을 반환했습니다."
                    )

                scene_clips.append(
                    scene
                )

                log(
                    f"✅ SCENE {idx + 1} 완료"
                )

            except Exception as e:

                log(
                    f"❌ SCENE {idx + 1} 실패: {e}"
                )

                raise

        # ----------------------------------------------------
        # 총 길이 검증
        # ----------------------------------------------------

        total_duration = (
            check_total_duration(
                scene_clips
            )
        )

        # ----------------------------------------------------
        # 최종 영상
        # ----------------------------------------------------

        final_path = (
            render_final_video(
                scene_clips
            )
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

        log(
            "======================================"
        )

        log(
            "🎉 SHORTS GENERATOR COMPLETE"
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
            f"💀 SHORTS GENERATOR ERROR: {e}"
        )

        log(
            "======================================"
        )

        send_telegram_message(
            "🚨 Shorts 생성 실패\n\n"
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
# 21. 실행
# ============================================================

if __name__ == "__main__":

    main()
