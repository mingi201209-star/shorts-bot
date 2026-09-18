"""Regression test: Explorer's REGENERATE placeholder-reason text was
rewritten (2026-09-18) because the model kept echoing the JSON schema's
literal example reason ("재탐색이 필요한 구체적인 이유") verbatim as its
actual REGENERATE reason, instead of writing a real one -- visible across
runs 613-616's logs. content/candidate_explorer.py's schema now shows an
explicit anti-copy instruction and a worked example instead of a bare
placeholder phrase.

This verifies content/candidate_explorer/__init__.py's
_is_placeholder_regenerate() (the safety net that forces one retry when
this happens) still catches:
  1. The original placeholder phrase (in case older cached prompts or
     partial echoes still produce it).
  2. The new placeholder template's distinguishing text, in case the
     model echoes IT verbatim instead.
  3. A real, specific reason is NOT flagged as a placeholder.
"""

from content.candidate_explorer import _is_placeholder_regenerate


def test_old_placeholder_detected():
    result = {"status": "REGENERATE", "reason": "재탐색이 필요한 구체적인 이유"}
    assert _is_placeholder_regenerate(result)


def test_new_placeholder_template_detected():
    result = {
        "status": "REGENERATE",
        "reason": (
            "<여기에 이번 탐색에서 구체적으로 무엇이 부족했는지 실제로 작성. "
            "아래는 형식 예시일 뿐 그대로 복사하지 말 것: '수도관 부식 후보의 "
            "Reveal이 일반 상식 수준(녹이 슨다)에서 끝나 예상 밖의 메커니즘이 "
            "없었음'>"
        ),
    }
    assert _is_placeholder_regenerate(result)


def test_real_reason_not_flagged():
    result = {
        "status": "REGENERATE",
        "reason": "제트 엔진 노즐 후보의 Reveal이 소음 감소라는 일반 상식 수준에서 끝나 예상 밖의 메커니즘이 없었음",
    }
    assert not _is_placeholder_regenerate(result)


if __name__ == "__main__":
    test_old_placeholder_detected()
    print("✓ test_old_placeholder_detected")

    test_new_placeholder_template_detected()
    print("✓ test_new_placeholder_template_detected")

    test_real_reason_not_flagged()
    print("✓ test_real_reason_not_flagged")

    print("\n✅ All tests passed")
