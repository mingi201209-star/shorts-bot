from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} marker mismatch count={text.count(old)}")
    return text.replace(old, new, 1)


# ============================================================
# Hook generation stability
# Keep deterministic validator 12..16, scoring floors, threshold,
# and bounded two-attempt policy unchanged. Only center generation
# guidance away from the upper boundary and teach retry how to
# repair overlong output without truncation.
# ============================================================
path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    "- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다.",
    "- 상한과 하한 모두에 여유를 두도록 13~15자를 목표로 쓴다.",
    "hook centered length guidance",
)
text = replace_once(
    text,
    "- 숫자 글자 수만 맞추려 하지 말고 text를 5~6개의 짧은 한국어 어절로 구성한다.",
    "- 숫자 글자 수만 맞추려 하지 말고 text를 4~5개의 짧은 한국어 어절로 구성한다.",
    "hook eojeol guidance",
)
text = replace_once(
    text,
    '- "드론이 균열을 찾아요"처럼 대상+동작만 있는 3~4어절 문장은 너무 짧으므로 출력하지 않는다.',
    '- 3어절 이하로 의미가 빈약한 문장은 피하되, 4~5어절 안에서 대상과 관찰 가능한 결과를 간결하게 말한다.',
    "hook concise structure guidance",
)
text = replace_once(
    text,
    "길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.",
    "길이 탈락이면 13~15자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.",
    "hook retry centered length guidance",
)
text = replace_once(
    text,
    "too_short가 발생했다면 기존 짧은 문장에 구체적인 부위/구조/관찰 단서를 1~2어절 추가해 5~6어절 문장으로 만든다.",
    "too_short가 발생했다면 핵심 대상을 유지하면서 관찰 단서를 짧게 보태 13~15자로 만든다.\ntoo_long이 발생했다면 핵심 대상과 이상현상/결과는 유지하되 수식어와 중복 표현을 제거해 13~15자로 다시 쓴다. 문장을 잘라내거나 어미를 훼손하지 않는다.",
    "hook retry too-long repair guidance",
)

path.write_text(text, encoding="utf-8")


# ============================================================
# Quality final-decision contract
# The production committee currently runs hook/novelty/fact/visual.
# GOOD_ENOUGH_FLOORS also has an optional explanation floor, but no
# explanation judge is present in the current pool. Do not convert an
# absent, unjudged domain into an artificial zero. If that domain is
# present in a future pool, its floor remains enforced unchanged.
# ============================================================
path = Path("quality/consensus.py")
text = path.read_text(encoding="utf-8")
old = '''def meets_good_enough_floors(summaries):
    for judge_type, minimum in GOOD_ENOUGH_FLOORS.items():
        score = safe_float(summaries.get(judge_type, {}).get("score", 0.0))
        if score < minimum:
            return False
    return True
'''
new = '''def meets_good_enough_floors(summaries):
    for judge_type, minimum in GOOD_ENOUGH_FLOORS.items():
        if judge_type not in summaries:
            continue
        score = safe_float(summaries.get(judge_type, {}).get("score", 0.0))
        if score < minimum:
            return False
    return True
'''
text = replace_once(text, old, new, "good-enough present-domain contract")
path.write_text(text, encoding="utf-8")

print("✅ Throughput recovery hotfix applied: centered Hook generation + present-domain Good Enough floors")
