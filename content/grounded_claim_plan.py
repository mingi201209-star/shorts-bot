"""Deterministic grounded factual-claim planning for Script Engine V2.

The Writer must not decide which factual effects exist. This module consumes only
claims with explicit provenance from the private trusted-grounding channel (or an
identically structured caller-injected fixture), assigns each claim to exactly one
scene, and validates Writer narration back against those owned claims.

No model/network call, retry, threshold relaxation, topic word list, or subject-
specific branch exists here.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, Iterable, List


_CLAIM_TYPE_ORDER = {
    "mechanism_input": 10,
    "constraint": 15,
    "mechanism_change": 20,
    "mechanism_step": 30,
    "mechanism_effect": 35,
    "result": 40,
    "primary_result": 40,
    "tradeoff": 50,
    "payoff": 60,
}

# Linguistic relation normalization only. These are not topic/effect blacklists:
# the same relation parser is used for every physical subject.
_DECREASE_TERMS = ("줄", "감소", "낮", "완화", "약화", "reduce", "decrease", "lower", "quiet")
_INCREASE_TERMS = ("향상", "증가", "높", "개선", "늘", "improve", "increase", "raise")

_PARTICLE_SUFFIXES = (
    "으로부터", "에게서", "에서는", "으로는", "으로", "에서", "에게", "께서", "부터", "까지",
    "처럼", "보다", "하고", "이며", "이면", "에는", "으로", "의", "은", "는", "이", "가", "을", "를",
    "에", "와", "과", "도", "만", "로", "서",
)

_STOP_TOKENS = {
    "이", "그", "저", "것", "때", "데", "수", "등", "위해", "통해", "결과", "결과적", "디자인",
    "설계", "구조", "효과", "기여", "도움", "주된", "대표적", "fact", "claim", "effect", "result",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_token(token: str) -> str:
    value = re.sub(r"[^0-9a-z가-힣]+", "", str(token or "").lower())
    if not value:
        return ""
    if re.search(r"[가-힣]", value):
        changed = True
        while changed:
            changed = False
            for suffix in _PARTICLE_SUFFIXES:
                if value.endswith(suffix) and len(value) - len(suffix) >= 2:
                    value = value[:-len(suffix)]
                    changed = True
                    break
    return value


def _tokens(value: Any) -> List[str]:
    result: List[str] = []
    for raw in re.findall(r"[0-9A-Za-z가-힣]+", _text(value).lower()):
        token = _normalize_token(raw)
        if len(token) < 2 or token in _STOP_TOKENS:
            continue
        result.append(token)
    return result


def _token_overlap(left: Any, right: Any) -> float:
    a, b = set(_tokens(left)), set(_tokens(right))
    if not a or not b:
        return 0.0
    return len(a & b) / float(min(len(a), len(b)))


def _relation_for_token(token: str) -> str:
    value = _normalize_token(token)
    if any(term in value for term in _DECREASE_TERMS):
        return "decrease"
    if any(term in value for term in _INCREASE_TERMS):
        return "increase"
    return ""


def _effect_signatures(value: Any) -> set[str]:
    """Extract generic outcome relations such as decrease:<object>.

    This catches paraphrases like "항력을 줄인다" and "항력 감소" without
    knowing what 항력 means or maintaining any subject-specific vocabulary.
    """
    raw_tokens = re.findall(r"[0-9A-Za-z가-힣]+", _text(value).lower())
    normalized = [_normalize_token(token) for token in raw_tokens]
    signatures: set[str] = set()
    for index, raw in enumerate(raw_tokens):
        relation = _relation_for_token(raw)
        if not relation:
            continue
        object_token = ""
        for previous in range(index - 1, max(-1, index - 4), -1):
            if previous < 0:
                break
            candidate = normalized[previous]
            if len(candidate) < 2 or candidate in _STOP_TOKENS:
                continue
            if _relation_for_token(candidate):
                continue
            object_token = candidate
            break
        if object_token:
            signatures.add(f"{relation}:{object_token}")
    return signatures


def _claim_scope_texts(claim: Dict[str, Any]) -> List[str]:
    values = [_text(claim.get("evidence_summary"))]
    values.extend(_text(item) for item in claim.get("allowed_paraphrase_scope") or [])
    return [item for item in values if item]


def _claim_effect_signatures(claim: Dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for value in _claim_scope_texts(claim):
        result.update(_effect_signatures(value))
    return result


def _claim_matches_text(text: Any, claim: Dict[str, Any]) -> bool:
    candidate = _text(text)
    if not candidate:
        return False

    sentence_effects = _effect_signatures(candidate)
    claim_effects = _claim_effect_signatures(claim)
    if sentence_effects and claim_effects and sentence_effects & claim_effects:
        return True

    best = 0.0
    for scope in _claim_scope_texts(claim):
        best = max(best, _token_overlap(candidate, scope))
    return best >= 0.45


def _valid_claim(raw: Any) -> bool:
    if not isinstance(raw, dict):
        return False
    if not _text(raw.get("claim_id")) or not _text(raw.get("claim_type")):
        return False
    if not _text(raw.get("evidence_summary")):
        return False
    if not _text(raw.get("source")) or not _text(raw.get("detail")):
        return False
    scope = raw.get("allowed_paraphrase_scope")
    return isinstance(scope, list) and any(_text(item) for item in scope)


def extract_grounded_claims(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return deduplicated provenance-bearing claims in deterministic causal order."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    trusted = candidate.get("_trusted_grounded_claims") or []
    claims: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for position, raw in enumerate(trusted):
        if not _valid_claim(raw):
            continue
        claim_id = _text(raw.get("claim_id"))
        if claim_id in seen:
            continue
        seen.add(claim_id)
        item = {
            "claim_id": claim_id,
            "claim_type": _text(raw.get("claim_type")),
            "evidence_summary": _text(raw.get("evidence_summary")),
            "source": _text(raw.get("source")),
            "detail": _text(raw.get("detail")),
            "allowed_paraphrase_scope": [
                _text(value) for value in raw.get("allowed_paraphrase_scope") or [] if _text(value)
            ],
            "provenance_present": True,
            "_source_order": position,
        }
        claims.append(item)

    claims.sort(key=lambda item: (
        _CLAIM_TYPE_ORDER.get(item["claim_type"], 35),
        int(item["_source_order"]),
        item["claim_id"],
    ))
    for item in claims:
        item.pop("_source_order", None)
    return claims


def assign_claim_owners(claims: Iterable[Dict[str, Any]], *, first_scene: int = 3) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    used_ids: set[str] = set()
    used_scenes: set[int] = set()
    for offset, raw in enumerate(claims):
        item = deepcopy(raw)
        claim_id = _text(item.get("claim_id"))
        owner = int(first_scene) + offset
        if not claim_id or claim_id in used_ids:
            raise ValueError("grounded claim ids must be unique")
        if owner in used_scenes:
            raise ValueError("each grounded claim must own exactly one unique scene")
        used_ids.add(claim_id)
        used_scenes.add(owner)
        item["owner_scene"] = owner
        result.append(item)
    return result


def build_grounded_claim_plan(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    claims = extract_grounded_claims(candidate)
    if not claims:
        return []
    return assign_claim_owners(claims, first_scene=3)


def validate_grounded_claim_usage(script: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reconnect each factual Writer scene to its pre-owned grounded claim.

    This is not a second FACT Judge. It only enforces provenance/ownership:
    every factual scene must realize its owned claim, no claim may migrate to
    another scene, and extra decrease/increase effects may not be invented.
    """
    claim_plan = plan.get("grounded_claim_plan") if isinstance(plan, dict) else None
    if not isinstance(claim_plan, list) or not claim_plan:
        return []

    claims = {str(item.get("claim_id")): item for item in claim_plan if isinstance(item, dict)}
    contracts = {
        int(item.get("index")): item
        for item in plan.get("contracts") or []
        if isinstance(item, dict) and item.get("index") is not None
    }
    scenes = script.get("scenes") if isinstance(script, dict) else None
    if not isinstance(scenes, list):
        return [{"scene_index": None, "reason": "grounded claim validation: script.scenes must be a list"}]

    failures: List[Dict[str, Any]] = []
    planned_effects: set[str] = set()
    for claim in claim_plan:
        planned_effects.update(_claim_effect_signatures(claim))

    # Generic paraphrase duplicate detector for outcome relations. The first
    # occurrence becomes the observed owner for diagnostic purposes.
    effect_occurrences: Dict[str, List[int]] = {}
    for scene_index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        text = _text(scene.get("text"))
        for signature in sorted(_effect_signatures(text)):
            effect_occurrences.setdefault(signature, []).append(scene_index)

    for signature, indexes in effect_occurrences.items():
        if len(indexes) < 2:
            continue
        owner = indexes[0]
        for offending in indexes[1:]:
            failures.append({
                "scene_index": offending,
                "reason": (
                    f"duplicate claim relation={signature} owner_scene={owner} "
                    f"offending_scene={offending}"
                ),
            })

    for scene_index, scene in enumerate(scenes, start=1):
        if scene_index < 3 or not isinstance(scene, dict):
            continue
        contract = contracts.get(scene_index) or {}
        owned_id = _text(contract.get("owned_claim_id"))
        text = _text(scene.get("text"))

        if not owned_id or owned_id not in claims:
            failures.append({
                "scene_index": scene_index,
                "reason": f"unplanned factual claim: scene {scene_index} has no grounded owned claim",
            })
            continue

        owned = claims[owned_id]
        if not bool(owned.get("provenance_present")):
            failures.append({
                "scene_index": scene_index,
                "reason": f"grounded claim {owned_id} is missing provenance",
            })

        matching_ids = [
            claim_id for claim_id, claim in claims.items()
            if _claim_matches_text(text, claim)
        ]
        if owned_id not in matching_ids:
            failures.append({
                "scene_index": scene_index,
                "reason": (
                    f"unplanned factual claim: scene {scene_index} does not realize "
                    f"owned claim {owned_id}"
                ),
            })
        for other_id in matching_ids:
            if other_id == owned_id:
                continue
            owner_scene = int(claims[other_id].get("owner_scene") or 0)
            failures.append({
                "scene_index": scene_index,
                "reason": (
                    f"duplicate claim {other_id} owner_scene={owner_scene} "
                    f"offending_scene={scene_index}"
                ),
            })

        # If a sentence includes an extra outcome relation that is not supported
        # by any planned claim, it is an unsupported expansion even when the
        # sentence also correctly states its owned claim.
        for signature in sorted(_effect_signatures(text) - planned_effects):
            failures.append({
                "scene_index": scene_index,
                "reason": (
                    f"unplanned factual claim: scene {scene_index} adds unsupported "
                    f"relation {signature}"
                ),
            })

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for failure in failures:
        key = (failure.get("scene_index"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)
    return deduped
