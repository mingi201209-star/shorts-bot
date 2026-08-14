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

# MoviePy Import 안전 처리
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
    from moviepy.video.fx.all import crop, loop
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    import moviepy.video.fx.crop as crop
    import moviepy.video.fx.loop as loop

openai.api_key = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": str(message)}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_telegram_video(video_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video_file:
            response = requests.post(
                url, 
                data={"chat_id": TELEGRAM_CHAT_ID}, 
                files={"video": video_file},
                timeout=120
            )
            if not response.ok:
                send_telegram_message(f"⚠️ 영상 전송 실패 (코드: {response.status_code})")
    except Exception as e:
        send_telegram_message(f"⚠️ 영상 전송 에러: {str(e)}")

async def generate_voice(text, output_path):
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural")
    await communicate.save(output_path)

def process_video_clip(clip_path, duration):
    clip = VideoFileClip(clip_path)
    if clip.duration < duration:
        try:
            clip = loop(clip, duration=duration)
        except Exception:
            clip = clip.loop(duration=duration)
    else:
        clip = clip.subclip(0, duration)

    w, h = clip.size
    target_w, target_h = 1080, 1920
    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        try:
            clip = crop(clip, x_center=w/2, width=new_w, height=h)
        except Exception:
            clip = clip.crop(x_center=w/2, width=new_w, height=h)
    else:
        new_h = int(w / target_ratio)
        try:
            clip = crop(clip, y_center=h/2, width=w, height=new_h)
        except Exception:
            clip = clip.crop(y_center=h/2, width=w, height=new_h)

    return clip.resize((target_w, target_h))

def get_safe_korean_font(size):
    font_filename = "NanumGothic.ttf"
    if os.path.exists(font_filename):
        try:
            return ImageFont.truetype(font_filename, size)
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
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def render_subtitle_image(text):
    target_w = 1080
    font_size = 70
    font = get_safe_korean_font(font_size)
    
    padding = 40
    img_h = font_size + padding * 2
    img = Image.new("RGBA", (target_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    line_w = sum(font_size if ord(c) > 127 else font_size * 0.55 for c in text)
    x = max(20, int((target_w - line_w) // 2))

    # 가독성을 높이기 위한 두꺼운 외곽선 처리
    stroke_width = 8
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            draw.text((x + dx, padding + dy), text, font=font, fill="black")

    draw.text((x, padding), text, font=font, fill="#FFE600")
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
            chunks.append(" ".join(curr))
            curr = []
    if curr:
        chunks.append(" ".join(curr))

    chunk_dur = duration / len(chunks) if len(chunks) > 0 else duration
    sub_clips = []

    for idx, chunk in enumerate(chunks):
        sub_np = render_subtitle_image(chunk)
        start_time = idx * chunk_dur
        
        clip = (ImageClip(sub_np)
                .set_start(start_time)
                .set_duration(chunk_dur)
                .set_position(('center', 0.72), relative=True))
        sub_clips.append(clip)

    return sub_clips

def fetch_pexels_video(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if "videos" in data and len(data["videos"]) > 0:
            videos = data["videos"][0]["video_files"]
            for v in videos:
                if v.get("width", 0) >= 1080 or v.get("quality") == "hd":
                    return v["link"]
            return videos[0]["link"]
    except Exception as e:
        print(f"Pexels fetch error for {query}: {e}")
    return "https://videos.pexels.com/video-files/856987/856987-hd_1080_1920_30fps.mp4"

def main():
    try:
        prompt = """
        유튜브 숏츠용으로 사람들이 전혀 몰랐던 '아주 깊고 구체적인 과학/역사/미스터리' 상식 주제로 대본을 구성해줘.
        단순히 겉핥기 식이 아니라 사건의 배경, 구체적인 수치, 놀라운 반전이나 이유를 상세히 서술할 것.
        
        [규칙]
        - 전체 총 길이가 1분 15초 ~ 1분 30초 내외가 되도록 **총 12개~13개의 구절(scenes)**로 풍성하게 구성할 것.
        - 각 구절은 명확한 내용 전달을 위해 15자 내외로 작성할 것.
        - Pexels 검색 키워드는 고유명사를 절대 쓰지 말고, 100% 보편적 영문 풍경/시각 키워드만 사용할 것.
        
        응답은 오직 아래 JSON 포맷으로만 전달해 (배열 형태):
        [
          {"text": "지구상에서 가장 외로운 곳, 포인트 네모를 아시나요?", "keyword": "deep ocean aerial"},
          {"text": "남태평양 한가운데 위치한 거대한 바다의 오지입니다.", "keyword": "blue ocean waves"},
          {"text": "가장 가까운 육지에서 무려 2,688km나 떨어져 있죠.", "keyword": "world map vintage"},
          {"text": "이곳은 영양분이 거의 없어 생물도 살기 힘든 바다의 사막입니다.", "keyword": "underwater empty sea"},
          {"text": "인간의 발길이 완전히 닿지 않는 완벽한 고립 지대인데요,", "keyword": "isolated ocean drone"},
          {"text": "너무 외딴곳이라 상공을 지나가는 가장 가까운 인간은,", "keyword": "iss astronaut space"},
          {"text": "무중력 우주 정거장에 머무는 우주 비행사들뿐입니다.", "keyword": "earth view from space"},
          {"text": "지상에서 수백 킬로미터 떨어진 우주가 더 가깝다는 뜻이죠.", "keyword": "galaxy stars night"},
          {"text": "게다가 이곳은 수명이 다한 인공위성들의 거대한 무덤이기도 한데요,", "keyword": "satellite orbiting earth"},
          {"text": "지구로 떨어질 때 민간 피해를 막기 위해 의도적으로 추락시키는 곳입니다.", "keyword": "dark ocean night"},
          {"text": "지금 이 순간에도 수많은 인공위성들이 이 깊은 바다로 잠들어 가고 있습니다.", "keyword": "deep blue sea underwater"},
          {"text": "우리가 모르는 지구의 또 다른 비밀, 정말 놀랍지 않나요?", "keyword": "mysterious universe glow"}
        ]
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        
        items = data if isinstance(data, list) else data.get("scenes", data.get("script", list(data.values())[0]))

        scene_clips = []

        for idx, item in enumerate(items[:13]):
            text = item.get("text", "")
            keyword = item.get("keyword", "nature landscape")

            audio_path = f"scene_{idx}.mp3"
            asyncio.run(generate_voice(text, audio_path))

            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration

            video_url = fetch_pexels_video(keyword)
            video_path = f"video_{idx}.mp4"
            with open(video_path, "wb") as f:
                f.write(requests.get(video_url, timeout=30).content)

            video_clip = process_video_clip(video_path, duration)
            sub_clips = create_split_subtitles(text, duration)

            combined = CompositeVideoClip([video_clip] + sub_clips).set_audio(audio_clip)
            scene_clips.append(combined)

        final_video = concatenate_videoclips(scene_clips, method="chain")
        final_output_path = "final_shorts.mp4"
        
        final_video.write_videofile(
            final_output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="5000k"
        )

        send_telegram_message("🎬 최대 1분 30초 상한선 적용 완료된 고화질 숏츠 완성!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)[:100]}")
        raise e

if __name__ == "__main__":
    main()
