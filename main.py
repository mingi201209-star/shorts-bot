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
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Shorts Generator
# ============================================================
# 목적:
#   1. 다양한 주제의 유튜브 Shorts 대본 생성
#   2. Pexels 스톡 영상 자동 검색
#   3. 한국어 TTS 생성
#   4. 장면별 자막 생성
#   5. 세로형 1080x1920 영상 합성
#   6. 완성 영상을 Telegram으로 전송
#
# 중요:
#   이 파일 하나만 GitHub Actions에서 실행되도록 설계
# ============================================================


# ============================================================
# 1. 환경 변수
# ============================================================

OPENAI_KEY = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# OpenAI 구버전/현재 코드 호환
openai.api_key = OPENAI_KEY


# ============================================================
# 2. 기본 설정
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

FPS = 30

MAX_SCENES = 13
MIN_SCENES = 10

TARGET_MIN_SECONDS = 75
TARGET_MAX_SECONDS = 90

VIDEO_BITRATE = "5000k"

TTS_VOICE = "ko-KR-InJoonNeural"

OUTPUT_VIDEO = "final_shorts.mp4"

RECENT_TOPICS_FILE = "recent_topics.json"

MAX_RECENT_TOPICS = 10


# ============================================================
# 3. Pillow 호환성 패치
# ============================================================

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS


# ============================================================
# 4. MoviePy Import
# ============================================================

try:
    from moviepy.editor import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        CompositeVideoClip,
        concatenate_videoclips
    )

    from moviepy.video.fx.all import crop, loop

except ImportError:

    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.VideoClip import ImageClip

    from moviepy.video.compositing.CompositeVideoClip import (
        CompositeVideoClip
    )

    from moviepy.video.compositing.concatenate import (
        concatenate_videoclips
    )

    import moviepy.video.fx.crop as crop
    import moviepy.video.fx.loop as loop


# ============================================================
# 5. 로그
# ============================================================

def log(message):
    """GitHub Actions 로그에 보기 좋게 출력"""

    now = datetime.now().strftime("%H:%M:%S")

    print(f"[{now}] {message}")


# ============================================================
# 6. Telegram 메시지
# ============================================================

def send_telegram_message(message):
    """텔레그램 텍스트 알림"""

    if not TELEGRAM_BOT_TOKEN:
        log("Telegram BOT TOKEN 없음")
        return

    if not TELEGRAM_CHAT_ID:
        log("Telegram CHAT ID 없음")
        return

    try:

        url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        response = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": str(message)
            },
            timeout=15
        )

        if not response.ok:
            log(
                f"Telegram 메시지 전송 실패: "
                f"{response.status_code}"
            )

    except Exception as e:

        log(f"Telegram 메시지 에러: {e}")


# ============================================================
# 7. Telegram 영상 전송
# ============================================================

def send_telegram_video(video_path):
    """완성된 Shorts를 Telegram으로 전송"""

    if not TELEGRAM_BOT_TOKEN:
        log("Telegram BOT TOKEN 없음")
        return

    if not TELEGRAM_CHAT_ID:
        log("Telegram CHAT ID 없음")
        return

    if not os.path.exists(video_path):
        log("전송할 영상이 존재하지 않음")
        return

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    )

    try:

        with open(video_path, "rb") as video_file:

            response = requests.post(
                url,

                data={
                    "chat_id": TELEGRAM_CHAT_ID
                },

                files={
                    "video": video_file
                },

                timeout=180
            )

        if response.ok:

            log("Telegram 영상 전송 완료")

        else:

            log(
                f"Telegram 영상 전송 실패: "
                f"{response.status_code}"
            )

            send_telegram_message(
                f"⚠️ 영상 전송 실패 "
                f"(HTTP {response.status_code})"
            )

    except Exception as e:

        log(f"Telegram 영상 전송 에러: {e}")

        send_telegram_message(
            f"⚠️ 영상 전송 에러: {str(e)[:200]}"
        )


# ============================================================
# 8. 필수 환경변수 검사
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
            "필수 환경변수 없음:\n"
            + "\n".join(missing)
        )

        log(error_message)

        send_telegram_message(
            f"🚨 환경변수 오류\n\n{error_message}"
        )

        raise RuntimeError(error_message)

    log("환경변수 검사 완료")


# ============================================================
# 9. 토픽 풀
# ============================================================
#
# 여기서 이번 대수술의 핵심이 시작됨.
#
# 이전:
#   AI에게 그냥 "깊은 과학/역사/미스터리"라고 하면
#   AI가 마음에 드는 소재 하나를 계속 재탕할 수 있음.
#
# 현재:
#   분야별 토픽 풀을 먼저 정하고
#   이번 영상에서 사용할 분야를 무작위/순환 선택.
#
# ============================================================

TOPIC_POOL = {

    "과학": [
        "우주에서 일어나는 이상한 현상",
        "지구에서 실제로 일어나는 극한 자연현상",
        "인간의 몸에서 일어나는 놀라운 현상",
        "동물의 특이한 생존 방식",
        "바다 속에서 발견되는 이상한 현상",
        "빛과 소리에 관한 놀라운 과학",
        "시간과 공간에 관한 과학적 사실",
        "중력과 관련된 흥미로운 현상",
        "물질의 이상한 성질",
        "실험으로 밝혀진 놀라운 과학",
        "기후와 대기의 특이한 현상",
        "지구 내부에서 일어나는 현상"
    ],

    "역사": [
        "역사 속에서 실제로 일어난 이상한 사건",
        "고대 문명의 특이한 기술",
        "사라진 도시와 문명",
        "과거 사람들이 사용했던 기묘한 물건",
        "역사적으로 가장 이상했던 법과 제도",
        "전쟁에서 실제로 사용된 특이한 전략",
        "과거의 생활 방식",
        "역사 속 미스터리",
        "유명한 사건의 숨겨진 뒷이야기",
        "과거의 과학 기술",
        "역사 속 재난",
        "사라진 기록과 유물"
    ],

    "지리": [
        "지구에서 가장 외딴 장소",
        "세계에서 가장 극단적인 지역",
        "지도에서 보면 이상한 장소",
        "국경과 영토에 관한 특이한 사실",
        "세계의 독특한 섬",
        "사람이 살기 힘든 지역",
        "지구에서 가장 추운 곳",
        "지구에서 가장 뜨거운 곳",
        "세계의 특이한 자연 지형",
        "세계의 숨겨진 장소",
        "바다와 관련된 지리적 미스터리",
        "도시의 이상한 지리"
    ],

    "기술": [
        "우리가 매일 사용하는 기술의 탄생 과정",
        "인터넷의 숨겨진 원리",
        "스마트폰에 들어 있는 기술",
        "인공지능의 흥미로운 원리",
        "컴퓨터의 역사",
        "우주 기술",
        "자동차 기술",
        "비행 기술",
        "통신 기술",
        "로봇 기술",
        "반도체 기술",
        "일상 속에 숨어 있는 첨단 기술"
    ],

    "자연": [
        "동물이 보여주는 놀라운 행동",
        "식물의 이상한 생존 전략",
        "세계의 희귀한 생물",
        "극한 환경에서 살아가는 생명체",
        "바다 생물의 특이한 능력",
        "곤충의 놀라운 능력",
        "새들의 특이한 행동",
        "자연에서 발견되는 기묘한 현상",
        "생태계의 숨겨진 관계",
        "동물의 의사소통",
        "자연에서 일어나는 대규모 현상",
        "인간이 잘 모르는 자연의 법칙"
    ],

    "미스터리": [
        "아직 완전히 설명되지 않은 현상",
        "사라진 장소에 관한 이야기",
        "정체가 밝혀지기까지 오래 걸린 사건",
        "이상한 기록으로 남은 사건",
        "과학적으로 조사된 미스터리",
        "바다에서 발견된 미스터리",
        "하늘에서 발견된 이상 현상",
        "고대의 미스터리",
        "정체불명의 물체",
        "실제로 존재하는 이상한 장소",
        "역사 속 미해결 사건",
        "사람들이 오랫동안 오해했던 미스터리"
    ],

    "생활": [
        "일상에서 아무도 알려주지 않는 과학",
        "우리가 매일 보는 물건의 비밀",
        "음식에 관한 놀라운 사실",
        "수면에 관한 흥미로운 사실",
        "소비자가 잘 모르는 제품의 원리",
        "집 안에서 일어나는 과학",
        "도시 생활의 숨겨진 원리",
        "교통에 관한 신기한 사실",
        "건축물의 특이한 설계",
        "사람들의 일상 행동에 관한 과학"
    ],

    "의학_인체": [
        "인간의 뇌에서 일어나는 신기한 현상",
        "인간의 감각에 관한 사실",
        "수면 중 몸에서 일어나는 일",
        "기억과 관련된 흥미로운 현상",
        "운동할 때 몸에서 일어나는 변화",
        "통증과 관련된 과학",
        "인체의 놀라운 방어 시스템",
        "심장과 혈액에 관한 과학",
        "눈과 시각에 관한 현상",
        "귀와 청각에 관한 현상"
    ],

    "경제_사회": [
        "돈의 역사",
        "화폐에 숨겨진 기술",
        "경제에서 일어나는 이상한 현상",
        "사람들이 돈을 사용하는 방식",
        "기업의 독특한 전략",
        "도시와 경제의 관계",
        "소비 심리에 관한 과학",
        "가격이 결정되는 방식",
        "세계 경제의 특이한 사례",
        "역사 속 경제 사건"
    ]
}


# ============================================================
# 10. 전체 토픽 풀 평탄화
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
# 11. 최근 사용 주제 로드
# ============================================================

def load_recent_topics():

    if not os.path.exists(RECENT_TOPICS_FILE):
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
            f"최근 주제 기록 읽기 실패: {e}"
        )

    return []


# ============================================================
# 12. 최근 주제 저장
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
            f"최근 주제 저장 실패: {e}"
        )


# ============================================================
# 13. 이번 영상 주제 선택
# ============================================================

def choose_topic():

    recent_topics = load_recent_topics()

    recent_names = []

    for item in recent_topics:

        if isinstance(item, dict):

            recent_names.append(
                item.get("topic", "")
            )

        elif isinstance(item, str):

            recent_names.append(item)

    candidates = [
        item
        for item in ALL_TOPICS
        if item["topic"] not in recent_names
    ]

    if not candidates:

        candidates = ALL_TOPICS

    selected = random.choice(candidates)

    log(
        f"🎯 선택된 분야: {selected['category']}"
    )

    log(
        f"🎯 선택된 방향: {selected['topic']}"
    )

    recent_topics.append(selected)

    save_recent_topics(recent_topics)

    return selected


# ============================================================
# 14. AI 응답에서 JSON 추출
# ============================================================

def extract_json(text):

    text = text.strip()

    # 코드블록 제거
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

    # 먼저 전체 JSON 시도
    try:

        return json.loads(text)

    except Exception:
        pass

    # 배열 찾기
    array_start = text.find("[")

    array_end = text.rfind("]")

    if (
        array_start != -1
        and array_end != -1
        and array_end > array_start
    ):

        candidate = text[
            array_start:array_end + 1
        ]

        try:

            return json.loads(candidate)

        except Exception:
            pass

    # 객체 찾기
    object_start = text.find("{")

    object_end = text.rfind("}")

    if (
        object_start != -1
        and object_end != -1
        and object_end > object_start
    ):

        candidate = text[
            object_start:object_end + 1
        ]

        try:

            return json.loads(candidate)

        except Exception:
            pass

    raise ValueError(
        "AI 응답에서 JSON을 찾을 수 없습니다."
    )


# ============================================================
# 15. 대본 생성
# ============================================================

def generate_script(topic_info):

    category = topic_info["category"]

    topic = topic_info["topic"]

    log(
        "🧠 AI에게 새로운 대본 요청 중..."
    )

    prompt = f"""
너는 유튜브 Shorts 전문 대본 작가다.

이번 영상의 분야:
{category}

이번 영상의 방향:
{topic}

중요:
이전 영상에서 사용했던 '포인트 네모(Point Nemo)' 같은
특정 소재를 반복하지 마라.

이번에는 반드시 위 방향에 맞는
완전히 다른 하나의 소재를 선택해라.

[목표]

사람들이 처음 들었을 때

"뭐라고?"
"그게 진짜야?"
"왜?"

라고 반응할 만한 소재를 찾아라.

단순한 잡학 상식이 아니라
하나의 흥미로운 이야기가 되도록 구성해라.

[영상 길이]

총 길이:
75초 ~ 90초

장면 수:
12 ~ 13개

각 장면은 짧고 강하게 작성한다.

한 장면당:
약 12 ~ 25자

단, 의미 전달을 위해 필요한 경우
조금 길어도 된다.

[구성]

1. 첫 장면:
강력한 후킹

2. 두 번째:
무슨 일이 일어나는지 설명

3~5:
배경과 핵심 정보

6~9:
구체적인 숫자나 사례

10~11:
반전 또는 가장 놀라운 사실

12~13:
마무리

[중요]

검증되지 않은 인터넷 괴담을
사실처럼 말하지 마라.

실제 과학/역사/지리/기술 등에서
확인 가능한 소재를 우선한다.

숫자가 필요하면 지나치게 세밀한
가짜 숫자를 만들지 마라.

[영상 검색]

keyword는 Pexels에서 검색할 것이다.

고유명사를 사용하지 마라.

예:

bad:
"point nemo"

good:
"deep ocean aerial"

bad:
"Einstein"

good:
"old scientist laboratory"

keyword는 반드시
일반적인 영어 시각 키워드로 작성한다.

[출력]

반드시 JSON 객체 하나만 출력한다.

형식:

{{
  "title": "영상 제목",
  "topic": "선택한 실제 소재",
  "category": "{category}",
  "scenes": [
    {{
      "text": "짧은 대사",
      "keyword": "english visual keyword"
    }}
  ]
}}

절대로 JSON 앞뒤에 설명을 붙이지 마라.
"""

    try:

        response = openai.chat.completions.create(

            model="gpt-4o-mini",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 사실 기반 "
                        "유튜브 Shorts 대본 전문가다."
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

        data = extract_json(content)

        if isinstance(data, list):

            items = data

            result = {
                "title": topic,
                "topic": topic,
                "category": category,
                "scenes": items
            }

        else:

            result = data

        scenes = result.get("scenes", [])

        if not isinstance(scenes, list):

            raise ValueError(
                "scenes가 배열이 아닙니다."
            )

        scenes = [
            scene
            for scene in scenes
            if isinstance(scene, dict)
            and scene.get("text")
        ]

        if len(scenes) < MIN_SCENES:

            raise ValueError(
                f"장면 수 부족: {len(scenes)}"
            )

        result["scenes"] = scenes[:MAX_SCENES]

        log(
            f"✅ 대본 생성 완료: "
            f"{len(result['scenes'])}개 장면"
        )

        log(
            f"📌 실제 소재: "
            f"{result.get('topic', '미상')}"
        )

        return result

    except Exception as e:

        log(
            f"AI 대본 생성 실패: {e}"
        )

        raise


# ============================================================
# 16. TTS
# ============================================================

async def generate_voice(text, output_path):

    communicate = edge_tts.Communicate(
        text,
        TTS_VOICE
    )

    await communicate.save(
        output_path
    )


# ============================================================
# 17. TTS 실행
# ============================================================

def create_voice(text, output_path):

    log(
        f"🎙️ TTS 생성: {text}"
    )

    asyncio.run(
        generate_voice(
            text,
            output_path
        )
    )

    if not os.path.exists(output_path):

        raise RuntimeError(
            "TTS 파일 생성 실패"
        )


# ============================================================
# 18. 안전한 한글 폰트
# ============================================================

def get_safe_korean_font(size):

    font_filename = "NanumGothic.ttf"

    if os.path.exists(font_filename):

        try:

            return ImageFont.truetype(
                font_filename,
                size
            )

        except Exception:
            pass

    font_paths = [

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothicExtraBold.ttf",

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothicBold.ttf",

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothic.ttf",

        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
    ]

    for path in font_paths:

        if os.path.exists(path):

            try:

                return ImageFont.truetype(
                    path,
                    size
                )

            except Exception:
                pass

    log(
        "⚠️ 한글 폰트를 찾지 못해 기본 폰트 사용"
    )

    return ImageFont.load_default()


# ============================================================
# 19. 자막 이미지
# ============================================================

def render_subtitle_image(text):

    target_w = VIDEO_WIDTH

    font_size = 70

    font = get_safe_korean_font(
        font_size
    )

    padding = 40

    img_h = (
        font_size
        + padding * 2
    )

    img = Image.new(
        "RGBA",
        (
            target_w,
            img_h
        ),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(img)

    # 실제 텍스트 크기 계산
    try:

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
            stroke_width=0
        )

        text_width = (
            bbox[2] - bbox[0]
        )

    except Exception:

        text_width = (
            len(text) * font_size
        )

    x = max(
        20,
        int(
            (target_w - text_width)
            / 2
        )
    )

    y = padding

    # 검은색 외곽선
    draw.text(
        (x, y),
        text,
        font=font,
        fill="black",
        stroke_width=8,
        stroke_fill="black"
    )

    # 노란색 본문
    draw.text(
        (x, y),
        text,
        font=font,
        fill="#FFE600",
        stroke_width=2,
        stroke_fill="#FFE600"
    )

    return np.array(img)


# ============================================================
# 20. 자막 분할
# ============================================================

def create_split_subtitles(
    text,
    duration
):

    words = text.split()

    if not words:
        return []

    chunks = []

    current = []

    # 한 번에 너무 많은 단어가 나오지 않도록
    for word in words:

        current.append(word)

        if len(current) >= 2:

            chunks.append(
                " ".join(current)
            )

            current = []

    if current:

        chunks.append(
            " ".join(current)
        )

    if not chunks:

        chunks = [text]

    chunk_duration = (
        duration / len(chunks)
    )

    subtitle_clips = []

    for idx, chunk in enumerate(chunks):

        subtitle_image = (
            render_subtitle_image(
                chunk
            )
        )

        start_time = (
            idx * chunk_duration
        )

        clip = (
            ImageClip(
                subtitle_image
            )
            .set_start(
                start_time
            )
            .set_duration(
                chunk_duration
            )
            .set_position(
                ("center", 0.72),
                relative=True
            )
        )

        subtitle_clips.append(
            clip
        )

    return subtitle_clips


# ============================================================
# 21. Pexels 영상 검색
# ============================================================

def fetch_pexels_video(query):

    if not PEXELS_API_KEY:

        raise RuntimeError(
            "PEXELS_API_KEY가 없습니다."
        )

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    url = (
        "https://api.pexels.com/videos/search"
        f"?query={requests.utils.quote(query)}"
        "&per_page=10"
        "&orientation=portrait"
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        videos = data.get(
            "videos",
            []
        )

        if not videos:

            log(
                f"⚠️ Pexels 결과 없음: {query}"
            )

            return get_fallback_video()

        # 후보 영상들을 수집
        candidates = []

        for video in videos:

            files = video.get(
                "video_files",
                []
            )

            for video_file in files:

                width = video_file.get(
                    "width",
                    0
                )

                height = video_file.get(
                    "height",
                    0
                )

                quality = video_file.get(
                    "quality",
                    ""
                )

                link = video_file.get(
                    "link"
                )

                if not link:
                    continue

                score = 0

                # 세로 영상 우선
                if height > width:

                    score += 50

                # 1080 이상 우선
                if width >= 1080:

                    score += 40

                # HD 우선
                if quality == "hd":

                    score += 20

                candidates.append(
                    (
                        score,
                        link
                    )
                )

        if candidates:

            candidates.sort(
                key=lambda x: x[0],
                reverse=True
            )

            # 상위 후보 중 하나를 랜덤 선택
            top_candidates = (
                candidates[:5]
            )

            selected = random.choice(
                top_candidates
            )

            log(
                f"🎥 Pexels 선택: {query}"
            )

            return selected[1]

    except Exception as e:

        log(
            f"Pexels 검색 실패 "
            f"({query}): {e}"
        )

    return get_fallback_video()


# ============================================================
# 22. Pexels fallback
# ============================================================

def get_fallback_video():

    return (
        "https://videos.pexels.com/"
        "video-files/856987/"
        "856987-hd_1080_1920_30fps.mp4"
    )


# ============================================================
# 23. 영상 다운로드
# ============================================================

def download_video(
    video_url,
    output_path
):

    log(
        f"⬇️ 영상 다운로드: {output_path}"
    )

    response = requests.get(
        video_url,
        timeout=60
    )

    response.raise_for_status()

    with open(
        output_path,
        "wb"
    ) as f:

        f.write(
            response.content
        )

    if (
        not os.path.exists(output_path)
        or os.path.getsize(output_path) < 1000
    ):

        raise RuntimeError(
            "영상 다운로드 결과가 비정상적입니다."
        )


# ============================================================
# 24. 영상 처리
# ============================================================

def process_video_clip(
    clip_path,
    duration
):

    clip = VideoFileClip(
        clip_path
    )

    try:

        if clip.duration < duration:

            try:

                clip = loop(
                    clip,
                    duration=duration
                )

            except Exception:

                clip = clip.loop(
                    duration=duration
                )

        else:

            clip = clip.subclip(
                0,
                duration
            )

        w, h = clip.size

        target_ratio = (
            VIDEO_WIDTH
            / VIDEO_HEIGHT
        )

        current_ratio = (
            w / h
        )

        # 가로 영상
        if current_ratio > target_ratio:

            new_w = int(
                h * target_ratio
            )

            try:

                clip = crop(
                    clip,
                    x_center=w / 2,
                    width=new_w,
                    height=h
                )

            except Exception:

                clip = clip.crop(
                    x_center=w / 2,
                    width=new_w,
                    height=h
                )

        # 세로 영상
        else:

            new_h = int(
                w / target_ratio
            )

            try:

                clip = crop(
                    clip,
                    y_center=h / 2,
                    width=w,
                    height=new_h
                )

            except Exception:

                clip = clip.crop(
                    y_center=h / 2,
                    width=w,
                    height=new_h
                )

        clip = clip.resize(
            (
                VIDEO_WIDTH,
                VIDEO_HEIGHT
            )
        )

        return clip

    except Exception:

        clip.close()

        raise


# ============================================================
# 25. 장면 하나 생성
# ============================================================

def create_scene(
    idx,
    item
):

    text = str(
        item.get(
            "text",
            ""
        )
    ).strip()

    keyword = str(
        item.get(
            "keyword",
            "nature landscape"
        )
    ).strip()

    if not text:

        raise ValueError(
            f"{idx}번 장면의 text가 비어 있습니다."
        )

    if not keyword:

        keyword = "nature landscape"

    log("")
    log(
        f"=============================="
    )
    log(
        f"🎬 SCENE {idx + 1}"
    )
    log(
        f"=============================="
    )

    log(
        f"대사: {text}"
    )

    log(
        f"검색어: {keyword}"
    )

    audio_path = (
        f"scene_{idx}.mp3"
    )

    video_path = (
        f"video_{idx}.mp4"
    )

    # ----------------------------------------
    # TTS
    # ----------------------------------------

    create_voice(
        text,
        audio_path
    )

    # ----------------------------------------
    # 오디오 길이 측정
    # ----------------------------------------

    audio_clip = AudioFileClip(
        audio_path
    )

    duration = audio_clip.duration

    log(
        f"⏱️ 장면 길이: "
        f"{duration:.2f}초"
    )

    # ----------------------------------------
    # Pexels
    # ----------------------------------------

    video_url = fetch_pexels_video(
        keyword
    )

    # ----------------------------------------
    # 다운로드
    # ----------------------------------------

    download_video(
        video_url,
        video_path
    )

    # ----------------------------------------
    # 영상 처리
    # ----------------------------------------

    video_clip = process_video_clip(
        video_path,
        duration
    )

    # ----------------------------------------
    # 자막
    # ----------------------------------------

    subtitle_clips = (
        create_split_subtitles(
            text,
            duration
        )
    )

    # ----------------------------------------
    # 합성
    # ----------------------------------------

    combined = (
        CompositeVideoClip(
            [video_clip]
            + subtitle_clips
        )
        .set_audio(audio_clip)
        .set_duration(duration)
    )

    return combined


# ============================================================
# 26. 임시 파일 정리
# ============================================================

def cleanup_temp_files():

    log(
        "🧹 임시 파일 정리 시작"
    )

    files = []

    for filename in os.listdir("."):

        if (
            filename.startswith("scene_")
            and filename.endswith(".mp3")
        ):

            files.append(filename)

        elif (
            filename.startswith("video_")
            and filename.endswith(".mp4")
        ):

            files.append(filename)

    for filename in files:

        try:

            os.remove(filename)

            log(
                f"삭제: {filename}"
            )

        except Exception as e:

            log(
                f"삭제 실패 "
                f"{filename}: {e}"
            )


# ============================================================
# 27. 총 영상 길이 검사
# ============================================================

def check_total_duration(
    scenes
):

    total = 0

    for scene in scenes:

        try:

            total += scene.duration

        except Exception:
            pass

    log(
        f"🎞️ 예상 최종 길이: "
        f"{total:.2f}초"
    )

    if total < TARGET_MIN_SECONDS:

        log(
            "⚠️ 목표 최소 길이보다 짧습니다."
        )

    elif total > TARGET_MAX_SECONDS:

        log(
            "⚠️ 목표 최대 길이를 초과했습니다."
        )

    else:

        log(
            "✅ 목표 영상 길이 범위!"
        )

    return total


# ============================================================
# 28. 최종 영상 생성
# ============================================================

def render_final_video(
    scene_clips
):

    if not scene_clips:

        raise RuntimeError(
            "생성된 장면이 없습니다."
        )

    log("")
    log(
        "🎞️ 모든 장면 합치는 중..."
    )

    final_video = concatenate_videoclips(
        scene_clips,
        method="chain"
    )

    total_duration = (
        final_video.duration
    )

    log(
        f"최종 영상 길이: "
        f"{total_duration:.2f}초"
    )

    log(
        "🎬 FFmpeg 렌더링 시작..."
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

    message = (
        "🎬 Shorts 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: "
        f"{len(script_data.get('scenes', []))}개\n\n"
        "📦 영상 전송 준비 완료"
    )

    send_telegram_message(
        message
    )


# ============================================================
# 30. 메인
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

        # ------------------------------------
        # 환경변수 검사
        # ------------------------------------

        validate_environment()

        # ------------------------------------
        # 주제 선택
        # ------------------------------------

        topic_info = choose_topic()

        # ------------------------------------
        # 대본 생성
        # ------------------------------------

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

        # ------------------------------------
        # 장면 생성
        # ------------------------------------

        for idx, item in enumerate(
            scenes[:MAX_SCENES]
        ):

            try:

                scene = create_scene(
                    idx,
                    item
                )

                scene_clips.append(
                    scene
                )

            except Exception as e:

                log(
                    f"❌ SCENE {idx + 1} 실패: "
                    f"{e}"
                )

                raise

        # ------------------------------------
        # 총 길이
        # ------------------------------------

        total_duration = (
            check_total_duration(
                scene_clips
            )
        )

        # ------------------------------------
        # 최종 렌더링
        # ------------------------------------

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ------------------------------------
        # Telegram 요약
        # ------------------------------------

        send_result_summary(
            script_data,
            total_duration
        )

        # ------------------------------------
        # Telegram 영상
        # ------------------------------------

        send_telegram_video(
            final_path
        )

        # ------------------------------------
        # 종료
        # ------------------------------------

        elapsed = (
            time.time()
            - start_time
        )

        log(
            "======================================"
        )

        log(
            f"🎉 전체 작업 완료 "
            f"({elapsed / 60:.1f}분)"
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

        # MoviePy 객체 닫기
        for clip in scene_clips:

            try:

                clip.close()

            except Exception:
                pass

        # 임시파일 제거
        cleanup_temp_files()


# ============================================================
# 31. 실행
# ============================================================

if __name__ == "__main__":

    main()
