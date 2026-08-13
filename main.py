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
    # 1. 후킹 프롬프트 대폭 강화 (첫 문장부터 시청자의 통념을 강력하게 깨는 구조)
    prompt = """
    유튜브 숏츠 상위 1% 크리에이터로서, 스와이프를 멈추게 만드는 1분짜리 지식 숏츠 대본 3문장을 작성해줘.
    [엄격한 규칙]
    - 1문장(초강력 후킹): "설마 아직도 ~라고 생각하시나요?" 혹은 대중의 상식을 완전히 뒤엎는 충격적인 질문이나 반전 팩트. (시청자가 스와이프를 못 하고 멈추게 만들어야 함)
    - 2문장(핵심 설명): 1문장의 주장을 뒷받침하는 구체적이고 흥미로운 과학적/역사적 원리.
    - 3문장(여운/반전): 여운을 주거나 가볍게 뒤통수를 치는 마무리 문장.
    - 출력은 오직 3줄의 문장만 출력할 것 (번호나 불필요한 기호 금지).
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

        # 2. Pexels 키워드 매칭 정교화 (시각적으로 몰입감 있는 구체적 영어 단어/사물 유도)
        keyword_prompt = f"""
        다음 문장을 시각적으로 극대화해서 보여주기 위해, Pexels 영상 검색에 사용할 '가장 시각적이고 구체적인 명사 또는 핵심 사물/풍경' 딱 1개만 영단어로 골라줘.
        - 규칙: 추상적인 단어(knowledge, fact 등) 금지. 영상으로 즉시 표현할 수 있는 구체적 대상(예: brain, rocket, money, ocean 등)일 것.
        - 문장: '{line}'
        - 출력: 영단어 1개만 출력
        """
        keyword_res = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": keyword_prompt}])
        search_query = keyword_res.choices[0].message.content.strip().replace('"', '').lower()

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

        # 3. 자막 가독성 및 디자인 업그레이드 (폰트 크기 확대, 두꺼운 외곽선으로 시선 강탈)
        txt_clip = TextClip(
            line,
            fontsize=52,             # 글씨 크기를 키워 모바일 가독성 극대화
            color='yellow',          # 노란색 메인 컬러
            font='NanumGothicBold',  # 굵은 나눔고딕
            stroke_color='black',    # 검은색 테두리
            stroke_width=4,          # 테두리를 더 두껍게 해 가독성 강화
            size=(video_clip.w * 0.85, None), # 화면 너비의 85%를 활용해 줄바꿈 최적화
            method='caption'
        ).set_duration(duration).set_position(('center', 'center')) # 화면 정중앙 또는 하단 배치 선택 가능 (현재는 안정적인 센터-하단 느낌을 위해 y축 조절 가능)

        combined_clip = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)
        clip_list.append(combined_clip)

    final_video = concatenate_videoclips(clip_list)
    final_output_path = "final_shorts.mp4"
    final_video.write_videofile(final_output_path, fps=30, codec="libx264", audio_codec="aac")

    send_telegram_message("후킹 및 자막/키워드 업그레이드 완료! 최종 숏츠 영상을 확인하세요.")
    send_telegram_video(final_output_path)

except Exception as e:
    send_telegram_message(f"오류 발생: {str(e)}")
    raise e
