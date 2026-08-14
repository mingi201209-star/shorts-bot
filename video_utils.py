import os

from moviepy.editor import VideoFileClip

try:
    from moviepy.video.fx.all import crop, loop
except ImportError:
    import moviepy.video.fx.crop as crop
    import moviepy.video.fx.loop as loop


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


def download_video(video_url, output_path, requests_module):
    print(f"⬇️ 영상 다운로드: {output_path}")

    response = requests_module.get(
        video_url,
        timeout=60
    )

    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    if (
        not os.path.exists(output_path)
        or os.path.getsize(output_path) < 1000
    ):
        raise RuntimeError(
            "영상 다운로드 결과가 비정상적입니다."
        )


def process_video_clip(clip_path, duration):
    clip = VideoFileClip(clip_path)

    try:
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

        # 가로 영상 → 중앙 크롭
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

        # 세로 영상 → 중앙 크롭
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

        # 최종 9:16
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
