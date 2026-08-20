from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label} marker count mismatch: {count}")
    return text.replace(marker, replacement, 1)


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    marker = '''    return f"""
[EXECUTION CONTEXT]

이번 탐색의 넓은 분야:
{category}
'''

    replacement = '''    run_scope = os.environ.get(
        "SHORTS_CANDIDATE_SCOPE",
        "",
    ).strip().lower()

    scope_context = ""
    if run_scope == "aviation":
        scope_context = """
[THIS RUN ONLY - AVIATION EXPLORATION CONTEXT]

이번 자동 탐색은 비행기/항공 범위 안에서만 수행하라.
특정 세부 소재를 미리 정하지 말고, 서로 실질적으로 다른 후보를 최소 10개 먼저 탐색한 뒤 기존 Candidate Explorer의 Hard Gate, scoring, shortlist, final sanity 규칙으로 경쟁시켜라.

탐색 방향 예시:
- 여객기의 숨겨진 기능
- 기내에서 사람들이 자주 궁금해하는 것
- 비행 중 일어나는 현상
- 조종석/객실의 특이한 설계
- 비행기 안전장치
- 공항/활주로의 숨겨진 시스템
- 사람들이 흔히 잘못 알고 있는 항공 상식
- 비행기를 타면서 한 번쯤 궁금했을 법한 질문

위 항목은 방향 예시일 뿐 특정 소재를 hard-code한 목록이 아니다.

후보 비교에서는 기존 점수와 gate를 변경하지 않은 채 다음 특성이 강한 후보를 우선 탐색하라:
- 대중적 호기심과 강한 curiosity gap
- 첫 1~3초 안에 즉시 이해 가능한 Hook 가능성
- 정답을 초반에 전부 공개하지 않고 payoff까지 retention을 만들 수 있음
- Pexels/Pixabay 무료 영상으로 의미가 맞는 시각 자료를 확보할 가능성이 높음
- 핵심 사실을 신뢰할 수 있는 자료로 검증 가능함

너무 전문적인 항공공학 설명이나 화면으로 표현하기 어려운 소재는 피하라.
흔하게 소비된 소재도 답이 너무 뻔하지 않고 강한 Hook/Payoff를 만들 수 있다면 허용한다.
기존 novelty/중복 회피 기준은 그대로 적용한다.
"""

    return f"""
[EXECUTION CONTEXT]
{scope_context}

이번 탐색의 넓은 분야:
{category}
'''

    text = replace_once(text, marker, replacement, "aviation execution context")
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ aviation candidate run context hotfix applied")


if __name__ == "__main__":
    main()
