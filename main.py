import os
import asyncio
import requests
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
                send_telegram_message(f"⚠️ 영상 업로드 실패: {response.text}")
    except Exception as e:
        send_telegram_message(f"⚠️ 영상 전송 에러: {str(e)}")

async def generate_voice(text, output_path):
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
    await communicate.save(output_path)

# 비디오 길이 부족 시 반복(loop) 및 세로(1080x1920) 강제 크롭 (검은 화면 완벽 방지)
def process_video_clip(clip_path, duration):
    clip = VideoFileClip(clip_path)
    
    # 비디오 길이가 음성보다 짧으면 루프 실행
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

# 가독성 높은 숏폼 전용 자막 생성
def create_subtitle_clip(text, duration):
    target_w = 1080
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
    font_size = 52
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    img_w = int(target_w * 0.85)
    words = text.split()
    
    lines = []
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

        stroke_width = 5
        # 테두리(검은색)
        for adj_x in range(-stroke_width, stroke_width + 1):
            for adj_y in range(-stroke_width, stroke_width + 1):
                draw.text((x + adj_x, y + adj_y), line, font=font, fill="black")

        # 본문(노란색)
        draw.text((x, y), line, font=font, fill="#FFE600")
        y += line_height

    img_np = np.array(img)
    return ImageClip(img_np).set_duration(duration).set_position(('center', 0.72), relative=True)

def main():
    try:
        prompt = """
        유튜브 숏츠용 흥미로운 과학/자연 상식 대본 3문장을 만들어줘.
        [규칙]
        - 반드시 시청자의 호기심을 유발하는 하나의 일관된 주제로만 작성할 것.
        - 특수문자, 번호표시(1.,2.), 따옴표 절대로 없이 순수 한국어 문장만 3줄 작성.
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

            # 키워드 추출 시 '바다', '우주' 등 배경 영상에 어울리는 구체적 명사 강조
            keyword_prompt = f"""
            다음 문장의 분위기와 가장 잘 어울리는 HD 배경 비디오 검색용 영어 단어 1개만 골라줘.
            (예시: ocean, space, forest, galaxy, deep sea)
            문장: '{line}'
            답변: 단어 1개만
            """
            keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
            search_query = keyword_res.choices[0].message.content.strip().replace('"', '').replace('.', '')

            headers = {"Authorization": PEXELS_API_KEY}
            res = requests.get(f"https://api.pexels.com/videos/search?query={search_query}&per_page=3&orientation=portrait", headers=headers).json()
            
            video_path = f"video_{i}.mp4"
            if "videos" in res and res["videos"] and len(res["videos"]) > 0:
                video_url = res["videos"][0]["video_files"][0]["link"]
                with open(video_path, "wb") as f:
                    f.write(requests.get(video_url).content)
            else:
                # 대체 기본 우주/바다 힐링 영상
                video_url = "https://static-vecteezy.com/system/resources/previews/001/802/396/mp4/abstract-loop-background-free-video.mp4"
                with open(video_path, "wb") as f:
                    f.write(requests.get(video_url).content)

            # 비디오 가공 (루프 + 크롭)
            video_clip = process_video_clip(video_path, duration)
            txt_clip = create_subtitle_clip(line, duration)

            combined_clip = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)
            clip_list.append(combined_clip)

        # 연결 부위 매끄럽게 합성
        final_video = concatenate_videoclips(clip_list, method="compose")
        final_output_path = "final_shorts.mp4"
        
        final_video.write_videofile(
            final_output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="3000k"
        )

        send_telegram_message("🎬 고화질 숏츠 영상 생성이 완료되었습니다!")
        send_telegram_video(final_output_path)

    except Exception as e:
        send_telegram_message(f"오류 발생: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
