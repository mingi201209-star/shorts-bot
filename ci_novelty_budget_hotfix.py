from pathlib import Path


path = Path("main.py")
text = path.read_text(encoding="utf-8")

needle = '''        pool[\n            judge_type\n        ] = [\n            result\n        ]\n\n    return pool\n'''

replacement = '''        pool[\n            judge_type\n        ] = [\n            result\n        ]\n\n        # Hard novelty failure means the candidate itself is weak.\n        # Stop before FACT/VISUAL judges and before any rewrite/review.\n        if judge_type == "novelty":\n\n            try:\n                novelty_score = float(\n                    result.get(\n                        "score",\n                        0.0,\n                    )\n                )\n            except Exception:\n                novelty_score = 10.0\n\n            if (\n                novelty_score\n                < NOVELTY_HARD_REGENERATE_SCORE\n            ):\n\n                print("")\n                print(\n                    "⏭️ Novelty 조기 차단: "\n                    f"{novelty_score:.2f} < "\n                    f"{NOVELTY_HARD_REGENERATE_SCORE:.2f}"\n                )\n                print(\n                    "   FACT/VISUAL Judge를 생략하고 "\n                    "Candidate Explorer로 반환합니다."\n                )\n\n                break\n\n    return pool\n'''

if replacement in text:
    print("early novelty hotfix already applied")
elif needle not in text:
    raise RuntimeError("run_initial_judges patch target not found")
else:
    path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    print("early novelty hotfix applied")


# Production counterexample: run 32538176597 selected a candidate that was
# specific enough for Candidate Gate but predictably scored Novelty 5/10 before
# and after rewrite. Align the pre-script gate with the downstream novelty
# contract without changing any judge threshold or adding another API call.
gate_path = Path("content/candidate_gate.py")
gate_text = gate_path.read_text(encoding="utf-8")

core_marker = '''"질문과 실제 답이 얼마나 예상 밖인가"\n\n이다.\n'''
core_insert = '''"질문과 실제 답이 얼마나 예상 밖인가"\n\n이다.\n\n이 Gate는 후단 Novelty Judge와 같은 방향으로 판단해야 한다.\n구체적인 사실이나 메커니즘이 있다는 이유만으로 PASS하지 마라.\n질문을 읽은 일반 시청자가 Reveal의 방향을 쉽게 예상할 수 있고,\nScript 표현을 바꾸는 것만으로 새로움이 생기지 않는다면 REGENERATE한다.\n'''

payoff_marker = '''라는 새로운 이해나 재해석이\n거의 생기지 않는다면 약하다.\n'''
payoff_insert = '''라는 새로운 이해나 재해석이\n거의 생기지 않는다면 약하다.\n\n특히 질문 자체가 답의 방향을 거의 말해주거나,\nReveal이 상식적인 물리 현상·일상적 인과를 단순 확인하는 수준이면\n구체적인 용어가 있어도 REGENERATE한다.\n\n예: "비행 중 기내에서 중력이 느껴지는 방식이 어떻게 다른가"처럼\n익숙한 현상의 단순 변화만 묻고 Reveal도 예상 가능한 변화 설명에 머문다면\n후단 Rewrite로 해결할 문제가 아니라 Candidate 자체가 약한 것이다.\n\n반대로 익숙한 비행기 소재라도 예상과 반대되는 원인, 숨은 설계 제약,\n구체적인 메커니즘으로 기존 직관을 바꾸는 Reveal이 있으면 PASS할 수 있다.\n'''

ambiguity_marker = '''판단이 애매하다면\nPASS 쪽으로 판단한다.\n'''
ambiguity_insert = '''단, "구체적이지만 예상 가능한 Candidate"는 애매한 PASS로 처리하지 마라.\n이 경우 후단 Novelty Rewrite가 Candidate 선택 문제를 고칠 수 없으므로\nREGENERATE 쪽으로 판단한다.\n\n그 외의 판단이 애매하다면\nPASS 쪽으로 판단한다.\n'''

if "CANDIDATE_NOVELTY_PARITY_V1" in gate_text:
    print("candidate novelty parity already applied")
else:
    for marker, patched in (
        (core_marker, core_insert + "\nCANDIDATE_NOVELTY_PARITY_V1\n"),
        (payoff_marker, payoff_insert),
        (ambiguity_marker, ambiguity_insert),
    ):
        if marker not in gate_text:
            raise RuntimeError("candidate novelty parity patch target not found")
        gate_text = gate_text.replace(marker, patched, 1)

    gate_path.write_text(gate_text, encoding="utf-8")
    print("candidate novelty parity hotfix applied")
