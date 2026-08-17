"""Mechanism-first wrapper for the legacy Shorts Script Generator.

Keeps the large legacy module untouched.  Normal generation still happens in
content/script_generator.py; this wrapper only adds the production lesson from
Short #1: the script must spend its explanation on HOW/WHY the core phenomenon
works, not merely say that it exists or matters.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_LEGACY_PATH = Path(__file__).resolve().parent.parent / "script_generator.py"
_SPEC = importlib.util.spec_from_file_location(
    "content._script_generator_legacy",
    _LEGACY_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load Script Generator: {_LEGACY_PATH}")

_LEGACY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_LEGACY)


_MECHANISM_REQUIREMENT = """

[MECHANISM / PRINCIPLE REQUIREMENT]
이 Shorts는 핵심 원리를 실제로 가르쳐야 한다.
단순히 '이 기술이 있었다', '효과가 있었다', '중요했다', '현대에 영향을 줬다'고 말하는 것만으로는 부족하다.

대본의 Explanation 구간에는 반드시 다음 흐름이 드러나야 한다.
1) 무엇이 실제로 일어나는가
2) 어떤 과정/구조/힘/상호작용 때문에 그렇게 되는가
3) 그 원인이 어떻게 결과로 이어지는가

가능하면 서로 이어지는 최소 2개 Scene을 핵심 메커니즘 설명에 사용한다.
배경 역사나 의미 설명보다 HOW/WHY 설명에 더 많은 시간을 배정한다.
시청자가 영상을 본 뒤 '그래서 정확히 어떻게 작동하는데?'라고 다시 물어야 한다면 대본은 실패다.

단, 구체성을 채우려고 Candidate에 없는 숫자, 고유명사, 연구 결과, 역사적 기원, 인과관계를 발명하지 않는다.
Candidate가 허용하는 사실 범위 안에서만 원리를 설명하고, 검증이 필요한 구체적 주장은 기존 Fact Judge가 확인할 수 있게 명확하게 표현한다.
""".strip()


def _with_mechanism_requirement(candidate):
    enriched = dict(candidate or {})
    existing = str(enriched.get("selection_reason", "")).strip()
    if "[MECHANISM / PRINCIPLE REQUIREMENT]" not in existing:
        enriched["selection_reason"] = (
            (existing + "\n\n") if existing else ""
        ) + _MECHANISM_REQUIREMENT
    return enriched


def generate_script(topic_info, candidate):
    return _LEGACY.generate_script(
        topic_info,
        _with_mechanism_requirement(candidate),
    )


# Compatibility for code/tests importing helpers or model settings from the
# original module.
MODEL = _LEGACY.MODEL
extract_json = _LEGACY.extract_json
require_nonempty_string = _LEGACY.require_nonempty_string
validate_candidate = _LEGACY.validate_candidate
validate_hook = _LEGACY.validate_hook
validate_scenes = _LEGACY.validate_scenes
validate_keyword_variety = _LEGACY.validate_keyword_variety
validate_script = _LEGACY.validate_script
build_candidate_context = _LEGACY.build_candidate_context
