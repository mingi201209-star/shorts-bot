import os
import re
import json
import asyncio
import urllib.request
import urllib.parse
import openai
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx.all import crop, loop

openai.api_key = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": str(message)}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")

def send_telegram_video(video_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        with open(video_path, 'rb') as f:
            video_data = f.read()

        body = []
        body.append(f'--{boundary}'.encode('utf-8'))
        body.append(f'Content-Disposition: form-data; name="chat_id"'.encode('utf-8'))
        body.append(b'')
        body.append(str(TELEGRAM_CHAT_ID).encode('utf-8'))

        body.append(f'--{boundary}'.encode('utf-8'))
        body.append(f'Content-Disposition: form-data; name="video"; filename="shorts.mp4"'.encode('utf-8'))
        body.append(b'Content-Type: video/mp4')
        body.append(b'')
        body.append(video_data)
        body.append(f'--{boundary}--'.encode('utf-8'))
        body.append(b'')

        payload = b'\r\n'.join(body)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(payload))
        }
        req = urllib.request.Request(url, data=payload, headers=headers)
        urllib.request.urlopen(req, timeout=120)
    except Exception as e:
        send_telegram_message(f"비디오 전송 실패: {str(e)}")

async def generate_voice(text, output_path):
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
    await communicate.save(output_path)

def process_video_clip(clip_path, duration):
    clip = VideoFileClip(clip_path)
    
    if clip.duration < duration:
        clip = loop(clip, duration=duration)
    else:
        clip = clip.subclip(0, duration)

    w, h = clip.size
    target_w, target_h = 1080, 1920
    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        clip = crop(clip, x_center=w/2, width=new_w, height=h)
    else:
        new_h = int(w / target_ratio)
        clip = crop(clip, y_center=h/2, width=w, height=new_h)

    return clip.resize((target_w, target_h))

def render_subtitle_image(text):
    target_w = 1080
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf"
    font_size = 65
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    img_w = int(target_w * 0.88)
    
    lines = []
    words = text.split()
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        if w <= img_w:
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
        bbox = font.getbbox(line)
        line_w = bbox[2] - bbox[0]
        x = (img_w - line_w) // 2

        stroke_width = 7
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

            keyword_prompt = f"""
            Extract ONE English word for Pexels video search based on this sentence: '{line}'
            Respond with ONLY ONE ENGLISH WORD.
            """
            keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
            raw_keyword = keyword_res.choices[0].message.content.strip()
            
            # 순수 영문 알파벳만 추출
            search_query = re.sub(r'[^a-zA-Z]', '', raw_keyword)
            if not search_query:
                search_query = "nature"

            headers = {"Authorization": PEXELS_API_KEY}
            pexels_url = f"https://api.pexels.com/videos/search?query={search_query}&per_page=3&orientation=portrait"
            
            req = urllib.request.Request(pexels_url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    data = json.loads(res.read().decode('utf-8'))
            except:
                data = {}

            video_path = f"video_{i}.mp4"
            if "videos" in data and len(data["videos"]) > 0:
                video_url = data["videos"][0]["video_files"][0]["link"]
                urllib.request.urlretrieve(video_url, video_path)
            else:
                fallback_url = "https://static-vecteezy.com/system/resources/previews/001/802/396/mp4/abstract-loop-background-free-video.mp4"
                urllib.request.urlretrieve(fallback_url, video_path)

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
        send_telegram_message("작업 중 오류 발생 (로그 확인 필요)")
        raise e

if __name__ == "__main__":
    main()
