# config.py

import os


# ============================================================
# API / 환경변수
# ============================================================

OPENAI_KEY = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID"
)


# ============================================================
# 영상 기본 설정
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

FPS = 30

VIDEO_BITRATE = "5000k"

OUTPUT_VIDEO = "final_shorts.mp4"


# ============================================================
# Shorts 길이
# ============================================================

MIN_SCENES = 12
MAX_SCENES = 13

TARGET_MIN_SECONDS = 75
TARGET_MAX_SECONDS = 90


# ============================================================
# TTS
# ============================================================

TTS_VOICE = "ko-KR-InJoonNeural"


# ============================================================
# 소재 관리
# ============================================================

RECENT_TOPICS_FILE = "recent_topics.json"

MAX_RECENT_TOPICS = 20


# ============================================================
# V3 콘텐츠 필터
# ============================================================

MIN_NOVELTY_SCORE = 7

MAX_SCRIPT_ATTEMPTS = 3


# ============================================================
# V3 후킹 기준
# ============================================================

HOOK_MAX_SECONDS = 3

MIN_HOOK_STRENGTH = 7

REQUIRE_EMOTIONAL_TRIGGER = True


# ============================================================
# V3 소재 기준
# ============================================================

MIN_PUBLIC_INTEREST = 7

MIN_SURPRISE_SCORE = 7

MIN_VISUAL_SCORE = 7


# ============================================================
# V3 B-roll 기준
# ============================================================

MIN_VISUAL_MATCH_SCORE = 85

MAX_REPEATED_KEYWORD = 2


# ============================================================
# 자막
# ============================================================

SUBTITLE_FONT_SIZE = 70

SUBTITLE_STROKE_WIDTH = 9

SUBTITLE_TEXT_COLOR = "#FFE600"

SUBTITLE_STROKE_COLOR = "black"


# ============================================================
# 작업 디렉터리
# ============================================================

TEMP_DIR = "workspace/temp"


# ============================================================
# 환경변수 검사
# ============================================================

def get_missing_environment_variables():

    required = {
        "OPENAI_KEY": OPENAI_KEY,
        "PEXELS_API_KEY": PEXELS_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }

    return [
        name
        for name, value in required.items()
        if not value
    ]
