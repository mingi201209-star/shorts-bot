import os


# ============================================================
# Environment Variables
# ============================================================

OPENAI_KEY = os.environ.get("OPENAI_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ============================================================
# Video Settings
# ============================================================

FPS = 30

MIN_SCENES = 12
MAX_SCENES = 13

TARGET_MIN_SECONDS = 75
TARGET_MAX_SECONDS = 90

VIDEO_BITRATE = "5000k"

TTS_VOICE = "ko-KR-InJoonNeural"

OUTPUT_VIDEO = "final_shorts.mp4"


# ============================================================
# Topic Settings
# ============================================================

RECENT_TOPICS_FILE = "recent_topics.json"

MAX_RECENT_TOPICS = 20

MIN_NOVELTY_SCORE = 7

MAX_SCRIPT_ATTEMPTS = 3
