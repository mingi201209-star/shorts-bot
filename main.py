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
# 역할:
#   1. 주제 선택
#   2. OpenAI 대본 생성
#   3. 한국어 TTS 생성
#   4. video_engine을 이용한 장면 생성
#   5. 전체 장면 합성
#   6. Telegram으로 결과 전송
#
# ============================================================


# ============================================================
# 1. 환경 변수
# ============================================================

OPENAI_KEY = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# OpenAI API 키
openai.api_key = OPENAI_KEY


# ============================================================
# 2. 기본 설정
# ============================================================

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
# 3. 로그
# ============================================================

def log(message):
    """GitHub Actions 로그 출력"""

    now = datetime.now().strftime("%H:%M:%S")

    print(
        f"[{now}] {message}",
        flush=True
    )


# ============================================================
# 4. Telegram 메시지
# ============================================================

def send_telegram_message(message):
    """Telegram 텍스트 메시지 전송"""

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
    """완성된 영상을 Telegram으로 전송"""

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
# 7. 토픽 풀
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
# 8. 전체 토픽 생성
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
# 9. 최근 주제 불러오기
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
            f"⚠️ 최근 주제 읽기 실패: {e}"
        )

    return []


# ============================================================
# 10. 최근 주제 저장
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
            f"⚠️ 최근 주제 저장 실패: {e}"
        )


# ============================================================
# 11. 주제 선택
# ============================================================

def choose_topic():

    recent_topics = load_recent_topics()

    recent_names = []

    for item in recent_topics:

        if isinstance(item, dict):

            name = item.get(
                "topic",
                ""
            )

            if name:
                recent_names.append(name)

        elif isinstance(item, str):

            recent_names.append(item)

    candidates = [
        item
        for item in ALL_TOPICS
        if item["topic"] not in recent_names
    ]

    if not candidates:

        log(
            "♻️ 모든 주제를 사용했으므로 "
            "전체 풀에서 다시 선택합니다."
        )

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

    recent_topics.append(
        selected
    )

    save_recent_topics(
        recent_topics
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

    # Markdown 코드블록 제거
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
# 13. AI 대본 생성
# ============================================================

def generate_script(topic_info):

    category = topic_info["category"]

    topic = topic_info["topic"]

    log(
        "🧠 AI 대본 생성 시작..."
    )

    prompt = f"""
너는 유튜브 Shorts 전문 대본 작가다.

분야:
{category}

영상 방향:
{topic}

반드시 위 방향에 맞는
하나의 구체적인 실제 소재를 선택해라.

이전에 사용한 소재를 반복하지 마라.

사람들이 처음 들었을 때
"뭐라고?"
"진짜?"
"왜?"
라는 반응을 할 만한 소재를 선택해라.

단순한 잡학 나열이 아니라
하나의 이야기처럼 이어져야 한다.

영상 길이는 75~90초를 목표로 한다.

장면 수는 12~13개다.

각 장면은 짧고 강하게 작성한다.

검증되지 않은 인터넷 괴담을
사실처럼 말하지 마라.

과학, 역사, 지리, 기술 등의
확인 가능한 소재를 우선한다.

숫자가 필요할 경우
지나치게 세밀한 가짜 숫자를 만들지 마라.

Pexels 영상 검색을 위해
각 장면마다 영어 keyword를 작성한다.

keyword는 일반적인 시각 키워드로 작성한다.

예:
deep ocean
night city
old laboratory
space stars
forest animal

고유명사는 가급적 사용하지 마라.

반드시 JSON 객체 하나만 출력한다.

형식:

{{
  "title": "영상 제목",
  "topic": "실제 선택한 소재",
  "category": "{category}",
  "scenes": [
    {{
      "text": "장면 대사",
      "keyword": "english visual keyword"
    }}
  ]
}}

JSON 앞뒤에 설명을 붙이지 마라.
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
        )

        data = extract_json(
            content
        )

        if isinstance(data, list):

            result = {
                "title": topic,
                "topic": topic,
                "category": category,
                "scenes": data
            }

        else:

            result = data

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

        clean_scenes = []

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
                    "nature landscape"
                )
            ).strip()

            if not text:
                continue

            if not keyword:
                keyword = "nature landscape"

            clean_scenes.append(
                {
                    "text": text,
                    "keyword": keyword
                }
            )

        if len(clean_scenes) < MIN_SCENES:

            raise ValueError(
                "장면 수 부족: "
                f"{len(clean_scenes)}개"
            )

        result["scenes"] = (
            clean_scenes[:MAX_SCENES]
        )

        if not result.get("title"):

            result["title"] = topic

        if not result.get("topic"):

            result["topic"] = topic

        if not result.get("category"):

            result["category"] = category

        log(
            "✅ 대본 생성 완료"
        )

        log(
            f"📝 제목: {result['title']}"
        )

        log(
            f"🧠 소재: {result['topic']}"
        )

        log(
            f"🎬 장면 수: "
            f"{len(result['scenes'])}"
        )

        return result

    except Exception as e:

        log(
            f"❌ AI 대본 생성 실패: {e}"
        )

        raise


# ============================================================
# 14. TTS
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
# 15. 총 영상 길이 검사
# ============================================================

def check_total_duration(
    scenes
):

    total = 0.0

    for scene in scenes:

        try:

            total += float(
                scene.duration
            )

        except Exception:
            pass

    log(
        f"🎞️ 최종 예상 길이: "
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
            "✅ 목표 길이 범위입니다."
        )

    return total


# ============================================================
# 16. 최종 영상 렌더링
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
# 17. 결과 요약
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

    message = (
        "🎬 Shorts 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: {len(scenes)}개\n\n"
        "📦 영상 전송 중..."
    )

    send_telegram_message(
        message
    )


# ============================================================
# 18. 임시 파일 정리
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
# 19. 메인
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
        # 주제
        # ----------------------------------------------------

        topic_info = choose_topic()

        # ----------------------------------------------------
        # 대본
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

                # ★ 중요 ★
                #
                # video_engine.py의 create_scene()
                # 함수는 다음 4개 인자를 받는다.
                #
                # create_scene(
                #     idx,
                #     item,
                #     create_voice,
                #     requests
                # )
                #
                # 기존 코드의
                #
                #     create_voice,
                #     requests
                #
                # 를 함수 바깥에 따로 적어버린 것이
                # "takes 4 positional arguments but 7"
                # 오류의 원인이었다.

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
# 20. 실행
# ============================================================

if __name__ == "__main__":

    main()
