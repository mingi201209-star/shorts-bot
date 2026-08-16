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
# 1. 큰 주제 방향 선택
# 2. "이미 다 아는 이야기인가?" 필터
# 3. 구체적인 실제 소재 선정
# 4. 의외성/신선도 검사
# 5. Shorts 대본 생성
# 6. 장면별 시각 검색어 생성
# 7. 한국어 TTS
# 8. Pexels 영상 + 장면 생성
# 9. 전체 영상 합성
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

# 평범한 소재를 걸러내는 기준
MIN_NOVELTY_SCORE = 7

# AI가 소재를 다시 뽑을 최대 횟수
MAX_SCRIPT_ATTEMPTS = 3


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
# 7. 토픽 방향
# ============================================================
#
# 중요:
#
# 여기 들어가는 것은 "영상 소재"가 아니다.
#
# AI가 여기서 하나의 구체적인 실제 소재를 찾아낸다.
#
# 예:
#
# "교통에 관한 신기한 사실"
#
# ↓
#
# "기차가 커브에서 안 넘어지도록 바깥 레일을 높이는 이유"
#
# 처럼 변환한다.
#
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
# 8. 전체 방향 풀 생성
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
# 9. 최근 소재 불러오기
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
# 10. 최근 소재 저장
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
# 11. 최근 소재 이름 추출
# ============================================================

def get_recent_topic_names():

    recent = load_recent_topics()

    names = []

    for item in recent:

        if isinstance(item, dict):

            topic = item.get(
                "topic",
                ""
            )

            if topic:
                names.append(topic)

        elif isinstance(item, str):

            names.append(item)

    return names


# ============================================================
# 12. 방향 선택
# ============================================================

def choose_topic_direction():

    recent_topics = get_recent_topic_names()

    candidates = []

    for item in ALL_TOPICS:

        # 방향 자체가 최근 소재와 완전히 같은 경우만 제외
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

    # 전체 JSON
    try:

        return json.loads(text)

    except Exception:
        pass

    # 배열
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

    # 객체
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
# 14. 소재 금지/주의 키워드
# ============================================================
#
# "누구나 아는 소재"를 완전히 판별하는 것은 AI 판단이
# 필요하지만, 명백하게 흔한 소재는 1차적으로 제거한다.
#
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
    "여름에는 덥"
]


def looks_too_common(topic):

    if not topic:
        return True

    normalized = topic.replace(
        " ",
        ""
    ).lower()

    for keyword in COMMON_KNOWLEDGE_KEYWORDS:

        k = keyword.replace(
            " ",
            ""
        ).lower()

        if k in normalized:
            return True

    return False


# ============================================================
# 15. AI 대본 생성
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
        "🧠 AI 소재 + 대본 생성 시작..."
    )

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1
    ):

        log(
            f"🔎 소재 탐색 {attempt}/"
            f"{MAX_SCRIPT_ATTEMPTS}"
        )

        prompt = f"""
너는 유튜브 Shorts 전문 콘텐츠 디렉터다.

이번 콘텐츠 방향:
{direction}

분야:
{category}


============================================================
[가장 중요한 엔진]
============================================================

이번 영상은 단순한 상식 전달이 아니다.

시청자가 처음 보면

"어? 왜 저렇지?"
"저게 저런 이유였어?"
"처음 알았는데?"

라고 느끼는 소재를 찾아야 한다.

특히

"이거 거의 모든 사람이 이미 아는 사실 아닌가?"

라는 느낌이 드는 소재는 탈락시켜라.


============================================================
[소재 선정]
============================================================

방향을 그대로 영상 제목으로 사용하지 마라.

반드시 하나의 구체적인 실제 소재로 좁혀라.

좋은 방향:

"교통시설의 숨은 설계"

좋은 실제 소재:

"기차가 커브를 돌 때 바깥쪽 레일을 높이는 이유"

좋지 않은 소재:

"기차는 커브에서 안전하게 달린다"

또 다른 좋은 방향:

"일상 속 숨은 기술"

좋은 실제 소재:

"대형 트랙터 타이어에 액체를 넣는 이유"

핵심은
평범한 장면 속에 숨어 있는
의외의 기능이다.


============================================================
[신선도 필터]
============================================================

다음 질문을 스스로 먼저 평가한다.

1. 한국의 일반적인 성인이 이미 대부분 알고 있을 가능성이 높은가?
2. 유튜브 Shorts에서 너무 흔하게 본 주제인가?
3. 제목만 봐도 답을 예상할 수 있는가?
4. 단순한 "놀라운 사실" 하나로 끝나는가?

하나라도 강하게 그렇다면
소재를 바꿔라.

novelty_score는 1~10으로 평가한다.

7 미만이면 실패다.

가능하면 8~10인 소재를 선택한다.


============================================================
[이전 사용 소재]
============================================================

다음 소재와 같거나
사실상 같은 내용은 사용하지 마라.

{recent_text}


============================================================
[스토리 엔진]
============================================================

대본은 다음 흐름을 따른다.

1. 이상한 장면 또는 의외의 사실
2. "왜?"라는 질문
3. 실제로 생기는 문제
4. 사람들이 생각할 법한 일반적인 해결책
5. 그런데 그 방법에는 한계가 있음
6. 그래서 전혀 다른 방식으로 해결
7. 핵심 원리를 쉬운 말로 설명
8. 실제 구조/과정/사례
9. 일상적인 다른 사례로 확장
10. 마지막에 납득되는 결론


============================================================
[중요]
============================================================

공학만 고집하지 마라.

과학,
자연,
동물,
역사,
지리,
생활,
기술

모두 가능하다.

단,

"정보를 알려주는 영상"

보다

"평범하게 보이던 것이 사실은 이런 이유로 존재한다"

라는 느낌을 우선한다.


============================================================
[길이]
============================================================

총 영상 길이:

75~90초

장면:

12~13개

각 장면의 대사는
너무 짧은 한 문장이 아니라
실제로 TTS로 읽었을 때
전체 영상이 75~90초가 되도록 작성한다.

전체 대사 분량은
대략 300~400자 범위를 목표로 한다.


============================================================
[장면]
============================================================

1번:
가장 강력한 시각적 후킹

2번:
무슨 일이 벌어지는지

3~5번:
문제와 배경

6~9번:
핵심 원리와 해결

10~11번:
가장 의외인 사실

12~13번:
확장과 결론


============================================================
[검색어]
============================================================

각 장면의 keyword는
Pexels에서 실제 영상을 찾기 위한
영어 검색어다.

2~5개의 영어 단어.

반드시 장면 대사와
직접적인 시각적 관계가 있어야 한다.

좋은 예:

"tractor muddy field"

"train railway curve"

"bridge concrete pillar water"

"large ship dry dock"

"mountain road slope"

"ocean predator underwater"

나쁜 예:

"science"

"technology"

"nature"

"interesting"

"amazing"

"space"


============================================================
[제목]
============================================================

제목은 호기심을 만든다.

가능하면

"왜 ~일까?"
"~하는 진짜 이유"
"~인데 사실은 ~입니다"
"사람들이 잘 모르는 ~"

같은 구조를 사용한다.

단, 낚시성 과장은 금지한다.


============================================================
[사실성]
============================================================

확인되지 않은 인터넷 괴담을
사실처럼 쓰지 마라.

확실하지 않은 숫자는 만들지 마라.

가짜 연구 결과를 만들지 마라.


============================================================
[마무리]
============================================================

가능하면 마지막은

"그래서 우리가 보는 ~는
이렇게 만들어진 겁니다."

처럼

"겉으로 보이는 결과 뒤에는
명확한 이유가 있었다"

는 느낌으로 끝낸다.


============================================================
[출력]
============================================================

반드시 JSON 객체 하나만 출력한다.

JSON 외 설명 금지.

형식:

{{
  "title": "영상 제목",
  "topic": "구체적인 실제 소재",
  "category": "{category}",
  "novelty_score": 8,
  "scenes": [
    {{
      "text": "대사",
      "keyword": "specific visual keyword"
    }}
  ]
}}

반드시 12~13개 scenes.

keyword는 서로 가능하면 다르게 작성한다.
"""

        try:

            response = openai.chat.completions.create(

                model="gpt-4o-mini",

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "너는 사실 기반 "
                            "유튜브 Shorts의 "
                            "콘텐츠 디렉터다. "
                            "가장 중요한 것은 "
                            "평범한 상식이 아니라 "
                            "의외성이 있는 실제 소재를 "
                            "발견하는 것이다."
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

            actual_topic = str(
                result.get(
                    "topic",
                    ""
                )
            ).strip()

            novelty_score = result.get(
                "novelty_score",
                0
            )

            try:

                novelty_score = int(
                    novelty_score
                )

            except Exception:

                novelty_score = 0

            log(
                f"🧠 선택 소재: {actual_topic}"
            )

            log(
                f"✨ 신선도 점수: "
                f"{novelty_score}/10"
            )

            # ----------------------------------------
            # 1차 필터
            # ----------------------------------------

            if looks_too_common(
                actual_topic
            ):

                log(
                    "🚫 너무 흔한 소재 → 폐기"
                )

                continue

            # ----------------------------------------
            # 2차 필터
            # ----------------------------------------

            if actual_topic in recent_topics:

                log(
                    "🚫 최근 사용 소재 → 폐기"
                )

                continue

            # ----------------------------------------
            # 3차 신선도
            # ----------------------------------------

            if novelty_score < MIN_NOVELTY_SCORE:

                log(
                    "🚫 신선도 점수 부족 → 재선정"
                )

                continue

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

            cleaned_scenes = []

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

                    keyword = (
                        "documentary technology"
                    )

                cleaned_scenes.append(
                    {
                        "text": text,
                        "keyword": keyword
                    }
                )

            if len(
                cleaned_scenes
            ) < MIN_SCENES:

                raise ValueError(
                    "장면 수 부족: "
                    f"{len(cleaned_scenes)}개"
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

            result["novelty_score"] = (
                novelty_score
            )

            log(
                "======================================"
            )

            log(
                "🎯 소재 선정 성공"
            )

            log(
                f"🧠 소재: {actual_topic}"
            )

            log(
                f"✨ 신선도: "
                f"{novelty_score}/10"
            )

            log(
                f"📝 제목: "
                f"{result['title']}"
            )

            log(
                f"🎬 장면: "
                f"{len(result['scenes'])}개"
            )

            log(
                "======================================"
            )

            log(
                "🔎 장면별 검색어:"
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
                f"⚠️ 대본 생성 시도 실패: {e}"
            )

    raise RuntimeError(
        "신선도 기준을 통과하는 "
        "소재를 찾지 못했습니다."
    )


# ============================================================
# 16. 실제 사용 소재 저장
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
# 17. TTS
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
# 18. 전체 장면 길이 검사
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
            "⚠️ 목표보다 짧습니다: "
            f"{TARGET_MIN_SECONDS}초 미만"
        )

    elif total > TARGET_MAX_SECONDS:

        log(
            "⚠️ 목표보다 깁니다: "
            f"{TARGET_MAX_SECONDS}초 초과"
        )

    else:

        log(
            "✅ Shorts 목표 길이 통과"
        )

    return total


# ============================================================
# 19. 최종 영상 렌더링
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
# 20. 결과 요약
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

    scenes = script_data.get(
        "scenes",
        []
    )

    message = (
        "🎬 Shorts 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"✨ 신선도: {novelty}/10\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: {len(scenes)}개\n\n"
        "📦 영상 전송 중..."
    )

    send_telegram_message(
        message
    )


# ============================================================
# 21. 임시 파일 정리
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
# 22. 메인
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
        # 방향 선택
        # ----------------------------------------------------

        topic_info = (
            choose_topic_direction()
        )

        # ----------------------------------------------------
        # 소재 + 대본
        # ----------------------------------------------------

        script_data = (
            generate_script(
                topic_info
            )
        )

        scenes = script_data.get(
            "scenes",
            []
        )

        if not scenes:

            raise RuntimeError(
                "AI가 장면을 생성하지 않았습니다."
            )

        # ----------------------------------------------------
        # 실제 소재 저장
        # ----------------------------------------------------

        remember_used_topic(
            script_data
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
        # 총 길이
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
# 23. 실행
# ============================================================

if __name__ == "__main__":

    main()
