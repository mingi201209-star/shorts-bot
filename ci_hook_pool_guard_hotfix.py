from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        "- 안정적으로 범위 안에 들어오도록 13~15자를 목표로 쓴다.",
        "- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다.",
    ),
    (
        "길이 탈락이면 13~15자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.",
        "길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.",
    ),
    (
        '''    best = None
    rejection_feedback = None
''',
        '''    best = None
    pool_ready = False
    rejection_feedback = None
''',
    ),
    (
        '''        if (
            diagnostics.get("scoring_pool_count", 0) >= HOOK_CANDIDATE_COUNT
            and round_best
        ):
            break
''',
        '''        if (
            diagnostics.get("scoring_pool_count", 0) >= HOOK_CANDIDATE_COUNT
            and round_best
        ):
            pool_ready = True
            break
''',
    ),
    (
        "    if best is None:\n",
        "    if best is None or not pool_ready:\n",
    ),
]

for old, new in replacements:
    if new in text:
        continue
    if text.count(old) != 1:
        raise RuntimeError(
            "Hook scoring-pool guard marker mismatch: "
            f"{old[:60]!r} count={text.count(old)}"
        )
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("✅ Hook 15-16 target + five-candidate scoring-pool guard applied")
