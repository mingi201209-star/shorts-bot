from pathlib import Path
import re


def set_regex(path, pattern, replacement, label):
    source = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        pattern,
        replacement,
        source,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError(
            f"{label} 패치 대상이 정확히 1개가 아닙니다. (count={count})"
        )
    path.write_text(updated, encoding="utf-8")


set_regex(
    Path("main.py"),
    r"^MAX_TOPIC_REGENERATIONS\s*=\s*\d+\s*$",
    "MAX_TOPIC_REGENERATIONS = 6",
    "main.py MAX_TOPIC_REGENERATIONS",
)
set_regex(
    Path("main.py"),
    r"^NOVELTY_HARD_REGENERATE_SCORE\s*=\s*[0-9.]+\s*$",
    "NOVELTY_HARD_REGENERATE_SCORE = 4.0",
    "main.py NOVELTY_HARD_REGENERATE_SCORE",
)
set_regex(
    Path("config.py"),
    r"^MAX_SCRIPT_ATTEMPTS\s*=\s*\d+\s*$",
    "MAX_SCRIPT_ATTEMPTS = 5",
    "config.py MAX_SCRIPT_ATTEMPTS",
)

explorer_path = Path("content/candidate_explorer.py")
explorer_source = explorer_path.read_text(encoding="utf-8")
explorer_source, count = re.subn(
    r"temperature\s*=\s*0\.[0-9]+,",
    "temperature=0.5,",
    explorer_source,
    count=1,
)
if count != 1:
    raise RuntimeError(
        "candidate_explorer.py temperature 패치 대상이 정확히 1개가 아닙니다. "
        f"(count={count})"
    )

specificity_marker = """============================================================
3. SEARCH FOR DISTINCT IDEAS
============================================================"""

specificity_block = """
============================================================
2.5 SPECIFICITY LOCK — BROAD THEME 금지
============================================================

Candidate는 반드시 하나의 구체적인 실제 대상이나 관찰 가능한 현상에 고정되어야 한다.

다음처럼 카테고리명·상위개념·교과서 단원처럼 들리는 topic은 Winner/Runner-up으로 선택하지 마라.

금지 예:
- 특이한 지리적 장소
- 동물의 특이한 생존 전략
- 사라진 고대의 물건 만들기 기술
- 산업 현장에서의 예측 유지보수 기술
- 중세 시대의 성곽 건축
- 스마트폰의 구조
- 자연의 소리
- 자동차 안전 설계

이런 표현은 탐색 방향일 뿐 Story Angle이 아니다.

반드시 아래 형태 중 하나처럼 더 좁혀라.

- 특정 대상 + 특정 이상한 구조 + 왜 그런가
- 특정 동물 + 특정 행동 + 어떻게 가능한가
- 특정 건축물/기술 + 특정 세부 + 숨은 목적
- 특정 물건 + 특정 설계 특징 + 예상 밖의 이유
- 특정 사건/관행 + 특정 결과 + 연결 메커니즘

좋은 예의 형태:
- 성문 앞 진입로가 일부러 꺾여 있던 이유
- 사막개미가 랜드마크 없이 둥지로 돌아오는 방법
- 로마 도로 아래 자갈층을 여러 겹 쌓은 이유
- 비행기 창문 모서리가 둥근 이유

[MANDATORY SPECIFICITY TEST]

Winner를 확정하기 직전에 다음을 확인하라.

1. topic만 읽어도 실제로 무엇을 보여줄지 떠오르는가?
2. core_question이 하나의 구체적 대상/구조/행동을 직접 가리키는가?
3. reveal을 한 문장으로 말했을 때 실제 mechanism이 들어가는가?
4. "특정", "어떤", "여러", "다양한", "기술", "전략", "장소", "구조" 같은 추상어를 빼도 대상이 남는가?

하나라도 NO라면 SELECTED하지 말고 더 구체적인 후보를 탐색하라.

특히 다음 질문 패턴은 그대로 출력하지 마라.
- 어떻게 특정 동물들은 극한 환경에서 살아남을 수 있을까?
- 왜 이 장소가 지리적으로 평범해 보이지만 실제로는 독특한 현상을 가지고 있을까?
- 어떻게 기계의 고장을 예측하고 예방할 수 있을까?
- 왜 고대의 물건 만들기 기술은 현대에 잊혀졌는가?

이런 질문은 반드시 실제 대상과 단일 mechanism이 드러나는 질문으로 좁혀라.

"""

if "2.5 SPECIFICITY LOCK" not in explorer_source:
    if explorer_source.count(specificity_marker) != 1:
        raise RuntimeError(
            "candidate_explorer.py specificity 삽입 위치를 찾지 못했습니다."
        )
    explorer_source = explorer_source.replace(
        specificity_marker,
        specificity_block + specificity_marker,
        1,
    )

explorer_path.write_text(explorer_source, encoding="utf-8")

set_regex(
    Path("quality/consensus.py"),
    r"^GOOD_ENOUGH_SCORE\s*=\s*[0-9.]+\s*$",
    "GOOD_ENOUGH_SCORE = 6.7",
    "consensus.py GOOD_ENOUGH_SCORE",
)

consensus_path = Path("quality/consensus.py")
consensus_source = consensus_path.read_text(encoding="utf-8")
consensus_source, count = re.subn(
    r'(^\s*"hook"\s*:\s*)[0-9.]+(,\s*$)',
    r'\g<1>6.0\2',
    consensus_source,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    raise RuntimeError(
        "consensus.py hook floor 패치 대상이 정확히 1개가 아닙니다. "
        f"(count={count})"
    )
consensus_path.write_text(consensus_source, encoding="utf-8")

script_path = Path("content/script_generator.py")
script_source = script_path.read_text(encoding="utf-8")

narration_block = """
[NARRATION TONE]
모든 Scene의 text는 시청자에게 설명하는 자연스러운 한국어 존댓말로 쓴다.
반말/해라체/문어체 종결인 "~다", "~이다", "~했다", "~한다"는 사용하지 않는다.
"~습니다/~입니다"만 기계적으로 반복하지 말고
"~는데요", "~죠", "~까요?", "~해요"를 문맥에 맞게 섞는다.
과한 감탄, 호들갑, 억지 친근함은 피한다.
짧고 또렷한 다큐멘터리 내레이션처럼 말한다.
문장부호를 자연스럽게 사용해 TTS가 쉬어 읽을 지점을 만든다.
"""

if "[NARRATION TONE]" not in script_source:
    fact_marker = "\n[FACT]\n"
    if script_source.count(fact_marker) != 1:
        raise RuntimeError(
            "script_generator.py NARRATION TONE 삽입 위치를 찾지 못했습니다."
        )
    script_source = script_source.replace(
        fact_marker,
        "\n" + narration_block + "\n[FACT]\n",
        1,
    )

if "존댓말 종결이 아님" not in script_source:
    visual_marker = "        if len(visual_goal) < 8:\n"
    if script_source.count(visual_marker) != 1:
        raise RuntimeError(
            "script_generator.py 존댓말 검사 삽입 위치를 찾지 못했습니다."
        )

    polite_check = "\n".join([
        '        polite_ending = text.rstrip(" .!?…~")',
        "        if not (",
        '            polite_ending.endswith("요")',
        '            or polite_ending.endswith("죠")',
        '            or polite_ending.endswith("니다")',
        '            or polite_ending.endswith("십시오")',
        "        ):",
        "            return False, (",
        '                f"{idx + 1}번 장면 대사가 존댓말 종결이 아님: {text}"',
        "            )",
        "",
        "",
    ])
    script_source = script_source.replace(
        visual_marker,
        polite_check + visual_marker,
        1,
    )

if "meaningful_keyword_words" not in script_source:
    abstract_marker = "        if normalized in BAD_VISUAL_KEYWORDS:\n"
    if script_source.count(abstract_marker) != 1:
        raise RuntimeError(
            "script_generator.py concrete keyword 검사 삽입 위치를 찾지 못했습니다."
        )

    concrete_keyword_check = "\n".join([
        "        generic_keyword_words = {",
        '            "science", "technology", "nature", "interesting",',
        '            "amazing", "documentary", "background", "concept",',
        '            "future", "innovation", "beautiful", "cool",',
        '            "information", "education", "abstract",',
        "        }",
        "        meaningful_keyword_words = [",
        "            word",
        "            for word in words",
        "            if word not in generic_keyword_words",
        "        ]",
        "        if len(meaningful_keyword_words) < 2:",
        "            return False, (",
        '                f"{idx + 1}번 검색어가 구체적 시각 대상 부족: {keyword}"',
        "            )",
        "",
        "",
    ])
    script_source = script_source.replace(
        abstract_marker,
        concrete_keyword_check + abstract_marker,
        1,
    )

if "[RETRY FEEDBACK]" not in script_source:
    content_lock_marker = "[CONTENT LOCK]\n"
    if script_source.count(content_lock_marker) != 1:
        raise RuntimeError(
            "script_generator.py retry feedback 삽입 위치를 찾지 못했습니다."
        )

    retry_feedback = """[RETRY FEEDBACK]
직전 생성 실패 이유: {last_error or "없음"}
재시도 중이라면 위 오류를 반드시 고친다.
특히 Scene 수와 keyword의 구체성을 같은 오류로 반복하지 마라.

"""
    script_source = script_source.replace(
        content_lock_marker,
        retry_feedback + content_lock_marker,
        1,
    )

script_path.write_text(script_source, encoding="utf-8")

rewrite_path = Path("quality/rewrite_engine.py")
rewrite_source = rewrite_path.read_text(encoding="utf-8")

if "모든 scene text는 자연스러운 한국어 존댓말" not in rewrite_source:
    rewrite_marker = "수정된 전체 JSON 객체만 출력한다."
    if rewrite_source.count(rewrite_marker) != 1:
        raise RuntimeError(
            "rewrite_engine.py 존댓말 규칙 삽입 위치를 찾지 못했습니다."
        )

    rewrite_tone = """- 모든 scene text는 자연스러운 한국어 존댓말을 유지한다.
- 반말/해라체 종결인 "~다", "~이다", "~했다", "~한다"로 바꾸지 않는다.
- "~습니다/~입니다"만 반복하지 말고 "~는데요", "~죠", "~까요?", "~해요"를 자연스럽게 섞는다.
- 과한 유튜버식 감탄보다 차분하고 또렷한 다큐멘터리 내레이션을 우선한다.

"""
    rewrite_source = rewrite_source.replace(
        rewrite_marker,
        rewrite_tone + rewrite_marker,
        1,
    )

rewrite_path.write_text(rewrite_source, encoding="utf-8")

main_path = Path("main.py")
main_source = main_path.read_text(encoding="utf-8")
review_pattern = re.compile(
    r'(if\s*\(\s*review_count\s*>=\s*MAX_REVIEW_ROUNDS\s*\):.*?'
    r'"status":\s*)"HOLD"(,.*?"reason":\s*"Review 최대 횟수 초과",\s*\})',
    flags=re.DOTALL,
)
main_source, count = review_pattern.subn(
    r'\1"REGENERATE_TOPIC"\2',
    main_source,
    count=1,
)
if count != 1:
    raise RuntimeError(
        "main.py Review limit fallback 패치 대상이 정확히 1개가 아닙니다. "
        f"(count={count})"
    )

script_call_marker = """            script_data = (
                generate_script(
                    topic_info,
                    winner,
                )
            )
"""
script_call_replacement = """            try:
                script_data = (
                    generate_script(
                        topic_info,
                        winner,
                    )
                )
            except RuntimeError as exc:
                message = str(exc)
                if "Script Generator가 유효한 대본 생성에 실패했습니다" not in message:
                    raise

                if current_topic not in rejected_topics:
                    rejected_topics.append(current_topic)

                print("")
                print("=" * 64)
                print("♻️ SCRIPT GENERATION FAILED → CANDIDATE REGENERATION")
                print("=" * 64)
                print("폐기 소재:", current_topic)
                print("이유:", message)
                print_budget_status()

                if topic_attempt < total_topic_attempts:
                    print("")
                    print("➡️ Candidate Explorer 재탐색")
                    continue

                raise RuntimeError(
                    "Script 생성 가능한 Winner를 확보하지 못했습니다. "
                    f"마지막 이유: {message}"
                )
"""
if main_source.count(script_call_marker) != 1:
    raise RuntimeError(
        "main.py Script Generator fallback 패치 대상이 정확히 1개가 아닙니다. "
        f"(count={main_source.count(script_call_marker)})"
    )
main_source = main_source.replace(
    script_call_marker,
    script_call_replacement,
    1,
)

main_path.write_text(main_source, encoding="utf-8")

print(
    "✅ Runtime production + candidate specificity + polite narration + visual retry + "
    "review fallback + script fallback hotfix applied"
)
