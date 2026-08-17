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
# TTS V2
# ============================================================
#
# Edge TTS prosody 값은 문자열 형식이어야 한다.
# 예: +8%, +0%, +0Hz
# 환경변수로 바로 조절 가능하게 유지한다.
# ============================================================

TTS_VOICE = os.environ.get(
    "TTS_VOICE",
    "ko-KR-InJoonNeural",
)

TTS_RATE = os.environ.get(
    "TTS_RATE",
    "+8%",
)

TTS_VOLUME = os.environ.get(
    "TTS_VOLUME",
    "+0%",
)

TTS_PITCH = os.environ.get(
    "TTS_PITCH",
    "+0Hz",
)


# ============================================================
# Pexels B-roll V2
# ============================================================
#
# 검색 결과 전체를 해상도순으로 재정렬하지 않는다.
# Pexels가 관련도순으로 준 앞쪽 결과만 후보로 인정하고,
# 그 안에서 세로 비율 / 해상도 / 길이를 비교한다.
# ============================================================

PEXELS_SEARCH_PER_PAGE = int(
    os.environ.get(
        "PEXELS_SEARCH_PER_PAGE",
        "8",
    )
)

PEXELS_RELEVANT_TOP_N = int(
    os.environ.get(
        "PEXELS_RELEVANT_TOP_N",
        "3",
    )
)

PEXELS_MIN_DURATION = float(
    os.environ.get(
        "PEXELS_MIN_DURATION",
        "4.0",
    )
)


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
