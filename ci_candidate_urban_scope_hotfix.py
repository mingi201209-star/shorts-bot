from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")

AUTO_SCOPE = """[AUTOMATIC TOPIC SCOPE]\n\nSHORTS_TOPIC이 비어 있는 자동 탐색 모드에서는 Candidate를 반드시 다음 범위 안에서만 탐색하라.\n\n- 도시\n- 건축\n- 초고층 건물\n- 도시 인프라\n- 도로, 교량, 터널\n- 지하 공간\n- 도시 설계\n- 건축에 숨겨진 기능\n\n이 범위 밖의 소재는 Candidate로 만들거나 Winner/Runner-up으로 선택하지 마라.\n특정 주제를 hard-code하지 말고 이 범위 안에서 서로 실질적으로 다른 여러 후보를 탐색한 뒤 기존 Hard Gate, Shortlist, Micro Narrative, Final Sanity 및 novelty/중복 기준으로 Winner를 선택하라.\n"""


def patch_candidate_explorer():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    marker = '''    return f"""\n[EXECUTION CONTEXT]\n\n이번 탐색의 넓은 분야:\n{category}\n'''

    replacement = '''    return f"""\n[EXECUTION CONTEXT]\n\n{AUTO_SCOPE}\n\n이번 탐색의 넓은 분야:\n{category}\n'''

    if replacement in text:
        return

    count = text.count(marker)
    if count != 1:
        raise RuntimeError(
            f"automatic scope marker count mismatch: {count}"
        )

    text = text.replace(marker, replacement, 1)
    EXPLORER_PATH.write_text(text, encoding="utf-8")


def main():
    patch_candidate_explorer()
    print("✅ automatic candidate urban scope hotfix applied")


if __name__ == "__main__":
    main()
