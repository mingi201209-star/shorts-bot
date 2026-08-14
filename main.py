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

    # 두꺼운 외곽선
    stroke_width = 8
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            draw.text((x + dx, padding + dy), text, font=font, fill="black")

    # 선명한 노란색 텍스트
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

    chunk_dur = duration / len(chunks)
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
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=3&orientation=portrait"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if "videos" in data and len(data["videos"]) > 0:
            return data["videos"][0]["video_files"][0]["link"]
    except Exception as e:
        print(f"Pexels fetch error for {query}: {e}")
    return "https://videos.pexels.com/video-files/856987/856987-hd_1080_1920_30fps.mp4"

def main():
    try:
        prompt = """
        유튜브 숏츠용 사람들이 거의 모를 법한 '아주 깊고 흥미로운 잡학/미스터리/과학/역사 상식' 주제로 대본을 구성해줘.
        뻔한 바나나 이야기 같은 것은 제외하고, '모르는 게 당연한' 수준의 신기한 주제를 선정할 것.
        
        [규칙]
        - 전체 길이가 30초 내외가 되도록 총 5개~6개 구절(scenes)로 구성할 것.
        - 각 구절은 짧고 명확하게(15자 내외) 작성할 것.
        - 구절마다 시각적으로 딱 맞는 정확한 Pexels 영어 검색 키워드(keyword)를 작성할 것.
        
        응답은 오직 아래 JSON 포맷으로만 전달해:
        [
          {"text": "지구상에서 가장 외로운 곳, '포인트 네모'를 아시나요?", "keyword": "point nemo ocean"},
          {"text": "육지에서 무려 2,688km나 떨어져 있습니다.", "keyword": "map isolated ocean"},
          {"text": "너무 멀어서 가장 가까운 인간은 우주 비행사입니다.", "keyword": "iss astronaut space"},
          {"text": "수명이 다한 인공위성들의 무덤이기도 하죠.", "keyword": "satellite crashing ocean"},
          {"text": "이곳에 가면 지구상 그 누구와도 만날 수 없습니다.", "keyword": "thinking mystery isolated"}
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

        for idx, item in enumerate(items[:6]):
            text = item.get("text", "")
            keyword = item.get("keyword", "mystery")

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

            # 괄호 수식 정확히 교정
            combined = CompositeVideoClip([video_clip] + sub_clips).set_audio(audio_clip)
            scene_clips.append(combined)

        final_video = concatenate_videoclips(scene_clips, method="chain")
        final_output_path = "final_shorts.mp4"
        
        final_video.write_videofile(
            final_output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="3000k"
        )

        send_telegram_message("🎬 딥한 잡학 주제 숏츠 제작 완료!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)[:100]}")
        raise e

if __name__ == "__main__":
    main()
