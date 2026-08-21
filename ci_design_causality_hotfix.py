from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
if "[DESIGN CAUSALITY — PREFERRED]" not in text:
    text = text.replace(
        "[CURIOSITY RETENTION — REQUIRED]\n",
        "[DESIGN CAUSALITY — PREFERRED]\n"
        "구체적인 설계/구조/기능을 설명하는 주제라면 장점을 나열하기보다 '왜 이렇게 만들었는가'가 이해되도록 인과적으로 설명한다.\n"
        "가능하면 PROBLEM → CONSTRAINT → DESIGN CHOICE → MECHANISM → RESULT 순서를 우선한다. 각 문장은 앞 문장의 원인/제약/결과와 자연스럽게 이어져야 한다.\n"
        "'A에도 도움이 되고 B에도 좋고 C 역할도 한다' 식 feature list를 만들지 않는다. 핵심 설계 필요성과 작동 원리를 먼저 설명한다.\n"
        "단, Candidate/Fact verification에 없는 인과관계를 추측해 만들지 않는다. 검증된 인과가 부족하면 사실 안전성과 명확성을 우선한다.\n\n"
        "[CURIOSITY RETENTION — REQUIRED]\n",
        1,
    )

text = append_once(
    text,
    "DESIGN_CAUSALITY_HELPER",
    r'''
# DESIGN_CAUSALITY_HELPER
_DESIGN_CAUSAL_CONNECTORS = (
    "때문", "그래서", "따라서", "이 때문에", "그 결과", "결과적으로",
    "압력", "부담", "제약", "문제", "설계", "구조", "작동", "조절",
)
_DESIGN_FEATURE_LIST_PATTERNS = (
    "도움이 된다", "도움이 됩니다", "좋습니다", "좋다",
    "역할을 한다", "역할을 합니다", "효과가 있다", "효과가 있습니다",
)


def design_causality_preference_score(scenes):
    """Small deterministic preference signal; not a new quality threshold."""
    texts = [
        str(scene.get("text", "")).strip()
        for scene in (scenes or [])
        if isinstance(scene, dict) and str(scene.get("text", "")).strip()
    ]
    joined = " ".join(texts)
    causal_hits = sum(1 for marker in _DESIGN_CAUSAL_CONNECTORS if marker in joined)
    list_hits = sum(1 for marker in _DESIGN_FEATURE_LIST_PATTERNS if marker in joined)
    # Reward explicit causal continuity; penalize repeated benefit-list phrasing.
    return causal_hits * 2 - list_hits * 3
''',
)
path.write_text(text, encoding="utf-8")


path = Path("quality/explanation_judge.py")
text = path.read_text(encoding="utf-8")
if "DESIGN CAUSALITY" not in text:
    text = text.replace(
        "CURIOSITY RETENTION / INFORMATION DENSITY",
        "DESIGN CAUSALITY / CURIOSITY RETENTION / INFORMATION DENSITY",
        1,
    )
    text += '''\n\n# DESIGN CAUSALITY: for concrete design/structure/function topics, prefer verified\n# problem -> constraint -> design choice -> mechanism -> result explanations over\n# a flat list of benefits. Do not invent causal links absent from the Candidate/facts.\n'''
path.write_text(text, encoding="utf-8")


path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
if "[DESIGN CAUSALITY 수정]" not in text:
    text = text.replace(
        "[CURIOSITY RETENTION 수정]\n",
        "[DESIGN CAUSALITY 수정]\n"
        "- 구체적 설계/구조/기능 주제에서 장점 목록처럼 보이면 검증된 사실 범위 안에서 문제 → 제약 → 설계 선택 → 작동 원리 → 결과의 인과 흐름으로 재구성한다.\n"
        "- 'A에도 좋고 B에도 좋다'는 식의 병렬 장점 나열보다 '왜 그렇게 설계해야 했는가'를 우선한다.\n"
        "- Candidate/Fact에 없는 인과관계는 추가하지 않는다.\n"
        "[CURIOSITY RETENTION 수정]\n",
        1,
    )
path.write_text(text, encoding="utf-8")

print("✅ Design causality preference applied")
