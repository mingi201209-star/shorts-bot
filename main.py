import os
import requests
import openai
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

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

try:
    prompt = """
    유튜브 숏츠 크리에이터로서 1분짜리 지식 숏츠 대본 3문장을 작성해줘.
    [규칙]
    - 과학적, 역사적, 사실적 근거가 확실한 팩트만 다룰 것.
    - 1문장(후킹): 시청자의 통념을 깨는 질문.
    - 2문장(설명): 구체적인 원리나 상식 설명.
    - 3문장(여운): 질문이나 여운.
    """
    
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
    lines = [line.strip() for line in response.choices[0].message.content.strip().split("\n") if line.strip()]

    clip_list = []

    for i, line in enumerate(lines):
        audio_path = f"audio_{i}.mp3"
        tts = gTTS(text=line, lang='ko')
        tts.save(audio_path)
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        keyword_prompt = f"""
        다음 문장을 시각적으로 보여주기 위해, 영상 검색에 사용할 '가장 핵심적인 구체적 명사' 딱 1개만 영어로 골라줘.
        - 규칙: 형용사, 동사, 추상적 단어 금지.
        - 문장: '{line}'
        - 출력: 단어 1개만 출력
        """
        keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
        search_query = keyword_res.choices[0].message.content.strip().replace('"', '')

        headers = {"Authorization": PEXELS_API_KEY}
        res = requests.get(f"https://api.pexels.com/videos/search?query={search_query}&per_page=1", headers=headers).json()
        
        video_path = f"video_{i}.mp4"
        if "videos" in res and res["videos"]:
            video_url = res["videos"][0]["video_files"][0]["link"]
            with open(video_path, "wb") as f:
                f.write(requests.get(video_url).content)
            video_clip = VideoFileClip(video_path).subclip(0, min(duration, 5))
        else:
            video_clip = VideoFileClip("default_video.mp4").subclip(0, duration)

        txt_clip = TextClip(
            line,
            fontsize=45,
            color='yellow',
            font='NanumGothicBold',
            stroke_color='black',
            stroke_width=3,
            size=(video_clip.w * 0.8, None),
            method='caption'
        ).set_duration(duration).set_position(('center', 'bottom'))

        combined_clip = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)
        clip_list.append(combined_clip)

    final_video = concatenate_videoclips(clip_list)
    final_output_path = "final_shorts.mp4"
    final_video.write_videofile(final_output_path, fps=30, codec="libx264", audio_codec="aac")

    send_telegram_message("🎬 자막 합성 완료! 아래 생성된 영상 파일을 확인하세요.")
    send_telegram_video(final_output_path)

except Exception as e:
    send_telegram_message(f"오류 발생: {str(e)}")
    raise e
