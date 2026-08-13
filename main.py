import os
import re
import requests
import openai
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx.all import crop

openai.api_key = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def send_telegram_video(video_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video_file:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"video": video_file})

def remove_emojis(text):
    # 이모티콘 및 특수 유니코드 문자 제거 (ImageMagick 에러 방지)
    emoji_pattern = re.compile(
        r"["
        r"\U00010000-\U0010ffff"
        r"\u200d"
        r"\u2600-\u27bf"
        r"]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r"", text)

try:
    prompt = """
    유튜브 숏츠 상위 1% 크리에이터로서, 스와이프를 멈추게 만드는 1분짜리 지식 숏츠 대본 3문장을 작성해줘.
    [엄격한 규칙]
    - 이모티콘, 특수 기호(🔥, 🎬 등) 절대 사용 금지. 오직 순수 한국어 텍스트와 기본 문장부호(?, ., ,)만 사용할 것.
    - 1문장(초강력 후킹): "설마 아직도 ~라고 생각하시나요?" 혹은 대중의 상식을 완전히 뒤엎는 충격적인 질문이나 반전 팩트.
    - 2문장(핵심 설명): 1문장의 주장을 뒷받침하는 구체적이고 흥미로운 과학적/역사적 원리.
    - 3문장(여운/반전): 여운을 주거나 가볍게 뒤통수를 치는 마무리 문장.
    - 출력은 오직 3줄의 문장만 출력할 것 (번호나 불필요한 기호 금지).
    """
    
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
    
    # 텍스트 추출 및 이모티콘 정화 작업 수행
    raw_lines = [line.strip() for line in response.choices[0].message.content.strip().split("\n") if line.strip()]
    lines = [remove_emojis(line) for line in raw_lines]

    clip_list = []

    for i, line in enumerate(lines):
        if not line: continue
        
        audio_path = f"audio_{i}.mp3"
        tts = gTTS(text=line, lang='ko')
        tts.save(audio_path)
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        keyword_prompt = f"""
        다음 문장을 시각적으로 극대화해서 보여주기 위해, Pexels 영상 검색에 사용할 '가장 시각적이고 구체적인 명사 또는 핵심 사물/풍경' 딱 1개만 영단어로 골라줘.
        - 규칙: 이모티콘 금지. 추상적인 단어 금지. 영상으로 즉시 표현할 수 있는 구체적 대상(예: brain, rocket, money, ocean 등)일 것.
        - 문장: '{line}'
        - 출력: 영단어 1개만 출력
        """
        keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
        search_query = remove_emojis(keyword_res.choices[0].message.content).strip().replace('"', '').lower()

        headers = {"Authorization": PEXELS_API_KEY}
        res = requests.get(f"https://api.pexels.com/videos/search?query={search_query}&per_page=1", headers=headers).json()
        
        video_path = f"video_{i}.mp4"
        if "videos" in res and res["videos"]:
            video_url = res["videos"][0]["video_files"][0]["link"]
            with open(video_path, "wb") as f:
                f.write(requests.get(video_url).content)
            
            raw_video = VideoFileClip(video_path)
            w, h = raw_video.size
            target_ratio = 9/16
            if w/h > target_ratio:
                new_w = h * target_ratio
                x1 = (w - new_w) / 2
                video_clip = crop(raw_video, x1=x1, y1=0, x2=x1+new_w, y2=h)
            else:
                new_h = w / target_ratio
                y1 = (h - new_h) / 2
                video_clip = crop(raw_video, x1=0, y1=y1, x2=w, y2=y1+new_h)
            
            video_clip = video_clip.resize(height=1920).subclip(0, min(duration, 5))
        else:
            video_clip = VideoFileClip("default_video.mp4").subclip(0, duration)

        words = line.split()
        word_clips = []
        start_time = 0
        word_duration = duration / len(words) if words else duration
        
        for word in words:
            txt_clip = TextClip(
                word, 
                fontsize=70, 
                color='yellow', 
                font='NanumGothicBold',
                stroke_color='black', 
                stroke_width=4, 
                method='caption',
                size=(video_clip.w * 0.9, None)
            ).set_start(start_time).set_duration(word_duration).set_position(('center', 'center'))
            
            word_clips.append(txt_clip)
            start_time += word_duration

        combined_clip = CompositeVideoClip([video_clip] + word_clips).set_audio(audio_clip)
        clip_list.append(combined_clip)

    final_video = concatenate_videoclips(clip_list)
    final_output_path = "final_shorts.mp4"
    final_video.write_videofile(final_output_path, fps=30, codec="libx264", audio_codec="aac")

    send_telegram_message("자막 합성 완료! 아래 생성된 영상 파일을 확인하세요.")
    send_telegram_video(final_output_path)

except Exception as e:
    send_telegram_message(f"오류 발생: {str(e)}")
    raise e
