from pathlib import Path


def _replace_once(text, old, new, label):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} marker mismatch")
    return text.replace(old, new, 1)


# ============================================================
# Script Generator: first 5 seconds must be direct, not introductory
# ============================================================
script_path = Path("content/script_generator.py")
script_text = script_path.read_text(encoding="utf-8")

old_banned = '''HOOK_BANNED_PATTERNS = [
    "있는 모습",
    "하는 장면",
    "보이는 모습",
    "보이고 있습니다",
    "놓여 있는",
    "놓여있는",
    "오늘은",
    "이번 영상에서는",
    "알아보겠습니다",
]
'''
new_banned = '''HOOK_BANNED_PATTERNS = [
    "있는 모습",
    "하는 장면",
    "보이는 모습",
    "보이고 있습니다",
    "놓여 있는",
    "놓여있는",
    "오늘은",
    "이번 영상에서는",
    "알아보겠습니다",
    "알려드릴게요",
    "알려드려요",
    "알아봅니다",
    "보여드릴게요",
    "보여드려요",
    "소개하겠습니다",
    "소개합니다",
]
'''
script_text = _replace_once(
    script_text,
    old_banned,
    new_banned,
    "script first-five banned phrasing",
)

old_scene_text = '''        text = str(
            scene.get("text", "")
        ).strip()

        visual_goal = str(
'''
new_scene_text = '''        text = str(
            scene.get("text", "")
        ).strip()

        if idx < 2:
            for banned in HOOK_BANNED_PATTERNS:
                if banned in text:
                    return False, (
                        f"{idx + 1}번 장면 첫 5초 금지 표현: {banned}"
                    )

        visual_goal = str(
'''
script_text = _replace_once(
    script_text,
    old_scene_text,
    new_scene_text,
    "script first-five deterministic intro guard",
)

old_story = '''[STORY]
Hook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.
첫 장면부터 본론에 들어간다.
"오늘은", "알아보겠습니다", "혹시 알고 계셨나요" 같은 도입은 금지한다.
후반부는 단순 요약이 아니라 처음 질문을 실제 답으로 보상해야 한다.
'''
new_story = '''[STORY]
Hook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.
첫 장면부터 본론에 들어간다.
"오늘은", "알아보겠습니다", "혹시 알고 계셨나요", "알려드릴게요", "보여드릴게요" 같은 도입/소개/예고는 금지한다.

[FIRST 5 SECONDS — RETENTION]
- 0~2초: Candidate 안에서 가장 이상하거나 놀라운 결과/현상을 첫 문장에 단정적으로 직접 말한다.
- 2~5초: 즉시 "왜?"가 생기게 만들고, 두 번째 Scene부터 답의 단서나 실제 원리를 바로 시작한다.
- 설명을 시작하겠다는 약속보다 이상현상/반전/결과 자체를 먼저 말한다.
- 첫 두 Scene 모두 대사와 visual_goal/keyword가 같은 핵심 대상·현상을 직접 가리켜야 한다.
- 단순 자극보다 대사와 화면의 직접 일치를 우선한다.

후반부는 단순 요약이 아니라 처음 질문을 실제 답으로 보상해야 한다.
'''
script_text = _replace_once(
    script_text,
    old_story,
    new_story,
    "script first-five prompt",
)
script_path.write_text(script_text, encoding="utf-8")


# ============================================================
# Edge TTS: use only supported request-level rate / volume / pitch
# ============================================================
tts_path = Path("integrations/tts.py")
tts_text = tts_path.read_text(encoding="utf-8")

old_tts_functions = '''async def generate_voice(
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
'''
new_tts_functions = '''def resolve_tts_prosody(text, hook_mode=False):
    """Return Edge TTS request-level prosody without unsupported SSML."""

    prepared = prepare_tts_text(text)
    explicit_rate = os.environ.get("TTS_RATE")
    explicit_pitch = os.environ.get("TTS_PITCH")

    hook_rate = os.environ.get(
        "TTS_HOOK_RATE",
        explicit_rate or TTS_RATE,
    )
    body_rate = os.environ.get(
        "TTS_BODY_RATE",
        explicit_rate or "+8%",
    )

    hook_pitch = os.environ.get(
        "TTS_HOOK_PITCH",
        explicit_pitch or "+3Hz",
    )
    question_pitch = os.environ.get(
        "TTS_QUESTION_PITCH",
        explicit_pitch or "+2Hz",
    )
    statement_pitch = os.environ.get(
        "TTS_STATEMENT_PITCH",
        explicit_pitch or "-1Hz",
    )

    if hook_mode:
        rate = hook_rate
        pitch = hook_pitch
        profile = "hook_energy"
    elif prepared.endswith("?"):
        rate = body_rate
        pitch = question_pitch
        profile = "body_question"
    else:
        rate = body_rate
        pitch = statement_pitch
        profile = "body_explanation"

    return {
        "profile": profile,
        "rate": rate,
        "volume": TTS_VOLUME,
        "pitch": pitch,
    }


async def generate_voice(
    text,
    output_path,
    *,
    hook_mode=False,
):
    """Edge TTS를 이용해 음성 파일을 생성한다."""

    prepared = prepare_tts_text(
        text
    )
    prosody = resolve_tts_prosody(
        prepared,
        hook_mode=hook_mode,
    )

    communicate = edge_tts.Communicate(
        prepared,
        TTS_VOICE,
        rate=prosody["rate"],
        volume=prosody["volume"],
        pitch=prosody["pitch"],
    )

    await communicate.save(
        output_path
    )


def create_voice(
    text,
    output_path,
    *,
    hook_mode=False,
):
    """main/video_engine에서 사용하는 동기식 TTS 인터페이스."""

    prepared = prepare_tts_text(
        text
    )
    prosody = resolve_tts_prosody(
        prepared,
        hook_mode=hook_mode,
    )

    print(
        "🎙️ TTS 생성: "
        f"voice={TTS_VOICE} "
        f"profile={prosody['profile']} "
        f"rate={prosody['rate']} "
        f"pitch={prosody['pitch']}"
    )

    try:
        asyncio.run(
            generate_voice(
                prepared,
                output_path,
                hook_mode=hook_mode,
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
'''
tts_text = _replace_once(
    tts_text,
    old_tts_functions,
    new_tts_functions,
    "Edge TTS prosody profiles",
)
tts_path.write_text(tts_text, encoding="utf-8")


# ============================================================
# Hook visual: reuse existing strict metadata gate for scene 2
# ============================================================
hook_visual_path = Path("video/hook_visual.py")
hook_visual_text = hook_visual_path.read_text(encoding="utf-8")

print_marker = '''def print_hook_visual_audit(audit):
'''
early_visual_function = '''def fetch_early_retention_pexels_video(scene):
    """Use the existing Hook metadata strict gate for the 2~5s scene."""

    original_query = str(scene.get("keyword", "")).strip()
    effective_query, context_lock = build_context_locked_query(original_query)
    historical = bool(context_lock)
    queries = [effective_query]

    if historical:
        fallback = _fallback_query_for_lock(context_lock)
        if fallback not in queries:
            queries.append(fallback)
    else:
        for fallback in _general_fallback_queries(effective_query):
            if fallback not in queries:
                queries.append(fallback)

    for search_query in queries:
        candidates = search_pexels_candidates(
            search_query,
            per_page=PEXELS_SEARCH_PER_PAGE,
        )
        safe_pool = _safe_candidate_pool(candidates, search_query, historical)
        scored = []

        for candidate in safe_pool:
            scores, total_score = _score_candidate(
                candidate,
                {**scene, "keyword": search_query},
            )
            scored.append({
                "candidate": candidate,
                "scores": scores,
                "total_score": total_score,
            })

        scored.sort(key=lambda item: item["total_score"], reverse=True)
        strict = [item for item in scored if _passes_strict_gate(item)]
        if strict:
            best = strict[0]
            candidate = best["candidate"]
            video_id = candidate.get("id")
            if video_id is not None:
                USED_VIDEO_IDS.add(video_id)
            print(
                "[RETENTION5] early_visual_strict=true "
                f"id={video_id} "
                f"semantic_match={best['scores']['semantic_match']:.3f} "
                f"subject_visibility={best['scores']['subject_visibility']:.3f} "
                f"mobile_clarity={best['scores']['mobile_clarity']:.3f}"
            )
            return candidate["url"]

    print(
        "[RETENTION5] early_visual_strict=false "
        "fallback=legacy_pexels"
    )
    return fetch_pexels_video(original_query)


'''
if "def fetch_early_retention_pexels_video(scene):" not in hook_visual_text:
    if hook_visual_text.count(print_marker) != 1:
        raise RuntimeError("early retention visual marker mismatch")
    hook_visual_text = hook_visual_text.replace(
        print_marker,
        early_visual_function + print_marker,
        1,
    )
hook_visual_path.write_text(hook_visual_text, encoding="utf-8")


# ============================================================
# Video engine: pass Hook context to TTS + strict metadata scene 2
# ============================================================
video_path = Path("video/video_engine.py")
video_text = video_path.read_text(encoding="utf-8")

video_text = _replace_once(
    video_text,
    "import os\nimport subprocess\n",
    "import inspect\nimport os\nimport subprocess\n",
    "video engine inspect import",
)

old_tts_start = '''    # ========================================================
    # 1. TTS
    # ========================================================

    print(
        "🎙️ TTS 생성 시작..."
    )

    create_voice(
        text,
        audio_path,
    )
'''
new_tts_start = '''    # ========================================================
    # 1. TTS
    # ========================================================

    hook_tts_mode = (
        idx == 0
        and bool(
            item.get(
                "hook_experiment",
                {},
            ).get(
                "selected",
                False,
            )
        )
        and str(
            os.environ.get(
                "ENABLE_HOOK_EXPERIMENT",
                "0",
            )
        ).strip().lower()
        in {"1", "true", "yes", "on"}
    )

    print(
        "🎙️ TTS 생성 시작..."
    )

    try:
        voice_params = inspect.signature(create_voice).parameters
    except (TypeError, ValueError):
        voice_params = {}

    if "hook_mode" in voice_params:
        create_voice(
            text,
            audio_path,
            hook_mode=hook_tts_mode,
        )
    else:
        create_voice(
            text,
            audio_path,
        )
'''
video_text = _replace_once(
    video_text,
    old_tts_start,
    new_tts_start,
    "video engine Hook TTS context",
)

old_visual_else = '''        else:

            video_url = (
                fetch_pexels_video(
                    keyword
                )
            )
'''
new_visual_else = '''        elif idx == 1:

            try:

                from video.hook_visual import (
                    fetch_early_retention_pexels_video,
                )

                video_url = (
                    fetch_early_retention_pexels_video(
                        item
                    )
                )

            except Exception as e:

                print(
                    "⚠️ First-5s strict visual selector 실패, "
                    "기존 Pexels 경로로 fallback: "
                    f"{e}"
                )

                video_url = (
                    fetch_pexels_video(
                        keyword
                    )
                )

        else:

            video_url = (
                fetch_pexels_video(
                    keyword
                )
            )
'''
video_text = _replace_once(
    video_text,
    old_visual_else,
    new_visual_else,
    "video engine first-five visual path",
)
video_path.write_text(video_text, encoding="utf-8")

print(
    "✅ First-5s retention + Edge TTS humanization hotfix applied "
    "(existing quality/dominance thresholds unchanged)"
)
