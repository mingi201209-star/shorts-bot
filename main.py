from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx.all import crop # 크롭 기능 임포트

# ... (앞부분 생략: API키, 텔레그램 함수 등은 동일) ...

    # ... (대본 생성 루프 내부) ...
        # [2번 강화] 9:16 자동 크롭 로직
        video_clip = VideoFileClip(video_path)
        w, h = video_clip.size
        target_ratio = 9/16
        if w/h > target_ratio: # 가로가 더 긴 경우
            new_w = h * target_ratio
            x1 = (w - new_w) / 2
            video_clip = crop(video_clip, x1=x1, y1=0, x2=x1+new_w, y2=h)
        else: # 세로가 더 긴 경우
            new_h = w / target_ratio
            y1 = (h - new_h) / 2
            video_clip = crop(video_clip, x1=0, y1=y1, x2=w, y2=y1+new_h)
        video_clip = video_clip.resize(height=1920).subclip(0, min(duration, 5))

        # [1번 강화] 다이내믹 자막 (단어 단위 분할 로직)
        words = line.split()
        word_clips = []
        start_time = 0
        word_duration = duration / len(words)
        
        for i, word in enumerate(words):
            txt_clip = TextClip(
                word, fontsize=70, color='yellow', font='NanumGothicBold',
                stroke_color='black', stroke_width=4, method='caption',
                size=(video_clip.w * 0.9, None)
            ).set_start(start_time).set_duration(word_duration).set_position(('center', 'center'))
            word_clips.append(txt_clip)
            start_time += word_duration

        combined_clip = CompositeVideoClip([video_clip] + word_clips).set_audio(audio_clip)
        clip_list.append(combined_clip)
