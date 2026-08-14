import os
import random
import json
import asyncio
import requests
import openai
import edge_tts
from pydub import AudioSegment, silence
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

# 환경 변수 설정
openai.api_key = os.environ.get("OPENAI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """텔레그램 텍스트 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": str(message)}, timeout=10)
    except Exception as e:
        print(f"Telegram message error: {e}")

def send_telegram_video(video_path):
    """텔레그램 최종 숏츠 영상 전송"""
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
    """edge-tts를 이용한 자연스러운 한국어 음성 생성"""
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
    await communicate.save(output_path)

def preprocess_audio(input_path, output_path, silence_thresh=-40, min_silence_len=400):
    """BGM이 없는 채널에 맞춰 내레이션의 무음 구간을 제거하고 볼륨을 정규화"""
    audio = AudioSegment.from_file(input_path)
    chunks = silence.split_on_silence(
        audio, 
        min_silence_len=min_silence_len, 
        silence_thresh=silence_thresh,
        keep_silence=150
    )
    processed_audio = AudioSegment.empty()
    for chunk in chunks:
        processed_audio += chunk
    processed_audio = processed_audio.normalize()
    processed_audio.export(output_path, format="mp3")
    return output_path

def process_video_clip(clip_path, duration):
    """스톡 영상을 숏츠 규격(9:16)으로 크롭 및 루프 처리 후 역동적인 줌 효과(Ken Burns) 적용"""
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

    clip = clip.resize((target_w, target_h))

    def zoom_effect(get_frame, t):
        img = get_frame(t)
        progress = t / duration if duration > 0 else 0
        zoom = 1.0 + 0.08 * progress
        new_w, new_h = int(target_w * zoom), int(target_h * zoom)
        pil_img = Image.fromarray(img).resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        cropped = pil_img.crop((left, top, left + target_w, top + target_h))
        return np.array(cropped)

    return clip.fl(zoom_effect, keep_duration=True)

def get_safe_korean_font(size):
    """가독성 높은 한글 폰트 로드"""
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
    """고가독성 자막 렌더링"""
    target_w = 1080
    font_size = 70
    font = get_safe_korean_font(font_size)
    
    padding = 40
    img_h = font_size + padding * 2
    img = Image.new("RGBA", (target_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    line_w = sum(font_size if ord(c) > 127 else font_size * 0.55 for c in text)
    x = max(20, int((target_w - line_w) // 2))

    stroke_width = 8
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            draw.text((x + dx, padding + dy), text, font=font, fill="black")

    draw.text((x, padding), text, font=font, fill="#FFE600")
    return np.array(img)

def render_hook_title_image(title_text):
    """초반 3초 시선을 강탈하는 인트로 후크 타이틀 배너 생성"""
    target_w = 1080
    font_size = 85
    font = get_safe_korean_font(font_size)
    
    padding = 50
    img_h = (font_size * 2) + (padding * 2)
    img = Image.new("RGBA", (target_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rectangle([100, padding, target_w - 100, img_h - padding], fill=(0, 0, 0, 180), outline=(255, 230, 0), width=4)
    draw.text((target_w // 2, img_h // 2), title_text, font=font, fill="#FFE600", anchor="mm")
    return np.array(img)

def create_split_subtitles(text, duration):
    """텍스트를 쪼개어 싱크에 맞는 자막 클립 생성"""
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
                .set_position(('center', 0.78), relative=True))
        sub_clips.append(clip)

    return sub_clips

def fetch_pexels_video(query):
    """Pexels API를 통한 세로형 스톡 비디오 검색"""
    headers = {"
