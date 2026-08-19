from pathlib import Path


# Keep this patch intentionally narrow: production TTS default rate and
# Hook-only subtitle timing. Legacy/Hook-OFF subtitle behavior is untouched.

config_path = Path("config.py")
config_text = config_path.read_text(encoding="utf-8")

old_rate = '''TTS_RATE = os.environ.get(
    "TTS_RATE",
    "+3%",
)
'''
new_rate = '''TTS_RATE = os.environ.get(
    "TTS_RATE",
    "+13%",
)
'''

if new_rate not in config_text:
    if config_text.count(old_rate) != 1:
        raise RuntimeError("TTS rate marker mismatch")
    config_text = config_text.replace(old_rate, new_rate, 1)

old_comment = "# +8%는 다소 급하게 들릴 수 있어 기본 속도를 +3%로 낮춘다."
new_comment = (
    "# 기존 +3% 대비 실제 발화 속도를 약 10% 높이기 위해 "
    "기본 속도를 +13%로 조정한다."
)
if new_comment not in config_text:
    if config_text.count(old_comment) != 1:
        raise RuntimeError("TTS rate comment marker mismatch")
    config_text = config_text.replace(old_comment, new_comment, 1)

config_path.write_text(config_text, encoding="utf-8")

subtitle_path = Path("video/subtitle_engine.py")
subtitle_text = subtitle_path.read_text(encoding="utf-8")

old_chunks = '''    chunks = split_subtitle_text(
        text
    )
'''
new_chunks = '''    # Selected experimental Hook text is already constrained to 12~16
    # visible characters. Keep the exact TTS Hook as one subtitle chunk so
    # it is present from the first rendered frame. Legacy/Hook-OFF keeps the
    # existing subtitle splitter unchanged.
    if hook_mode:
        hook_text = str(text or "").strip()
        chunks = [hook_text] if hook_text else []
    else:
        chunks = split_subtitle_text(
            text
        )
'''

if new_chunks not in subtitle_text:
    if subtitle_text.count(old_chunks) != 1:
        raise RuntimeError("Hook subtitle chunk marker mismatch")
    subtitle_text = subtitle_text.replace(old_chunks, new_chunks, 1)

old_start = '''    start = 0.0

    for idx, (chunk, weight) in enumerate(
'''
new_start = '''    start = 0.0

    if hook_mode:
        print(
            "[HOOK] subtitle_start=0.000s "
            f"duration={duration:.3f}s "
            "exact_tts_text=true"
        )

    for idx, (chunk, weight) in enumerate(
'''

if new_start not in subtitle_text:
    if subtitle_text.count(old_start) != 1:
        raise RuntimeError("Hook subtitle start marker mismatch")
    subtitle_text = subtitle_text.replace(old_start, new_start, 1)

subtitle_path.write_text(subtitle_text, encoding="utf-8")

print("✅ Retention hotfix applied: TTS +13%, Hook subtitle starts at 0.000s")
