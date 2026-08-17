import asyncio
import os
import re

import edge_tts

from config import (
    TTS_VOICE,
    TTS_RATE,
    TTS_VOLUME,
    TTS_PITCH,
)


# ============================================================
# TTS Engine V2
# ============================================================
#
# 책임:
# - 한국어 음성 생성
# - Shorts용 약간 빠른 기본 속도
# - 문장부호 / 공백 정리
# - rate / volume / pitch 설정
# - 생성 파일 검증
# ============================================================


def prepare_tts_text(text):
    """Edge TTS가 자연스럽게 읽도록 입력 문장을 정리한다."""

    text = str(text or "").strip()

    if not text:
        raise ValueError(
            "TTS로 변환할 텍스트가 비어 있습니다."
        )

    # 줄바꿈과 연속 공백을 한 칸으로 정리한다.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # 반복 문장부호를 과도하게 늘이지 않는다.
    text = re.sub(
        r"([!?.,])\1{2,}",
        r"\1\1",
        text,
    )

    # 장면 끝이 글자/숫자로 끝나면 종결감을 준다.
    # Edge TTS가 장면 마지막 음절을 급하게 끊는 현상을 줄인다.
    if text[-1] not in ".?!…~":
        text += "."

    return text


async def generate_voice(
    text,
    output_path,
):
    """Edge TTS를 이용해 음성 파일을 생성한다."""

    prepared = prepare_tts_text(
        text
    )

    communicate = edge_tts.Communicate(
        prepared,
        TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
        pitch=TTS_PITCH,
    )

    await communicate.save(
        output_path
    )


def create_voice(
    text,
    output_path,
):
    """main/video_engine에서 사용하는 동기식 TTS 인터페이스."""

    prepared = prepare_tts_text(
        text
    )

    print(
        "🎙️ TTS 생성: "
        f"voice={TTS_VOICE} "
        f"rate={TTS_RATE} "
        f"pitch={TTS_PITCH}"
    )

    try:
        asyncio.run(
            generate_voice(
                prepared,
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
            "TTS 파일이 생성되지 않았습니다: "
            f"{output_path}"
        )

    if os.path.getsize(
        output_path
    ) <= 0:
        raise RuntimeError(
            "TTS 파일 크기가 0입니다: "
            f"{output_path}"
        )

    print(
        f"✅ TTS 생성 완료: {output_path}"
    )

    return output_path
