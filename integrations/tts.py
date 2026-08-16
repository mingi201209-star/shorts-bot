# integrations/tts.py

import os
import asyncio

import edge_tts

from config import TTS_VOICE


# ============================================================
# TTS Engine
# ============================================================
#
# 책임:
#   - 한국어 음성 생성
#   - 음성 파일 저장 확인
#
# 하지 않는 것:
#   - 대본 생성
#   - 영상 생성
#   - 자막 생성
#   - Telegram 전송
#
# ============================================================


async def generate_voice(
    text,
    output_path,
):
    """
    Edge TTS를 이용해 음성 파일을 생성한다.
    """

    text = str(text).strip()

    if not text:
        raise ValueError(
            "TTS로 변환할 텍스트가 비어 있습니다."
        )

    communicate = edge_tts.Communicate(
        text,
        TTS_VOICE,
    )

    await communicate.save(
        output_path
    )


def create_voice(
    text,
    output_path,
):
    """
    main/video_engine에서 사용하는 동기식 TTS 인터페이스.
    """

    text = str(text).strip()

    if not text:
        raise ValueError(
            "TTS 텍스트가 비어 있습니다."
        )

    print(
        f"🎙️ TTS 생성: {text}"
    )

    try:

        asyncio.run(
            generate_voice(
                text,
                output_path,
            )
        )

    except Exception as e:

        raise RuntimeError(
            f"TTS 생성 실패: {e}"
        ) from e

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            f"TTS 파일이 생성되지 않았습니다: "
            f"{output_path}"
        )

    if os.path.getsize(
        output_path
    ) <= 0:

        raise RuntimeError(
            f"TTS 파일 크기가 0입니다: "
            f"{output_path}"
        )

    print(
        f"✅ TTS 생성 완료: {output_path}"
    )

    return output_path
