"""Shared deterministic Korean Script speech-style normalization.

Declarative rules are corpus-driven and intentionally narrow. Only terminal
endings already represented by production/regression contracts are normalized.
Question handling remains a separate existing contract; quoted/code-like text
and already-formal narration are left intact.
"""
from __future__ import annotations

import re
from typing import Any

FORMAL_ENDING_CORPUS_VERSION = "v1"

_DECLARATIVE_ENDING_REPAIRS = (
    (r"줄여준다(?=[.!…]*$)", "줄여줍니다"),
    (r"감소시킨다(?=[.!…]*$)", "감소시킵니다"),
    (r"(줄|높|보)인다(?=[.!…]*$)", r"\1입니다"),
    (r"감소한다(?=[.!…]*$)", "감소합니다"),
    (r"발생한다(?=[.!…]*$)", "발생합니다"),
    (r"만든다(?=[.!…]*$)", "만듭니다"),
    (r"시킨다(?=[.!…]*$)", "시킵니다"),
    (r"돕는다(?=[.!…]*$)", "돕습니다"),
    (r"않는다(?=[.!…]*$)", "않습니다"),
    (r"않다(?=[.!…]*$)", "않습니다"),
    (r"한다(?=[.!…]*$)", "합니다"),
    (r"하다(?=[.!…]*$)", "합니다"),
    (r"된다(?=[.!…]*$)", "됩니다"),
    (r"설계다(?=[.!…]*$)", "설계입니다"),
    (r"이유다(?=[.!…]*$)", "이유입니다"),
    (r"구조다(?=[.!…]*$)", "구조입니다"),
    (r"위해서다(?=[.!…]*$)", "위해서입니다"),
    (r"이다(?=[.!…]*$)", "입니다"),
    (r"있다(?=[.!…]*$)", "있습니다"),
    (r"없다(?=[.!…]*$)", "없습니다"),
    (r"줄어든다(?=[.!…]*$)", "줄어듭니다"),
    (r"늘어난다(?=[.!…]*$)", "늘어납니다"),
    (r"약해진다(?=[.!…]*$)", "약해집니다"),
    (r"강해진다(?=[.!…]*$)", "강해집니다"),
    (r"달라진다(?=[.!…]*$)", "달라집니다"),
    (r"좋아진다(?=[.!…]*$)", "좋아집니다"),
    (r"향상된다(?=[.!…]*$)", "향상됩니다"),
    (r"궁금해진다(?=[.!…]*$)", "궁금해집니다"),
    (r"용이해진다(?=[.!…]*$)", "용이해집니다"),
    (r"가능해진다(?=[.!…]*$)", "가능해집니다"),
    (r"이루어진다(?=[.!…]*$)", "이루어집니다"),
    (r"알려진다(?=[.!…]*$)", "알려집니다"),
    (r"도와준다(?=[.!…]*$)", "도와줍니다"),
    (r"워진다(?=[.!…]*$)", "워집니다"),
    (r"되었다(?=[.!…]*$)", "되었습니다"),
    (r"사실(?=[.!…]*$)", "사실입니다"),
)

# Narrow narration-only conversion for terminal visual-attention requests.
# These forms are not made acceptable to the validator; they are rewritten
# before validation into an explanatory observation without inventing a
# mechanism/performance claim. Quoted dialogue remains protected below.
_NARRATION_ATTENTION_REPAIRS = (
    (
        re.compile(
            r"^(?P<object>.+?(?:을|를))\s*(?:한번\s*)?"
            r"(?:주목해\s*보세요|봐\s*보세요|봐\s*주세요|보세요)(?=[.!…]*$)"
        ),
        r"\g<object> 확인할 수 있습니다",
    ),
    (
        re.compile(
            r"^(?P<object>.+?(?:을|를))\s*"
            r"(?:주목|확인|관찰)\s*해\s*주세요(?=[.!…]*$)"
        ),
        r"\g<object> 확인할 수 있습니다",
    ),
)

# Existing production question contract. This is deliberately separate from
# declarative generalization so V1 does not invent a new question grammar path.
_QUESTION_ENDING_REPAIRS = (
    (r"있나요(?=[?…]*$)", "있습니까"),
)

_FORMAL_ENDING_RE = re.compile(
    r"(?:습니다|습니까|입니다|합니다|됩니다|줍니다|듭니다|납니다|집니다|었습니다|였습니다)[.!?…]*$"
)
_QUOTE_OR_CODE_CHARS = ("'", '"', "`", "‘", "’", "“", "”")


def _risky_literal_text(value: str) -> bool:
    return any(mark in value for mark in _QUOTE_OR_CODE_CHARS)


def formalize_existing_question_ending(text: Any) -> str:
    """Preserve only the already-approved production question repair contract."""
    value = str(text or "").strip()
    if not value or _risky_literal_text(value):
        return value
    for pattern, replacement in _QUESTION_ENDING_REPAIRS:
        converted, count = re.subn(pattern, replacement, value)
        if count:
            return converted
    return value


def _formalize_narration_attention_request(value: str) -> str:
    """Convert a narrow terminal visual-attention request into narration."""
    for pattern, replacement in _NARRATION_ATTENTION_REPAIRS:
        converted, count = pattern.subn(replacement, value)
        if count:
            punctuation = "." if value.endswith(".") else ""
            return converted.rstrip(".!…") + punctuation
    return value


def formalize_declarative_sentence(text: Any) -> str:
    """Normalize one terminal declarative sentence, preserving risky text verbatim."""
    stripped = str(text or "").strip()
    if not stripped:
        return stripped
    if "?" in stripped or _risky_literal_text(stripped):
        return stripped
    if _FORMAL_ENDING_RE.search(stripped):
        return stripped
    if stripped.endswith(("]", "}", ">")):
        return stripped

    attention_formalized = _formalize_narration_attention_request(stripped)
    if attention_formalized != stripped:
        return attention_formalized

    for pattern, replacement in _DECLARATIVE_ENDING_REPAIRS:
        converted, count = re.subn(pattern, replacement, stripped)
        if count:
            return converted
    return stripped


def formalize_declarative_text(text: Any) -> str:
    """Apply the declarative terminal contract independently to every sentence."""
    value = str(text or "").strip()
    if not value:
        return value
    if _risky_literal_text(value):
        return value
    parts = re.split(r"(?<=[.!?…])(\s*)", value)
    for index in range(0, len(parts), 2):
        if parts[index]:
            parts[index] = formalize_declarative_sentence(parts[index])
    return "".join(parts)


def formalize_script_text(text: Any) -> str:
    """Existing question contract followed by the shared declarative corpus."""
    value = formalize_existing_question_ending(text)
    return formalize_declarative_text(value)


def declarative_repairs():
    return _DECLARATIVE_ENDING_REPAIRS
