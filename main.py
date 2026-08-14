import os
import re
import json
import asyncio
import requests
import openai
import edge_tts
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFont

# Pillow 호환성 패치
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# MoviePy Import
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
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    import moviepy.video.fx.crop as crop
    import moviepy.video.fx.loop as loop


# ============================================================
# 환경 변수
# ============================================================

openai.api_key = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

USED_TOPICS_FILE = "used_topics.json"


# ============================================================
# 텔레그램
# ============================================================

def send_telegram_message(message):
    """텔레그램 텍스트 알림 전송"""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": str(message)
            },
            timeout=10
        )

    except Exception as e:
        print(f"Telegram error: {e}")


def send_telegram_video(video_path):
    """텔레그램 최종 숏츠 영상 전송"""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"

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
                timeout=120
            )

            if not response.ok:
                send_telegram_message(
                    f"⚠️ 영상 전송 실패 (코드: {response.status_code})"
                )

    except Exception as e:
        send_telegram_message(
            f"⚠️ 영상 전송 에러: {str(e)}"
        )


# ============================================================
# 사용한 주제 관리
# ============================================================

def load_used_topics():
    """지금까지 사용한 쇼츠 주제 목록 불러오기"""

    if not os.path.exists(USED_TOPICS_FILE):
        return []

    try:

        with open(
            USED_TOPICS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except Exception as e:

        print(
            f"used_topics.json 읽기 오류: {e}"
        )

        return []


def save_used_topic(topic):
    """쇼츠 생성이 성공한 주제를 기록"""

    topics = load_used_topics()

    if topic not in topics:
        topics.append(topic)

    with open(
        USED_TOPICS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            topics,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"✅ 주제 기록 완료: {topic}"
    )


def choose_new_topic():
    """
    AI가 이전에 사용하지 않은
    새로운 쇼츠 주제를 선정한다.
    """

    used_topics = load_used_topics()

    # 너무 많은 기록을 한꺼번에 프롬프트에 넣지 않도록
    # 최근 100개만 전달
    recent_topics = used_topics[-100:]

    if recent_topics:

        used_text = "\n".join(
            f"- {topic}"
            for topic in recent_topics
        )

    else:

        used_text = "(아직 사용한 주제가 없습니다.)"


    prompt = f"""
너는 유튜브 쇼츠 채널의 주제 선정 AI다.

이번 실행에서 단 하나의 새로운 쇼츠 주제를 선정해야 한다.

채널에서 다룰 수 있는 분야:

- 과학
- 우주
- 역사
- 고고학
- 심해
- 자연
- 미스터리
- 인간의 몸과 뇌
- 기술
- 지구의 특이한 현상
- 실제 사건
- 잘 알려지지 않은 놀라운 사실

가장 중요한 규칙:

이미 사용한 주제와 같은 소재를 절대 반복하지 마라.

단순히 제목만 바꾼 비슷한 주제도 금지한다.

예를 들어 이미
"포인트 네모"
를 다뤘다면,

- 지구에서 가장 외로운 곳
- 가장 고립된 바다
- 인공위성 무덤

처럼 핵심 소재가 겹치는 주제도 피해야 한다.

이미 사용한 주제:

{used_text}


새로운 주제는 다음 조건을 만족해야 한다.

1. 실제 사실에 기반할 것.
2. 첫 3초에 시청자의 호기심을 끌 수 있을 것.
3. 1분 15초~1분 30초 정도의 쇼츠로 충분히 설명할 내용이 있을 것.
4. 너무 유명하고 뻔한 소재는 피할 것.
5. 이전 주제와 최대한 다른 분야를 선택할 것.
6. 특정 인물이나 유명 사건의 단순 소개는 피할 것.
7. 구체적인 사실과 숫자를 설명할 수 있을 것.
8. 놀라운 반전이나 의외의 이유가 있을 것.
9. 영상으로 표현하기 좋은 소재일 것.
10. Pexels에서 관련 영상을 찾을 수 있는 소재일 것.


반드시 아래 JSON 형식으로만 답해라.

{{
    "topic": "선정한 새로운 주제",
    "reason": "이 주제가 흥미로운 이유를 한 문장으로 설명"
}}
"""


    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"
        }
    )


    content = response.choices[0].message.content.strip()

    result = json.loads(content)

    topic = result.get(
        "topic",
        ""
    ).strip()

    reason = result.get(
        "reason",
        ""
    ).strip()


    if not topic:
        raise ValueError(
            "AI가 새로운 주제를 선정하지 못했습니다."
        )


    print(
        f"🎯 새로운 주제: {topic}"
    )

    print(
        f"💡 선정 이유: {reason}"
    )

    return topic


# ============================================================
# TTS
# ============================================================

async def generate_voice(text, output_path):
    """한국어 음성 생성"""

    communicate = edge_tts.Communicate(
        text,
        "ko-KR-InJoonNeural"
    )

    await communicate.save(output_path)


# ============================================================
# 영상 처리
# ============================================================

def process_video_clip(clip_path, duration):

    clip = VideoFileClip(clip_path)


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

    target_w = 1080
    target_h = 1920

    target_ratio = target_w / target_h
    current_ratio = w / h


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


    return clip.resize(
        (target_w, target_h)
    )


# ============================================================
# 한글 폰트
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

        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",

        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",

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


    return ImageFont.load_default()


# ============================================================
# 자막
# ============================================================

def render_subtitle_image(text):

    target_w = 1080

    font_size = 70

    font = get_safe_korean_font(
        font_size
    )


    padding = 40

    img_h = (
        font_size +
        padding * 2
    )


    img = Image.new(
        "RGBA",
        (target_w, img_h),
        (0, 0, 0, 0)
    )


    draw = ImageDraw.Draw(img)


    line_w = sum(
        font_size if ord(c) > 127
        else font_size * 0.55
        for c in text
    )


    x = max(
        20,
        int(
            (target_w - line_w) / 2
        )
    )


    # 두꺼운 외곽선
    stroke_width = 8


    for dx in range(
        -stroke_width,
        stroke_width + 1
    ):

        for dy in range(
            -stroke_width,
            stroke_width + 1
        ):

            draw.text(
                (
                    x + dx,
                    padding + dy
                ),
                text,
                font=font,
                fill="black"
            )


    draw.text(
        (x, padding),
        text,
        font=font,
        fill="#FFE600"
    )


    return np.array(img)


def create_split_subtitles(text, duration):

    words = text.split()

    if not words:
        return []


    chunks = []

    curr = []


    for word in words:

        curr.append(word)

        if len(curr) >= 2:

            chunks.append(
                " ".join(curr)
            )

            curr = []


    if curr:

        chunks.append(
            " ".join(curr)
        )


    chunk_dur = (
        duration / len(chunks)
    )


    sub_clips = []


    for idx, chunk in enumerate(chunks):

        sub_np = render_subtitle_image(
            chunk
        )


        start_time = (
            idx * chunk_dur
        )


        clip = (
            ImageClip(sub_np)
            .set_start(start_time)
            .set_duration(chunk_dur)
            .set_position(
                ('center', 0.72),
                relative=True
            )
        )


        sub_clips.append(clip)


    return sub_clips


# ============================================================
# Pexels
# ============================================================

def fetch_pexels_video(query):

    headers = {
        "Authorization": PEXELS_API_KEY
    }


    url = (
        "https://api.pexels.com/videos/search"
        f"?query={query}"
        "&per_page=5"
        "&orientation=portrait"
    )


    try:

        res = requests.get(
            url,
            headers=headers,
            timeout=10
        )


        data = res.json()


        if (
            "videos" in data
            and len(data["videos"]) > 0
        ):

            videos = data["videos"][0][
                "video_files"
            ]


            for v in videos:

                if (
                    v.get("width", 0) >= 1080
                    or v.get("quality") == "hd"
                ):

                    return v["link"]


            return videos[0]["link"]


    except Exception as e:

        print(
            f"Pexels fetch error for {query}: {e}"
        )


    return (
        "https://videos.pexels.com/"
        "video-files/856987/"
        "856987-hd_1080_1920_30fps.mp4"
    )


# ============================================================
# 메인
# ============================================================

def main():

    topic = None

    try:

        # ----------------------------------------------------
        # 1. AI가 새로운 주제 선정
        # ----------------------------------------------------

        topic = choose_new_topic()


        # ----------------------------------------------------
        # 2. 선정된 주제로 대본 생성
        # ----------------------------------------------------

        prompt = f"""
유튜브 쇼츠용 대본을 작성해줘.

이번 주제:

{topic}


이 주제에 대해 사람들이 잘 모르는
구체적인 사실을 중심으로 구성해라.


[규칙]

- 전체 총 길이는 1분 15초 ~ 1분 30초
- 총 12~13개의 scenes
- 각 scene은 짧고 자연스러운 한국어 내레이션
- 단순한 백과사전식 설명 금지
- 초반에는 강한 궁금증을 유발
- 중간에는 구체적인 숫자, 사실, 배경을 제시
- 후반에는 의외의 반전이나 놀라운 사실을 제시
- 마지막에는 여운이 남는 마무리
- 서로 이어지는 하나의 이야기처럼 구성
- 같은 표현을 반복하지 말 것


Pexels 검색 키워드 규칙:

- 반드시 영어
- 일반적인 시각적 검색어
- 고유명사 금지
- 사람 이름 금지
- 브랜드명 금지
- 특정 장소의 고유명사 금지
- 영상으로 표현하기 쉬운 키워드 사용


예:

"deep ocean"

"ancient ruins"

"night sky"

"human brain"

"laboratory experiment"

"desert landscape"

"old machinery"


응답은 반드시 아래 JSON 형식으로만 출력해.

{{
    "scenes": [
        {{
            "text": "한국어 내레이션",
            "keyword": "영문 Pexels 검색어"
        }}
    ]
}}
"""


        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={
                "type": "json_object"
            }
        )


        content = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )


        data = json.loads(content)


        items = data.get(
            "scenes",
            []
        )


        if not items:

            raise ValueError(
                "AI가 scenes를 생성하지 못했습니다."
            )


        # ----------------------------------------------------
        # 3. 장면별 영상 생성
        # ----------------------------------------------------

        scene_clips = []


        for idx, item in enumerate(
            items[:13]
        ):

            text = item.get(
                "text",
                ""
            )


            keyword = item.get(
                "keyword",
                "nature landscape"
            )


            print(
                f"🎬 Scene {idx + 1}/{min(len(items), 13)}"
            )

            print(
                f"   내용: {text}"
            )

            print(
                f"   검색어: {keyword}"
            )


            # TTS
            audio_path = (
                f"scene_{idx}.mp3"
            )


            asyncio.run(
                generate_voice(
                    text,
                    audio_path
                )
            )


            audio_clip = AudioFileClip(
                audio_path
            )


            duration = (
                audio_clip.duration
            )


            # Pexels 영상 검색
            video_url = fetch_pexels_video(
                keyword
            )


            video_path = (
                f"video_{idx}.mp4"
            )


            video_response = requests.get(
                video_url,
                timeout=30
            )


            video_response.raise_for_status()


            with open(
                video_path,
                "wb"
            ) as f:

                f.write(
                    video_response.content
                )


            # 영상 처리
            video_clip = process_video_clip(
                video_path,
                duration
            )


            # 자막
            sub_clips = create_split_subtitles(
                text,
                duration
            )


            # 영상 + 자막 + 음성
            combined = (
                CompositeVideoClip(
                    [video_clip] + sub_clips
                )
                .set_audio(audio_clip)
            )


            scene_clips.append(
                combined
            )


        # ----------------------------------------------------
        # 4. 최종 영상 합치기
        # ----------------------------------------------------

        if not scene_clips:

            raise ValueError(
                "생성된 영상 장면이 없습니다."
            )


        final_video = concatenate_videoclips(
            scene_clips,
            method="chain"
        )


        final_output_path = (
            "final_shorts.mp4"
        )


        print(
            "🎞️ 최종 영상 렌더링 시작..."
        )


        final_video.write_videofile(
            final_output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="5000k"
        )


        # ----------------------------------------------------
        # 5. 완성 알림
        # ----------------------------------------------------

        send_telegram_message(
            "🎬 새로운 주제로 쇼츠 완성!\n\n"
            f"📌 주제: {topic}\n"
            "⏱️ 최대 1분 30초 상한선 적용\n"
            "🎞️ 고화질 렌더링 완료"
        )


        send_telegram_video(
            final_output_path
        )


        # ----------------------------------------------------
        # 6. 성공한 주제만 기록
        # ----------------------------------------------------

        save_used_topic(
            topic
        )


        print(
            "✅ 쇼츠 생성 및 주제 기록 완료!"
        )


    except Exception as e:

        error_message = str(e)[:300]


        send_telegram_message(
            "❌ 쇼츠 생성 중 오류 발생\n\n"
            f"주제: {topic or '주제 선정 전'}\n"
            f"오류: {error_message}"
        )


        print(
            f"❌ 오류 발생: {e}"
        )


        raise


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()
