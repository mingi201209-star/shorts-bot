# video/subtitle_timing.py
"""Shorts subtitle timing helpers.

Keeps caption chunks short and aligns their boundaries to the spoken TTS audio
when a local audio file is available.  Alignment is best-effort: production
must still render if Whisper is unavailable, in which case the caller can use
the existing deterministic duration-weighted fallback.
"""

import os
import re

CAPTION_LEAD_SECONDS = 0.18
MAX_CAPTION_WORDS = 5


def normalize_caption_text(text):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", str(text or "")).lower()


def _short_groups(words):
    groups = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= MAX_CAPTION_WORDS or re.search(r"[,;:!?…]$", word):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def align_subtitle_chunks_to_audio(text, audio_path):
    """Return [(caption, start, end), ...] using Whisper word timestamps.

    Returns [] when alignment is unavailable or unreliable so callers can
    safely retain the existing fallback path.
    """
    if not audio_path or not os.path.isfile(audio_path):
        return []

    try:
        from faster_whisper import WhisperModel
    except Exception:
        return []

    try:
        model_name = os.environ.get("SUBTITLE_ALIGN_MODEL", "tiny")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(
            audio_path,
            language="ko",
            word_timestamps=True,
            vad_filter=False,
            beam_size=1,
        )
        spoken = []
        for segment in segments:
            for word in (segment.words or []):
                token = str(word.word or "").strip()
                if token and word.start is not None and word.end is not None:
                    spoken.append((token, float(word.start), float(word.end)))
    except Exception:
        return []

    if not spoken:
        return []

    # ASR text is used only for timing. Captions retain the approved script
    # wording by mapping script words monotonically onto spoken word times.
    script_words = str(text or "").strip().split()
    if not script_words:
        return []

    # Refuse alignment when transcription is obviously incomplete.
    ratio = len(spoken) / max(1, len(script_words))
    if ratio < 0.55 or ratio > 1.8:
        return []

    groups = _short_groups(script_words)
    result = []
    script_i = 0
    spoken_i = 0

    for group in groups:
        count = len(group)
        if spoken_i >= len(spoken):
            return []

        # Proportional monotonic mapping tolerates Korean tokenizer differences
        # while anchoring every caption to actual speech timestamps.
        next_script_i = script_i + count
        end_spoken_i = round(next_script_i * len(spoken) / len(script_words))
        end_spoken_i = max(spoken_i + 1, min(len(spoken), end_spoken_i))

        start = max(0.0, spoken[spoken_i][1] - CAPTION_LEAD_SECONDS)
        end = spoken[end_spoken_i - 1][2]
        if end <= start:
            return []

        result.append((" ".join(group), start, end))
        script_i = next_script_i
        spoken_i = end_spoken_i

    return result
