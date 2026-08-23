"""Deterministic subscriber-conversion planning for Shorts.

The layer is intentionally model/provider-free. It never changes Candidate selection,
never places CTA language before the payoff, and omits CTA when retention headroom is
insufficient.
"""

from copy import deepcopy
import re

SUBSCRIBER_CONVERSION_VERSION = 1
CTA_MAX_ESTIMATED_SECONDS = 2.5

_FORBIDDEN_CTA_PATTERNS = (
    r"구독\s*해주세요",
    r"좋아요.{0,6}구독",
    r"구독.{0,6}좋아요",
    r"알림\s*설정",
    r"다음\s*영상에서\s*(?:공개|알려|보여)",
    r"다음\s*편에서\s*(?:공개|알려|보여)",
)

_AVIATION_SIGNALS = (
    "비행기", "항공기", "항공", "기내", "객실", "날개", "엔진", "창문", "좌석",
    "착륙장치", "조종석", "airplane", "aircraft", "aviation", "cabin", "cockpit",
)

_SERIES_CONTINUITY_SIGNALS = (
    "왜", "이유", "숨은", "설계", "구조", "원리", "기능", "평소", "익숙",
    "보지만", "몰랐", "일상", "장치", "mechanism", "design", "structure",
)


def _candidate_text(candidate):
    if not isinstance(candidate, dict):
        return ""
    parts = []
    for key in (
        "topic", "angle", "core_question", "specific_observation", "constraint",
        "counterintuitive_result", "tradeoff", "concrete_condition", "selection_reason",
        "candidate_scope", "scope", "category",
    ):
        value = candidate.get(key)
        if value:
            parts.append(str(value))
    micro = candidate.get("micro_narrative") or {}
    if isinstance(micro, dict):
        parts.extend(str(value) for value in micro.values() if value)
    return " ".join(parts).lower()


def infer_series_identity(candidate):
    text = _candidate_text(candidate)
    if any(signal in text for signal in _AVIATION_SIGNALS):
        return "비행기에서 늘 보지만 이유는 몰랐던 설계와 원리"
    if any(signal in text for signal in ("도시", "건물", "건축", "교량", "도로", "터널", "인프라")):
        return "도시에서 늘 보지만 이유는 몰랐던 구조와 설계"
    return "익숙한 것에서 발견하는 숨은 이유와 원리"


def _series_continuity_score(candidate):
    text = _candidate_text(candidate)
    score = sum(1 for signal in _SERIES_CONTINUITY_SIGNALS if signal in text)
    visual_proof = candidate.get("visual_proof") if isinstance(candidate, dict) else None
    if isinstance(visual_proof, list) and len(visual_proof) >= 2:
        score += 1
    micro = candidate.get("micro_narrative") if isinstance(candidate, dict) else None
    if isinstance(micro, dict) and micro.get("reveal") and micro.get("payoff"):
        score += 1
    return score


def _is_aviation(candidate):
    text = _candidate_text(candidate)
    return any(signal in text for signal in _AVIATION_SIGNALS)


def build_subscriber_conversion_plan(candidate):
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a mapping")

    identity = infer_series_identity(candidate)
    score = _series_continuity_score(candidate)

    if _is_aviation(candidate) and score >= 2:
        mode = "soft_series_cta"
        cta_text = "비행기에서 보던 것들의 이유가 궁금하시다면 구독해 두셔도 좋습니다."
        reason = "aviation series continuity is strong"
    elif score >= 4:
        mode = "soft_series_cta"
        cta_text = "익숙한 것들의 숨은 이유가 궁금하시다면 구독해 두셔도 좋습니다."
        reason = "recurring series value is explicit"
    elif score >= 2:
        mode = "curiosity_bridge"
        cta_text = "익숙한 것들의 숨은 이유는 주변에 아직 더 많습니다."
        reason = "topic supports a broader curiosity bridge"
    else:
        mode = "none"
        cta_text = ""
        reason = "series continuity is too weak"

    return {
        "version": SUBSCRIBER_CONVERSION_VERSION,
        "subscriber_conversion_mode": mode,
        "series_identity": identity,
        "cta_text": cta_text,
        "cta_added": False,
        "cta_reason": reason,
    }


def validate_cta_text(text):
    value = str(text or "").strip()
    if not value:
        return True, "empty CTA allowed"
    if any(re.search(pattern, value) for pattern in _FORBIDDEN_CTA_PATTERNS):
        return False, "forbidden engagement boilerplate or ungrounded next-video promise"
    if len(re.findall(r"[.!?…]+", value)) > 1:
        return False, "CTA must be at most one spoken sentence"
    compact_len = len(re.sub(r"\s+", "", value))
    if compact_len > 42:
        return False, "CTA is too long for bounded conversion layer"
    return True, "CTA language pass"


def _estimate_text_seconds(text):
    compact_len = len(re.sub(r"\s+", "", str(text or "")))
    # Conservative approximation for the accelerated Korean TTS path. The exact
    # renderer remains authoritative; this is only a pre-render omission guard.
    return compact_len / 7.0


def estimate_script_seconds(scenes):
    if not isinstance(scenes, list):
        return 0.0
    return sum(
        _estimate_text_seconds(scene.get("text", ""))
        for scene in scenes
        if isinstance(scene, dict)
    )


def _cta_visual(candidate):
    text = _candidate_text(candidate)
    if any(signal in text for signal in _AVIATION_SIGNALS):
        return {
            "visual_goal": "실제 여객기 외부 또는 객실의 익숙한 설계 디테일을 선명하게 보여주는 장면",
            "keyword": "airplane cabin design detail",
        }
    if any(signal in text for signal in ("도시", "건물", "건축", "교량", "도로", "터널", "인프라")):
        return {
            "visual_goal": "도시 건축물이나 인프라의 구체적인 구조 디테일을 보여주는 장면",
            "keyword": "city infrastructure design detail",
        }
    return {
        "visual_goal": "영상의 핵심 물리적 대상을 마지막으로 선명하게 다시 보여주는 장면",
        "keyword": "everyday object design detail",
    }


def apply_subscriber_conversion(script, candidate, plan=None):
    result = deepcopy(script)
    plan = deepcopy(plan or build_subscriber_conversion_plan(candidate))

    mode = plan.get("subscriber_conversion_mode", "none")
    cta_text = str(plan.get("cta_text", "")).strip()
    valid, reason = validate_cta_text(cta_text)
    if not valid:
        plan["subscriber_conversion_mode"] = "none"
        plan["cta_text"] = ""
        plan["cta_added"] = False
        plan["cta_reason"] = reason
        result.update(plan)
        return result

    scenes = list(result.get("scenes") or [])
    retention = result.get("retention_structure") or {}
    max_scenes = int(retention.get("max_scenes") or len(scenes) + 1)
    max_seconds = float(retention.get("max_seconds") or 60.0)

    if mode == "none" or not cta_text:
        plan["cta_added"] = False
        result.update(plan)
        return result

    if len(scenes) >= max_scenes:
        plan["subscriber_conversion_mode"] = "none"
        plan["cta_text"] = ""
        plan["cta_added"] = False
        plan["cta_reason"] = "no scene-count headroom in retention bucket"
        result.update(plan)
        return result

    estimated_before = estimate_script_seconds(scenes)
    estimated_cta = _estimate_text_seconds(cta_text)
    if estimated_cta > CTA_MAX_ESTIMATED_SECONDS or estimated_before + estimated_cta > max_seconds:
        plan["subscriber_conversion_mode"] = "none"
        plan["cta_text"] = ""
        plan["cta_added"] = False
        plan["cta_reason"] = "insufficient estimated runtime headroom"
        result.update(plan)
        return result

    visual = _cta_visual(candidate)
    scenes.append({
        "text": cta_text,
        "visual_goal": visual["visual_goal"],
        "visual_type": "real_world_broll",
        "keyword": visual["keyword"],
        "retention_role": "subscriber_conversion",
        "subscriber_conversion": True,
    })
    result["scenes"] = scenes
    plan["cta_added"] = True
    plan["cta_reason"] = plan.get("cta_reason") or "subscriber conversion CTA appended after payoff"
    result.update(plan)
    return result


def subscriber_conversion_prompt_contract(plan):
    return (
        "[SUBSCRIBER CONVERSION RESERVE]\n"
        f"subscriber_conversion_mode={plan['subscriber_conversion_mode']}. "
        "본문의 factual payoff를 먼저 완결한다. CTA는 Script Generator가 직접 쓰지 않는다. "
        "후처리 레이어가 필요할 때만 마지막에 한 문장을 추가하므로, CTA 대상 모드에서는 "
        "retention bucket 상한까지 본문을 억지로 채우지 말고 약 2초의 여유를 남긴다. "
        "Hook/첫 5초에는 구독·좋아요·알림·다음 영상 약속을 절대 넣지 않는다.\n"
    )
