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
# Shorts Generator V3.0
# ============================================================
#
# V3 핵심 변경
#
# 1. 소재 트래픽 잠재력 검사
# 2. 첫 3초 후킹 강제 검사
# 3. 위험/비밀/의외성 기반 오프닝
# 4. 단순 설명조 오프닝 금지
# 5. B-roll 맥락 검증
# 6. 장면별 검색어 구체화
# 7. 검증 실패 시 렌더링 전 재생성
# 8. 작업 상태 저장
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

WORK_STATE_FILE = "work_state.json"

MAX_RECENT_TOPICS = 20


# ============================================================
# 3. V3 엔진 규칙
# ============================================================

V3_VERSION = "3.0"

MIN_NOVELTY_SCORE = 7

MIN_TRAFFIC_SCORE = 7

MIN_HOOK_SCORE = 8

MIN_BROLL_SCORE = 8

MAX_SCRIPT_ATTEMPTS = 5


RULE_HOOKING_FORCE = {

    "ban_descriptive_opening": True,

    "mandatory_hook_type": [
        "danger",
        "secret",
        "unexpected",
        "curiosity",
        "shock"
    ],

    "first_scene_must_be_hook": True,

    "first_3_seconds_critical": True
}


RULE_TRAFFIC_POTENTIAL = {

    "min_public_interest": 7,

    "require_emotional_trigger": [
        "fear",
        "curiosity",
        "shock",
        "surprise"
    ],

    "reject_low_interest_technical_topic": True
}


RULE_BROLL_INTEGRITY = {

    "context_match_score_min": 8,

    "random_mix_ban": True,

    "generic_keyword_ban": True
}


# ============================================================
# 4. 로그
# ============================================================

def log(message):

    now = datetime.now().strftime("%H:%M:%S")

    print(
        f"[{now}] {message}",
        flush=True
    )


# ============================================================
# 5. 작업 상태 저장
# ============================================================

def save_work_state(
    current_task,
    status="in_progress",
    data=None
):

    state = {

        "version": V3_VERSION,

        "current_task": current_task,

        "status": status,

        "updated_at": datetime.now().isoformat(),

        "data": data or {}
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
            f"💾 작업 상태 저장: {current_task}"
        )

    except Exception as e:

        log(
            f"⚠️ 작업 상태 저장 실패: {e}"
        )


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

            return json.load(f)

    except Exception as e:

        log(
            f"⚠️ 작업 상태 읽기 실패: {e}"
        )

        return None


# ============================================================
# 6. Telegram 메시지
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
        "https://api.telegram.org/"
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
# 7. Telegram 영상 전송
# ============================================================

def send_telegram_video(video_path):

    if not TELEGRAM_BOT_TOKEN:
        return

    if not TELEGRAM_CHAT_ID:
        return

    if not os.path.exists(video_path):

        log(
            f"⚠️ 전송할 영상 없음: {video_path}"
        )

        return

    url = (
        "https://api.telegram.org/"
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

    except Exception as e:

        log(
            f"⚠️ Telegram 영상 전송 에러: {e}"
        )


# ============================================================
# 8. 환경변수 검사
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
# 9. 토픽 풀
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
# 10. 최근 소재
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

        return data if isinstance(
            data,
            list
        ) else []

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
# 11. 방향 선택
# ============================================================

def choose_topic_direction():

    recent_topics = get_recent_topic_names()

    candidates = [

        item

        for item in ALL_TOPICS

        if item["topic"]
        not in recent_topics
    ]

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

    save_work_state(
        "topic_direction",
        data=selected
    )

    return selected


# ============================================================
# 12. JSON 추출
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

    if start != -1 and end > start:

        try:

            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:

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
# 13. 너무 흔한 소재 필터
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
# 14. V3 후킹 검사
# ============================================================

BANNED_OPENING_PATTERNS = [

    "있는 모습",
    "하는 모습",
    "보이는 모습",
    "장면입니다",
    "모습입니다",
    "살펴보겠습니다",
    "알아보겠습니다",
    "설명하겠습니다",
    "오늘은",
    "이번 영상에서는",
    "소개해드리겠습니다"
]


HOOK_KEYWORDS = [

    "왜",
    "사실",
    "그런데",
    "놀랍게도",
    "의외로",
    "위험",
    "소름",
    "비밀",
    "진짜 이유",
    "모르는",
    "생각과 다릅니다",
    "반대",
    "절대",
    "숨겨진"
]


def validate_hook(scene):

    text = str(
        scene.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        return False, 0

    for banned in BANNED_OPENING_PATTERNS:

        if banned in text:

            return (
                False,
                2
            )

    score = 0

    for keyword in HOOK_KEYWORDS:

        if keyword in text:

            score += 2

    if "?" in text:

        score += 2

    if len(text) >= 15:

        score += 1

    score = min(
        score,
        10
    )

    passed = (
        score >= MIN_HOOK_SCORE
    )

    return passed, score


# ============================================================
# 15. B-roll 검색어 검사
# ============================================================

GENERIC_BROLL_KEYWORDS = {

    "science",
    "technology",
    "nature",
    "interesting",
    "amazing",
    "space",
    "documentary",
    "concept",
    "background",
    "abstract",
    "future",
    "innovation"
}


def validate_keyword(keyword):

    if not keyword:

        return False

    words = keyword.lower().split()

    if len(words) < 2:

        return False

    if all(
        word in GENERIC_BROLL_KEYWORDS
        for word in words
    ):

        return False

    if any(
        word in GENERIC_BROLL_KEYWORDS
        for word in words
    ) and len(words) <= 2:

        return False

    return True


# ============================================================
# 16. 장면 구조 검사
# ============================================================

def validate_scene_structure(
    scenes
):

    if not isinstance(
        scenes,
        list
    ):

        return False, "scenes가 배열이 아님"

    if not (
        MIN_SCENES
        <= len(scenes)
        <= MAX_SCENES
    ):

        return (
            False,
            f"장면 수 오류: {len(scenes)}"
        )

    for idx, scene in enumerate(
        scenes
    ):

        if not isinstance(
            scene,
            dict
        ):

            return (
                False,
                f"{idx + 1}번 장면 객체 오류"
            )

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

            return (
                False,
                f"{idx + 1}번 대사 없음"
            )

        if not validate_keyword(
            keyword
        ):

            return (
                False,
                f"{idx + 1}번 검색어가 너무 일반적"
            )

    return True, "통과"


# ============================================================
# 17. AI V3 품질 심사
# ============================================================

def judge_script_v3(
    result
):

    scenes = result.get(
        "scenes",
        []
    )

    if not scenes:

        raise ValueError(
            "심사할 장면이 없습니다."
        )

    compact_scenes = []

    for idx, scene in enumerate(
        scenes
    ):

        compact_scenes.append(
            {
                "scene": idx + 1,
                "text": scene.get(
                    "text",
                    ""
                ),
                "keyword": scene.get(
                    "keyword",
                    ""
                )
            }
        )

    judge_prompt = f"""
너는 Shorts 콘텐츠 품질 심사관이다.

아래 영상을 아주 냉정하게 평가하라.

{json.dumps(
    {
        "title": result.get("title", ""),
        "topic": result.get("topic", ""),
        "scenes": compact_scenes
    },
    ensure_ascii=False,
    indent=2
)}

다음 기준으로 1~10점을 준다.

1. traffic_score
   일반 대중이 보고 싶어할 가능성

2. hook_score
   첫 장면이 스크롤을 멈추게 하는 정도

3. broll_score
   대사와 검색 영상의 실제 맥락 일치도

4. novelty_score
   흔하지 않은 소재인가

5. overall_score
   전체 Shorts로서의 완성도

특히 첫 장면이

"~하는 모습입니다"
"오늘은 ~를 알아보겠습니다"
"~에 대해 설명하겠습니다"

같은 식이면 hook_score를 낮게 평가하라.

단순히 대사에 "전선"이라는 단어가 나오고
전선 영상을 붙이는 수준도 broll_score를 낮게 평가하라.

반드시 JSON 하나만 출력한다.

{{
  "traffic_score": 8,
  "hook_score": 9,
  "broll_score": 8,
  "novelty_score": 8,
  "overall_score": 8,
  "reason": "짧은 평가"
}}
"""

    response = openai.chat.completions.create(

        model="gpt-4o-mini",

        messages=[
            {
                "role": "system",
                "content": (
                    "너는 매우 엄격한 "
                    "YouTube Shorts 품질 심사관이다."
                )
            },
            {
                "role": "user",
                "content": judge_prompt
            }
        ],

        temperature=0.2
    )

    content = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    return extract_json(
        content
    )


# ============================================================
# 18. V3 검증
# ============================================================

def validate_script_v3(
    result
):

    log(
        "🔬 V3 품질 검증 시작"
    )

    scenes = result.get(
        "scenes",
        []
    )

    # ----------------------------------------
    # 장면 구조
    # ----------------------------------------

    structure_ok, structure_reason = (
        validate_scene_structure(
            scenes
        )
    )

    if not structure_ok:

        log(
            f"🚫 구조 검사 실패: "
            f"{structure_reason}"
        )

        return False

    # ----------------------------------------
    # 첫 장면 후킹
    # ----------------------------------------

    hook_ok, hook_score = validate_hook(
        scenes[0]
    )

    log(
        f"🪝 첫 장면 Hook: "
        f"{hook_score}/10"
    )

    if not hook_ok:

        log(
            "🚫 첫 3초 후킹 실패"
        )

        return False

    # ----------------------------------------
    # 모든 검색어
    # ----------------------------------------

    for idx, scene in enumerate(
        scenes
    ):

        if not validate_keyword(
            scene.get(
                "keyword",
                ""
            )
        ):

            log(
                f"🚫 B-roll 검색어 실패: "
                f"scene {idx + 1}"
            )

            return False

    # ----------------------------------------
    # AI 심사
    # ----------------------------------------

    judge = judge_script_v3(
        result
    )

    traffic_score = int(
        judge.get(
            "traffic_score",
            0
        )
    )

    judge_hook_score = int(
        judge.get(
            "hook_score",
            0
        )
    )

    broll_score = int(
        judge.get(
            "broll_score",
            0
        )
    )

    novelty_score = int(
        judge.get(
            "novelty_score",
            0
        )
    )

    overall_score = int(
        judge.get(
            "overall_score",
            0
        )
    )

    log(
        "======================================"
    )

    log(
        f"📈 Traffic: {traffic_score}/10"
    )

    log(
        f"🪝 Hook: {judge_hook_score}/10"
    )

    log(
        f"🎥 B-roll: {broll_score}/10"
    )

    log(
        f"✨ Novelty: {novelty_score}/10"
    )

    log(
        f"🏆 Overall: {overall_score}/10"
    )

    log(
        f"📝 평가: "
        f"{judge.get('reason', '')}"
    )

    log(
        "======================================"
    )

    # ----------------------------------------
    # 최종 필터
    # ----------------------------------------

    if traffic_score < MIN_TRAFFIC_SCORE:

        log(
            "🚫 Traffic 점수 부족"
        )

        return False

    if judge_hook_score < MIN_HOOK_SCORE:

        log(
            "🚫 AI Hook 점수 부족"
        )

        return False

    if broll_score < MIN_BROLL_SCORE:

        log(
            "🚫 B-roll 맥락 점수 부족"
        )

        return False

    if novelty_score < MIN_NOVELTY_SCORE:

        log(
            "🚫 Novelty 점수 부족"
        )

        return False

    if overall_score < 7:

        log(
            "🚫 전체 점수 부족"
        )

        return False

    log(
        "✅ V3 품질 검증 통과"
    )

    result["_v3_judge"] = {

        "traffic_score": traffic_score,

        "hook_score": judge_hook_score,

        "broll_score": broll_score,

        "novelty_score": novelty_score,

        "overall_score": overall_score,

        "reason": judge.get(
            "reason",
            ""
        )
    }

    return True


# ============================================================
# 19. AI 대본 생성
# ============================================================

def generate_script(
    topic_info
):

    category = topic_info[
        "category"
    ]

    direction = topic_info[
        "topic"
    ]

    recent_topics = (
        get_recent_topic_names()
    )

    recent_text = "\n".join(
        f"- {item}"
        for item in recent_topics[-20:]
    )

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1
    ):

        log(
            "======================================"
        )

        log(
            f"🧠 V3 대본 생성 "
            f"{attempt}/{MAX_SCRIPT_ATTEMPTS}"
        )

        save_work_state(
            "script_generation",
            data={
                "attempt": attempt,
                "direction": direction
            }
        )

        prompt = f"""
너는 YouTube Shorts 전문 콘텐츠 디렉터다.

이번 방향:
{direction}

분야:
{category}

============================================================
V3 핵심
============================================================

이번 영상은 절대로 평범한 정보 전달 영상처럼 만들지 마라.

목표는

"어? 저게 왜 저렇게 되어 있지?"

라는 궁금증을 만드는 것이다.

시청자가 이미 알고 있을 법한 상식은 버려라.

============================================================
1. 소재 트래픽 필터
============================================================

일반 시청자가 관심을 가질 만한 소재여야 한다.

특히 다음 감정을 하나 이상 만들어야 한다.

- 호기심
- 놀라움
- 위험 인식
- 의외성
- 충격

단순한 기술 설명,
행정 정보,
교과서적인 원리,
너무 전문적인 안전교육은 피한다.

============================================================
2. 첫 3초
============================================================

첫 장면은 가장 중요하다.

절대로 다음처럼 시작하지 마라.

"오늘은..."
"이번 영상에서는..."
"~하는 모습입니다."
"~를 알아보겠습니다."
"~에 대해 설명하겠습니다."

대신 바로 이상하거나 위험하거나
의외인 사실을 던져라.

예:

"이건 일부러 망가뜨린 것처럼 보이지만, 사실 반대입니다."

"이 도로는 왜 일부러 이렇게 기울어져 있을까요?"

"이 장치가 없으면 이 기계는 생각보다 쉽게 망가집니다."

"사람들이 매일 지나치지만 거의 아무도 이유를 모릅니다."

첫 장면만 보고도
시청자가 다음 장면을 보고 싶어야 한다.

============================================================
3. 스토리
============================================================

다음 구조를 최대한 따른다.

1. 충격/의외의 장면
2. 왜 그런지 질문
3. 실제 문제
4. 일반적인 예상
5. 예상과 다른 해결법
6. 핵심 원리
7. 실제 구조
8. 가장 의외인 사실
9. 다른 사례
10. 결론

============================================================
4. B-roll
============================================================

대사의 단어 하나를 보고
그 단어와 관련된 영상을 붙이지 마라.

영상이 대사의 상황을 실제로 보여줘야 한다.

예를 들어

"기차가 커브에서 바깥쪽으로 밀립니다."

라면

train railway curve

처럼 실제 상황을 보여주는 검색어를 써라.

다음 검색어는 금지한다.

science
technology
nature
interesting
amazing
space
documentary
concept
background

각 keyword는 2~5개의 구체적인 영어 단어.

============================================================
5. 장면 일관성
============================================================

장면마다 장소와 분위기가 갑자기 바뀌지 않게 한다.

하나의 영상처럼 이어져야 한다.

============================================================
6. 길이
============================================================

75~90초.

12~13개 장면.

TTS로 읽었을 때 충분한 대사량을 확보한다.

============================================================
7. 제목
============================================================

과장하지 말고 궁금증을 만든다.

============================================================
8. 사실성
============================================================

확인되지 않은 숫자,
가짜 연구,
인터넷 괴담을 만들지 마라.

============================================================
9. 이전 소재
============================================================

다음 소재와 같거나 사실상 같은 내용은 금지.

{recent_text}

============================================================
출력
============================================================

JSON 하나만 출력한다.

{{
  "title": "영상 제목",
  "topic": "구체적인 실제 소재",
  "category": "{category}",
  "novelty_score": 8,
  "scenes": [
    {{
      "text": "첫 3초를 책임지는 강력한 대사",
      "keyword": "specific visual search"
    }}
  ]
}}

12~13 scenes.
"""

        try:

            response = openai.chat.completions.create(

                model="gpt-4o-mini",

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "YouTube Shorts V3 콘텐츠 디렉터. "
                            "후킹과 대중성을 최우선으로 한다."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=1.0
            )

            result = extract_json(
                response
                .choices[0]
                .message
                .content
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

            if looks_too_common(
                actual_topic
            ):

                log(
                    "🚫 너무 흔한 소재"
                )

                continue

            if actual_topic in recent_topics:

                log(
                    "🚫 최근 사용 소재"
                )

                continue

            scenes = result.get(
                "scenes",
                []
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

            # ----------------------------------------
            # V3 검사
            # ----------------------------------------

            if not validate_script_v3(
                result
            ):

                log(
                    "💥 V3 검사 실패 → 대본 폐기"
                )

                continue

            # ----------------------------------------
            # 통과
            # ----------------------------------------

            log(
                "🎯 V3 대본 최종 승인"
            )

            save_work_state(
                "script_approved",
                status="approved",
                data=result
            )

            return result

        except Exception as e:

            log(
                f"⚠️ 대본 생성 실패: {e}"
            )

    raise RuntimeError(
        "V3 기준을 통과하는 대본을 "
        "찾지 못했습니다."
    )


# ============================================================
# 20. 실제 소재 저장
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
# 21. TTS
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
# 22. 전체 장면 길이 검사
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
            f"⚠️ {TARGET_MIN_SECONDS}초 미만"
        )

    elif total > TARGET_MAX_SECONDS:

        log(
            f"⚠️ {TARGET_MAX_SECONDS}초 초과"
        )

    else:

        log(
            "✅ Shorts 목표 길이 통과"
        )

    return total


# ============================================================
# 23. 최종 영상 렌더링
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

    save_work_state(
        "video_rendering"
    )

    log(
        "🎞️ 모든 장면 합치는 중..."
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
# 24. 결과 요약
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

    judge = script_data.get(
        "_v3_judge",
        {}
    )

    message = (

        "🎬 Shorts V3 생성 완료!\n\n"

        f"📂 분야: {category}\n"

        f"🧠 소재: {topic}\n"

        f"📝 제목: {title}\n"

        f"🎞️ 길이: {duration:.1f}초\n"

        f"🎥 장면: {len(scenes)}개\n\n"

        "📊 V3 검사\n"

        f"🪝 Hook: "
        f"{judge.get('hook_score', '?')}/10\n"

        f"📈 Traffic: "
        f"{judge.get('traffic_score', '?')}/10\n"

        f"🎥 B-roll: "
        f"{judge.get('broll_score', '?')}/10\n"

        f"✨ Novelty: "
        f"{judge.get('novelty_score', '?')}/10\n\n"

        "📦 영상 전송 중..."
    )

    send_telegram_message(
        message
    )


# ============================================================
# 25. 임시 파일 정리
# ============================================================

def cleanup_temp_files():

    log(
        "🧹 임시 파일 정리"
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

        except Exception as e:

            log(
                f"⚠️ 삭제 실패 "
                f"{filename}: {e}"
            )


# ============================================================
# 26. 메인
# ============================================================

def main():

    start_time = time.time()

    scene_clips = []

    try:

        log(
            "======================================"
        )

        log(
            "🚀 SHORTS GENERATOR V3.0 START"
        )

        log(
            "======================================"
        )

        save_work_state(
            "startup"
        )

        # ----------------------------------------
        # 환경
        # ----------------------------------------

        validate_environment()

        # ----------------------------------------
        # 방향
        # ----------------------------------------

        topic_info = (
            choose_topic_direction()
        )

        # ----------------------------------------
        # 대본
        # ----------------------------------------

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

        # ----------------------------------------
        # 소재 저장
        # ----------------------------------------

        remember_used_topic(
            script_data
        )

        save_work_state(
            "scene_generation",
            data=script_data
        )

        log(
            f"📚 총 {len(scenes)}개 장면 처리"
        )

        # ----------------------------------------
        # 장면
        # ----------------------------------------

        for idx, item in enumerate(
            scenes[:MAX_SCENES]
        ):

            log(
                f"🎬 SCENE {idx + 1}/"
                f"{len(scenes)} 시작"
            )

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

        # ----------------------------------------
        # 길이
        # ----------------------------------------

        total_duration = (
            check_total_duration(
                scene_clips
            )
        )

        # ----------------------------------------
        # 렌더링
        # ----------------------------------------

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ----------------------------------------
        # 결과
        # ----------------------------------------

        save_work_state(
            "telegram_delivery",
            data={
                "video": final_path,
                "duration": total_duration
            }
        )

        send_result_summary(
            script_data,
            total_duration
        )

        send_telegram_video(
            final_path
        )

        # ----------------------------------------
        # 완료
        # ----------------------------------------

        elapsed = (
            time.time()
            - start_time
        )

        save_work_state(
            "completed",
            status="completed",
            data={
                "video": final_path,
                "duration": total_duration
            }
        )

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

        save_work_state(
            "error",
            status="failed",
            data={
                "error": str(e)
            }
        )

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
            "🚨 Shorts V3 생성 실패\n\n"
            f"{str(e)[:500]}"
        )

        raise

    finally:

        for clip in scene_clips:

            try:

                clip.close()

            except Exception:
                pass

        cleanup_temp_files()


# ============================================================
# 27. 실행
# ============================================================

if __name__ == "__main__":

    main()
