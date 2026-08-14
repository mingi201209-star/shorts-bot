import os
import re
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

# MoviePy 안전 Import
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
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
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
    font_paths = [
        font_filename,
        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
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
    font_size = 65
    font = get_safe_korean_font(font_size)
    img_w = int(target_w * 0.9)

    img = Image.new("RGBA", (img_w, font_size + 50), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    line_w = sum(font_size if ord(c) > 127 else font_size * 0.55 for c in text)
    x = max(0, int((img_w - line_w) // 2))

    stroke_width = 6
    for adj_x in range(-stroke_width, stroke_width + 1):
        for adj_y in range(-stroke_width, stroke_width + 1):
            draw.text((x + adj_x, 20 + adj_y), text, font=font, fill="black")

    draw.text((x, 20), text, font=font, fill="#FFE600")
    return np.array(img)

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
        # GPT에게 PPT 연출용 대본 세트 요구
        prompt = """
        유튜브 숏츠용 과학 상식 숏츠 구조를 JSON 형태로 짜줘.
        [규칙]
        - 대본은 3개 구절로 구성.
        - 구절마다 화면에 어울리는 영어 검색 키워드(search_keyword)를 명확히 지정해줘.
        
        응답은 오직 아래 JSON 포맷으로만 전달해:
        [
          {"text": "지구의 대기는 수많은 가스로 차있습니다.", "keyword": "earth atmosphere"},
          {"text": "질소가 약 78퍼센트를 차지하고 있죠.", "keyword": "nitrogen gas"},
          {"text": "대기가 없다면 화성처럼 황량해집니다.", "keyword": "mars planet"}
        ]
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        import json
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        
        # JSON 구조 유연하게 파싱
        items = data if isinstance(data, list) else data.get("scenes", data.get("script", list(data.values())[0]))

        scene_clips = []

        for idx, item in enumerate(items[:4]):
            text = item.get("text", "")
            keyword = item.get("keyword", "nature")

            audio_path = f"scene_{idx}.mp3"
            asyncio.run(generate_voice(text, audio_path))

            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration

            # Pexels 비디오 매칭
            video_url = fetch_pexels_video(keyword)
            video_path = f"video_{idx}.mp4"
            with open(video_path, "wb") as f:
                f.write(requests.get(video_url, timeout=30).content)

            # 비디오 처리
            video_clip = process_video_clip(video_path, duration)

            # 자막 이미지 생성 및 적용 (해당 구절 재생 시점에 싱크 고정)
            sub_np = render_subtitle_image(text)
            sub_clip = (ImageClip(sub_np)
                        .set_start(0)
                        .set_duration(duration)
                        .set_position(('center', 0.75), relative=True))

            combined = CompositeVideoClip([video_clip, sub_clip]).set_audio(audio_clip)
            scene_clips.append(combined)

        final_video = concatenate_videoclips(scene_clips, method="compose")
        final_output_path = "final_shorts.mp4"
        
        final_video.write_videofile(
            final_output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="3000k"
        )

        send_telegram_message("🎬 내용-영상 딱 맞춘 PPT 연출 숏츠 완성!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)[:100]}")
        raise e

if __name__ == "__main__":
    main()
