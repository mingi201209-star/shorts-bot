"""Shared deterministic Korean declarative ending normalization for Script V2.

The rules are corpus-driven and intentionally narrow. Only terminal declarative
endings already represented by production/regression contracts are normalized.
Questions, quoted/code-like text, and already-formal narration are left intact.
"""
from __future__ import annotations

import re
from typing import Any

FORMAL_ENDING_CORPUS_VERSION = "v1"

# Keep one production table for locked and unlocked narration. These classes are
# backed by current/historical production regression contracts; this is not a
# fuzzy Korean grammar engine.
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
    (r"어두워진다(?=[.!…]*$)", "어두워집니다"),
    (r"되었다(?=[.!…]*$)", "되었습니다"),
    (r"사실(?=[.!…]*$)", "사실입니다"),
)

_FORMAL_ENDING_RE = re.compile(
    r"(?:습니다|습니까|입니다|합니다|됩니다|줍니다|듭니다|납니다|집니다|었습니다|였습니다)[.!?…]*$"
)
_QUOTE_OR_CODE_CHARS = ("'", '"', "`", "‘", "’", "“", "”")


def formalize_declarative_sentence(text: Any) -> str:
    """Normalize one terminal declarative sentence, preserving risky text verbatim."""
    value = str(text or "")
    stripped = value.strip()
    if not stripped:
        return stripped
    if "?" in stripped:
        return stripped
    if any(mark in stripped for mark in _QUOTE_OR_CODE_CHARS):
        return stripped
    if _FORMAL_ENDING_RE.search(stripped):
        return stripped
    if stripped.endswith(("]", "}", ">")):
        return stripped
    for pattern, replacement in _DECLARATIVE_ENDING_REPAIRS:
        converted, count = re.subn(pattern, replacement, stripped)
        if count:
            return converted
    return stripped


def formalize_declarative_text(text: Any) -> str:
    """Apply the terminal contract sentence-by-sentence outside quoted/code text."""
    value = str(text or "").strip()
    if not value:
        return value
    # V1 deliberately fails closed for any quoted/code-like narration rather than
    # attempting a quote-aware Korean parser and accidentally mutating a quotation.
    if any(mark in value for mark in _QUOTE_OR_CODE_CHARS):
        return value
    parts = re.split(r"(?<=[.!?…])(\s*)", value)
    for index in range(0, len(parts), 2):
        if parts[index]:
            parts[index] = formalize_declarative_sentence(parts[index])
    return "".join(parts)


def declarative_repairs():
    return _DECLARATIVE_ENDING_REPAIRS
