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
