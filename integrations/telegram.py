# integrations/telegram.py

import os
import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)


# ============================================================
# Telegram Integration
# ============================================================
#
# 책임:
#   - 텍스트 메시지 전송
#   - 완성 영상 전송
#
# ============================================================


def send_telegram_message(message):

    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN 없음")
        return False

    if not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_CHAT_ID 없음")
        return False

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    try:

        response = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": str(message),
            },
            timeout=20,
        )

        if response.ok:
            print("📨 Telegram 메시지 전송 완료")
            return True

        print(
            "⚠️ Telegram 메시지 전송 실패: "
            f"HTTP {response.status_code}"
        )

        return False

    except Exception as e:

        print(
            f"⚠️ Telegram 메시지 에러: {e}"
        )

        return False


# ============================================================
# 영상 전송
# ============================================================

def send_telegram_video(video_path):

    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN 없음")
        return False

    if not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_CHAT_ID 없음")
        return False

    if not os.path.exists(video_path):

        print(
            "⚠️ 전송할 영상이 없습니다: "
            f"{video_path}"
        )

        return False

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    )

    try:

        with open(
            video_path,
            "rb",
        ) as video_file:

            response = requests.post(
                url,
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                },
                files={
                    "video": video_file,
                },
                timeout=300,
            )

        if response.ok:

            print(
                "📤 Telegram 영상 전송 완료"
            )

            return True

        print(
            "⚠️ Telegram 영상 전송 실패: "
            f"HTTP {response.status_code}"
        )

        send_telegram_message(
            "⚠️ 영상 전송 실패\n"
            f"HTTP {response.status_code}"
        )

        return False

    except Exception as e:

        print(
            f"⚠️ Telegram 영상 전송 에러: {e}"
        )

        send_telegram_message(
            "⚠️ 영상 전송 에러\n"
            f"{str(e)[:300]}"
        )

        return False


# ============================================================
# Shorts 결과 요약
# ============================================================

def send_result_summary(
    script_data,
    duration,
):

    title = script_data.get(
        "title",
        "제목 없음",
    )

    topic = script_data.get(
        "topic",
        "소재 없음",
    )

    category = script_data.get(
        "category",
        "분야 없음",
    )

    novelty = script_data.get(
        "novelty_score",
        "?",
    )

    scenes = script_data.get(
        "scenes",
        [],
    )

    message = (
        "🎬 Shorts 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"✨ 신선도: {novelty}/10\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: {len(scenes)}개\n\n"
        "📦 영상 전송 중..."
    )

    return send_telegram_message(
        message
  )
