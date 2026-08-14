import os
import re
import asyncio
import requests
import openai
import edge_tts
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFont

# Pillow 10+ 호환성 패치 (MoviePy 1.0.3의 Image.ANTIALIAS 에러 방지)
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
    
    if not any(os.path.exists(p) for p in font_paths):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
            r = requests.get(url, timeout=15)
            with open(font_filename, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Font download failed: {e}")

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

    img_w = int(target_w * 0.88)
    
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        estimated_w = sum(font_size if ord(c) > 127 else font_size * 0.55 for c in test_line)
            
        if estimated_w <= img_w:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    line_height = font_size + 20
    img_h = line_height * len(lines) + 40

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = 20
    for line in lines:
        line_w = sum(font_size if ord(c) > 127 else font_size * 0.55 for c in line)
        x = max(0, int((img_w - line_w) // 2))

        stroke_width = 6
        for adj_x in range(-stroke_width, stroke_width + 1):
            for adj_y in range(-stroke_width, stroke_width + 1):
                draw.text((x + adj_x, y + adj_y), line, font=font, fill="black")

        draw.text((x, y), line, font=font, fill="#FFE600")
        y += line_height

    return np.array(img)

def create_animated_subtitles(text, total_duration):
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

    chunk_duration = total_duration / len(chunks)
    subtitle_clips = []

    for i, chunk in enumerate(chunks):
        img_np = render_subtitle_image(chunk)
        start_time = i * chunk_duration
        sub_clip = (ImageClip(img_np)
                    .set_start(start_time)
                    .set_duration(chunk_duration)
                    .set_position(('center', 0.72), relative=True))
        subtitle_clips.append(sub_clip)

    return subtitle_clips

def main():
    try:
        prompt = """
        유튜브 숏츠용 흥미로운 과학/우주/자연 상식 대본 3문장을 작성해줘.
        [규칙]
        - 반드시 하나의 일관된 주제로만 작성할 것.
        - 특수문자, 번호표시, 따옴표 없이 순수 한국어 문장만 3줄로 출력할 것.
        """
        
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        raw_lines = response.choices[0].message.content.strip().split("\n")
        lines = [l.strip() for l in raw_lines if l.strip() and not l.strip().isdigit()]

        clip_list = []

        for i, line in enumerate(lines[:3]):
            audio_path = f"audio_{i}.mp3"
            asyncio.run(generate_voice(line, audio_path))
            
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration

            keyword_prompt = f"Extract 1 English word for Pexels search: '{line}'"
            keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
            raw_keyword = keyword_res.choices[0].message.content.strip()
            
            search_query = re.sub(r'[^a-zA-Z]', '', raw_keyword)
            if not search_query:
                search_query = "galaxy"

            headers = {"Authorization": PEXELS_API_KEY}
            pexels_url = f"https://api.pexels.com/videos/search?query={search_query}&per_page=3&orientation=portrait"
            
            res = requests.get(pexels_url, headers=headers, timeout=15)
            res.encoding = 'utf-8'
            data = res.json()

            video_path = f"video_{i}.mp4"
            if "videos" in data and len(data["videos"]) > 0:
                video_url = data["videos"][0]["video_files"][0]["link"]
            else:
                video_url = "https://videos.pexels.com/video-files/856987/856987-hd_1080_1920_30fps.mp4"

            video_bytes = requests.get(video_url, timeout=30).content
            with open(video_path, "wb") as f:
                f.write(video_bytes)

            video_clip = process_video_clip(video_path, duration)
            sub_clips = create_animated_subtitles(line, duration)

            combined_clip = CompositeVideoClip([video_clip] + sub_clips).set_audio(audio_clip)
            clip_list.append(combined_clip)

        final_video = concatenate_videoclips(clip_list, method="compose")
        final_output_path = "final_shorts.mp4"
        
        final_video.write_videofile(
            final_output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="3000k"
        )

        send_telegram_message("🎬 업그레이드된 숏츠 생성이 완료되었습니다!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)[:100]}")
        raise e

if __name__ == "__main__":
    main()
