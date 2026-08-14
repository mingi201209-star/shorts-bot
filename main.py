import os
import re
import asyncio
import requests
import openai
import edge_tts
import whisper
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFont

# Pillow 10+ 호환성 패치
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

    img = Image.new("RGBA", (img_w, font_size + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    line_w = sum(font_size if ord(c) > 127 else font_size * 0.55 for c in text)
    x = max(0, int((img_w - line_w) // 2))

    stroke_width = 6
    for adj_x in range(-stroke_width, stroke_width + 1):
        for adj_y in range(-stroke_width, stroke_width + 1):
            draw.text((x + adj_x, 20 + adj_y), text, font=font, fill="black")

    draw.text((x, 20), text, font=font, fill="#FFE600")
    return np.array(img)

def fetch_pexels_video(query, index=0):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if "videos" in data and len(data["videos"]) > 0:
            idx = min(index, len(data["videos"]) - 1)
            return data["videos"][idx]["video_files"][0]["link"]
    except Exception as e:
        print(f"Pexels search error: {e}")
    return "https://videos.pexels.com/video-files/856987/856987-hd_1080_1920_30fps.mp4"

def main():
    try:
        # Whisper 경량 모델 로드
        whisper_model = whisper.load_model("base")

        prompt = """
        유튜브 숏츠용 흥미로운 과학 상식 대본 3문장을 작성해줘.
        [규칙]
        - 각 문장마다 명확히 다른 영상 주제(예: 지구 대기, 화성 환경, 우주 먼지)가 드러나게 작성할 것.
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
            total_duration = audio_clip.duration

            # 1. Whisper로 음성 분석 (단어별 타임스탬프 추출)
            result = whisper_model.transcribe(audio_path, language="ko", word_timestamps=True)
            
            # 2. 문장 대표 검색어 추출
            keyword_prompt = f"Convert this Korean sentence into 1 short English keyword for stock video: '{line}'"
            keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
            search_query = re.sub(r'[^a-zA-Z]', '', keyword_res.choices[0].message.content.strip()) or "nature"

            # 3. 해당 키워드로 배경 영상 매칭
            video_url = fetch_pexels_video(search_query, i)
            video_path = f"video_{i}.mp4"
            with open(video_path, "wb") as f:
                f.write(requests.get(video_url, timeout=30).content)

            bg_video_clip = process_video_clip(video_path, total_duration)

            # 4. 자막 타임라인 싱크 맞추기 (Whisper 분석 데이터 기반)
            subtitle_clips = []
            segments = result.get("segments", [])
            
            for segment in segments:
                words = segment.get("words", [])
                if not words:
                    # 단어 분할이 안 된 경우 세그먼트 전체 기준
                    txt = segment.get("text", "").strip()
                    if txt:
                        start = segment["start"]
                        end = min(segment["end"], total_duration)
                        dur = max(0.1, end - start)
                        img_np = render_subtitle_image(txt)
                        sub_clip = (ImageClip(img_np)
                                    .set_start(start)
                                    .set_duration(dur)
                                    .set_position(('center', 0.75), relative=True))
                        subtitle_clips.append(sub_clip)
                else:
                    for w in words:
                        word_txt = w["word"].strip()
                        if not word_txt:
                            continue
                        start = w["start"]
                        end = min(w["end"], total_duration)
                        dur = max(0.1, end - start)
                        img_np = render_subtitle_image(word_txt)
                        sub_clip = (ImageClip(img_np)
                                    .set_start(start)
                                    .set_duration(dur)
                                    .set_position(('center', 0.75), relative=True))
                        subtitle_clips.append(sub_clip)

            combined_clip = CompositeVideoClip([bg_video_clip] + subtitle_clips).set_audio(audio_clip)
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

        send_telegram_message("🎬 PPT 스타일 초단위 싱크 숏츠 작성이 완료되었습니다!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)[:100]}")
        raise e

if __name__ == "__main__":
    main()
