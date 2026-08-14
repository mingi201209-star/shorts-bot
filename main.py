import os
import asyncio
import requests
import openai
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx.all import crop

openai.api_key = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

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
                send_telegram_message(f"⚠️ 영상 업로드 실패 ({response.status_code}): {response.text}")
    except Exception as e:
        send_telegram_message(f"⚠️ 영상 전송 에러: {str(e)}")

async def generate_voice(text, output_path):
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
    await communicate.save(output_path)

# 가로/세로 모든 비디오를 1080x1920 세로 규격으로 변환
def process_video_clip(clip_path, duration):
    clip = VideoFileClip(clip_path)
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

    clip = clip.resize((target_w, target_h))
    return clip.subclip(0, min(duration, clip.duration if clip.duration else duration))

def create_subtitle_clip(text, duration):
    target_w, target_h = 1080, 1920
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
    font_size = 50
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    img_w = int(target_w * 0.85)
    
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

    line_height = font_size + 15
    img_h = line_height * len(lines) + 30

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = 15
    for line in lines:
        bbox = font.getbbox(line)
        line_w = bbox[2] - bbox[0]
        x = (img_w - line_w) // 2

        stroke_width = 4
        for adj_x in range(-stroke_width, stroke_width + 1):
            for adj_y in range(-stroke_width, stroke_width + 1):
                draw.text((x + adj_x, y + adj_y), line, font=font, fill="black")

        draw.text((x, y), line, font=font, fill="yellow")
        y += line_height

    img_np = np.array(img)
    return ImageClip(img_np).set_duration(duration).set_position(('center', 0.75), relative=True)

def main():
    try:
        prompt = """
        유튜브 숏츠용 재미있는 상식 대본을 작성해줘.
        [규칙]
        - 반드시 하나의 주제에 대해서만 연결되게 작성할 것.
        - 숫자인덱스(1., 2. 등), 특수문자, 따옴표 없이 순수 문장만 3줄로 작성할 것. (한 줄에 한 문장)
        - 예시:
        당신이 몰랐던 흥미로운 우주의 비밀을 알고 계신가요?
        우주는 지금 이 순간에도 빛보다 빠른 속도로 커지고 있습니다.
        과연 우주의 끝에는 무엇이 기다리고 있을까요?
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

            keyword_prompt = f"다음 문장에 어울리는 영상 검색용 영어 단어 딱 1개만 출력해줘: '{line}'"
            keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
            search_query = keyword_res.choices[0].message.content.strip().replace('"', '').replace('.', '')

            headers = {"Authorization": PEXELS_API_KEY}
            res = requests.get(f"https://api.pexels.com/videos/search?query={search_query}&per_page=1&orientation=portrait", headers=headers).json()
            
            video_path = f"video_{i}.mp4"
            if "videos" in res and res["videos"] and len(res["videos"]) > 0:
                video_url = res["videos"][0]["video_files"][0]["link"]
                with open(video_path, "wb") as f:
                    f.write(requests.get(video_url).content)
            else:
                # 대체 기본 영상다운
                video_url = "https://static-vecteezy.com/system/resources/previews/001/802/396/mp4/abstract-loop-background-free-video.mp4"
                with open(video_path, "wb") as f:
                    f.write(requests.get(video_url).content)

            video_clip = process_video_clip(video_path, duration)
            txt_clip = create_subtitle_clip(line, duration)

            combined_clip = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)
            clip_list.append(combined_clip)

        # compose 방식으로 안정적으로 합성 (글리치 방지)
        final_video = concatenate_videoclips(clip_list, method="compose")
        final_output_path = "final_shorts.mp4"
        
        final_video.write_videofile(
            final_output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="3000k"
        )

        send_telegram_message("🎬 숏츠 생성이 완료되었습니다!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
