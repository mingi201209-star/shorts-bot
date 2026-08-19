import importlib
import math



def _assert(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"✅ PASS | {message}")


# Production hotfix must already have been applied before importing config.
config = importlib.import_module("config")
subtitle_engine = importlib.import_module("video.subtitle_engine")


_assert(config.TTS_RATE == "+13%", "Production default TTS rate is +13%")
old_speed = 1.03
new_speed = 1.13
relative_gain = new_speed / old_speed - 1.0
_assert(
    abs(relative_gain - 0.0970873786) < 1e-6,
    "TTS default is about 9.7% faster than previous +3% rate",
)

# Hook mode must keep the exact Hook text as one clip starting at zero.
original_render = subtitle_engine.render_subtitle_image
original_choose = subtitle_engine.choose_safe_subtitle_y
try:
    import numpy as np

    subtitle_engine.render_subtitle_image = lambda text: np.zeros((120, 1080, 4), dtype=np.uint8)
    subtitle_engine.choose_safe_subtitle_y = lambda *args, **kwargs: 123

    hook_text = "벌집 구조는 왜 육각형일까요?"
    hook_clips = subtitle_engine.create_subtitle_clips(
        hook_text,
        2.4,
        video_clip=None,
        hook_mode=True,
    )
    _assert(len(hook_clips) == 1, "Hook subtitle remains one exact text chunk")
    _assert(abs(float(hook_clips[0].start) - 0.0) < 1e-9, "Hook subtitle starts at 0.000s")
    _assert(abs(float(hook_clips[0].duration) - 2.4) < 1e-9, "Hook subtitle covers full Hook TTS duration")

    # Hook OFF / legacy continues using the normal splitter.
    legacy_clips = subtitle_engine.create_subtitle_clips(
        "첫 문장입니다. 두 번째 문장입니다.",
        2.4,
        video_clip=None,
        hook_mode=False,
    )
    _assert(len(legacy_clips) >= 2, "Hook OFF keeps legacy subtitle splitting")
    _assert(abs(float(legacy_clips[0].start) - 0.0) < 1e-9, "Legacy first subtitle timing remains unchanged")
finally:
    subtitle_engine.render_subtitle_image = original_render
    subtitle_engine.choose_safe_subtitle_y = original_choose

print("✅ RETENTION REGRESSION TESTS PASS")
