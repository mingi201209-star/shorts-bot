from moviepy.editor import VideoFileClip

try:
    from moviepy.video.fx.all import crop, loop
except ImportError:
    import moviepy.video.fx.crop as crop
    import moviepy.video.fx.loop as loop


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


def process_video_clip(
    clip_path,
    duration
):
    """
    영상을 목표 길이 + 9:16 + 1080x1920으로 변환
    """

    clip = VideoFileClip(
        clip_path
    )

    try:

        # 영상이 짧으면 반복
        if clip.duration < duration:

            try:
                clip = loop(
                    clip,
                    duration=duration
                )

            except Exception:
                clip = clip.loop(
                    duration=duration
                )

        # 영상이 길면 자르기
        else:

            clip = clip.subclip(
                0,
                duration
            )

        w, h = clip.size

        target_ratio = (
            VIDEO_WIDTH / VIDEO_HEIGHT
        )

        current_ratio = w / h

        # 가로 영상
        if current_ratio > target_ratio:

            new_w = int(
                h * target_ratio
            )

            try:

                clip = crop(
                    clip,
                    x_center=w / 2,
                    width=new_w,
                    height=h
                )

            except Exception:

                clip = clip.crop(
                    x_center=w / 2,
                    width=new_w,
                    height=h
                )

        # 세로 영상
        else:

            new_h = int(
                w / target_ratio
            )

            try:

                clip = crop(
                    clip,
                    y_center=h / 2,
                    width=w,
                    height=new_h
                )

            except Exception:

                clip = clip.crop(
                    y_center=h / 2,
                    width=w,
                    height=new_h
                )

        # 최종 크기
        clip = clip.resize(
            (
                VIDEO_WIDTH,
                VIDEO_HEIGHT
            )
        )

        return clip

    except Exception:

        clip.close()

        raise
