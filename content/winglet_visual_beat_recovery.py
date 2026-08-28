"""Bounded Script ↔ Visual support recovery for the winglet production counterexample.

V1 is intentionally narrow: it only replaces an unsupported winglet noise-benefit
beat when the existing script/candidate already grounds an airflow explanation and
that airflow information has not already been narrated. It adds no model calls,
changes no FACT/visual thresholds, and fails closed when its proof conditions are
not met.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Optional


RECOVERY_MARKER = "WINGLET_UNSUPPORTED_VISUAL_BEAT_RECOVERY_V1"
UPLOAD_REPAIR_MARKER = "WINGLET_UPLOAD_REPAIR_33190260884_V1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _blob(values: Iterable[Any]) -> str:
    return " ".join(_text(value).lower() for value in values if _text(value))


def _micro(candidate: Dict[str, Any]) -> Dict[str, Any]:
    value = candidate.get("micro_narrative") or {}
    return value if isinstance(value, dict) else {}


def _is_winglet_aviation_context(candidate: Dict[str, Any]) -> bool:
    micro = _micro(candidate)
    context = _blob((
        candidate.get("topic"),
        candidate.get("angle"),
        candidate.get("core_question"),
        micro.get("hook"),
        micro.get("reveal"),
        micro.get("payoff"),
    ))
    aviation = any(token in context for token in (
        "비행기", "항공", "aircraft", "airplane", "aviation",
    ))
    winglet = any(token in context for token in (
        "윙렛", "날개 끝", "winglet", "wing tip", "wingtip",
    ))
    return aviation and winglet


def _repair_run_33190260884_upload_blocks(script: Dict[str, Any]) -> Dict[str, Any]:
    """Repair only the two human-QA blockers observed in Run 33190260884.

    This is deliberately keyed to the exact malformed Scene 3 sentence from that
    run. When that counterexample is absent, the function is a no-op. No model
    call, threshold, retry, FACT scope, or budget is changed.
    """
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    if len(scenes) < 3 or not all(isinstance(scene, dict) for scene in scenes[:3]):
        return result

    scene3 = scenes[2]
    malformed = (
        "원인의 첫 단서는 날개 끝이 위로 꺾인 모습은 "
        "비행기의 성능에 영향을 미칩니다."
    )
    if _text(scene3.get("text")) != malformed:
        return result

    scene1 = scenes[0]
    if _text(scene1.get("text")) == "비행기 날개 끝이 위로 꺾여 있습니다.":
        scene1["visual_goal"] = "비행기 날개 끝의 윙렛을 선명하게 보여주는 근접 모습"
        scene1["keyword"] = "airplane wing winglet closeup stage 1"

    scene3["text"] = "위로 꺾인 날개 끝은 공기 흐름을 바꿔 비행 성능에 영향을 줍니다."
    scene3["visual_goal"] = "윙렛 주변에서 달라지는 날개 끝 공기 흐름"
    scene3["keyword"] = "airplane wing winglet airflow stage 3"

    result["scenes"] = scenes
    result["winglet_upload_repair"] = {
        "version": 1,
        "source_run": 33190260884,
        "scene1": "explicit_winglet_closeup",
        "scene3": "natural_airflow_explanation",
        "additional_api_calls": 0,
    }
    print(
        f"[{UPLOAD_REPAIR_MARKER}] status=repaired "
        "scene1=explicit_winglet_closeup scene3=natural_airflow_explanation"
    )
    return result


def _is_noise_benefit_scene(scene: Dict[str, Any]) -> bool:
    value = _blob((scene.get("text"), scene.get("visual_goal"), scene.get("keyword")))
    noise = "소음" in value or "noise" in value
    benefit = any(token in value for token in (
        "감소", "줄", "기여", "reduction", "reduce", "benefit",
    ))
    return noise and benefit


def _airflow_information_already_narrated(scene: Dict[str, Any]) -> bool:
    narration = _text(scene.get("text")).lower()
    return any(token in narration for token in (
        "공기 흐름",
        "공기의 흐름",
        "airflow",
        "흐름을 바꿉",
        "흐름이 바뀝",
        "흐름이 달라",
        "흐름을 조절",
    ))


def _candidate_airflow_evidence(candidate: Dict[str, Any]) -> bool:
    evidence = list(candidate.get("fact_check_focus") or []) + list(candidate.get("visual_proof") or [])
    value = _blob(evidence)
    return any(token in value for token in (
        "공기 흐름", "공기의 흐름", "airflow", "wingtip flow", "flow around",
    ))


def _existing_script_airflow_grounding(scenes: list[Dict[str, Any]]) -> bool:
    """Accept only the exact already-grounded causal contract seen in production.

    Run 33169424813 already paired an induced-drag narration with an airflow
    visual/search contract. Reusing that existing semantic contract as a spoken
    beat adds no new performance claim; the downstream FACT Judge remains the
    authoritative hard gate for the resulting full script.
    """
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        narration = _text(scene.get("text")).lower()
        visual_contract = _blob((scene.get("visual_goal"), scene.get("keyword")))
        induced_drag = "유도항력" in narration or "induced drag" in narration
        airflow_visual = any(token in visual_contract for token in (
            "공기 흐름", "airflow", "flow",
        ))
        if induced_drag and airflow_visual:
            return True
    return False


def _airflow_grounding_source(candidate: Dict[str, Any], scenes: list[Dict[str, Any]]) -> Optional[str]:
    if _candidate_airflow_evidence(candidate):
        return "candidate_evidence"
    if _existing_script_airflow_grounding(scenes):
        return "existing_script_contract"
    return None


def recover_unsupported_winglet_visual_beat(
    script: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    """Recover one unsupported winglet noise beat without spending an API call.

    The recovery is deliberately all-or-nothing. If context, grounding, or
    novelty checks fail, the original script is returned unchanged so the
    existing visual path can fail closed exactly as before.
    """
    original = deepcopy(script)
    if not isinstance(script, dict) or not isinstance(candidate, dict):
        return original
    if not _is_winglet_aviation_context(candidate):
        return original

    original = _repair_run_33190260884_upload_blocks(original)
    scenes = deepcopy(original.get("scenes") or [])
    if not scenes or not all(isinstance(scene, dict) for scene in scenes):
        return original

    target_indexes = [
        index
        for index, scene in enumerate(scenes, start=1)
        if _is_noise_benefit_scene(scene)
    ]
    if len(target_indexes) != 1:
        return original

    # Information novelty is narration-based: an earlier airflow visual used to
    # illustrate induced drag does not itself consume the airflow explanation beat.
    if any(
        _airflow_information_already_narrated(scene)
        for index, scene in enumerate(scenes, start=1)
        if index not in target_indexes
    ):
        print(
            f"[{RECOVERY_MARKER}] status=duplicate_rejected beat=airflow"
        )
        return original

    grounding = _airflow_grounding_source(candidate, scenes)
    if not grounding:
        print(
            f"[{RECOVERY_MARKER}] status=ungrounded_rejected beat=airflow"
        )
        return original

    scene_index = target_indexes[0]
    target = scenes[scene_index - 1]
    target["text"] = "윙렛은 날개 끝의 공기 흐름을 바꿉니다."
    target["visual_goal"] = "윙렛 주변 날개 끝 공기 흐름 방향"
    target["keyword"] = f"aircraft wing airflow direction stage {scene_index}"

    result = deepcopy(original)
    result["scenes"] = scenes
    result["winglet_visual_beat_recovery"] = {
        "version": 1,
        "scene_index": scene_index,
        "from": "noise_reduction",
        "to": "airflow",
        "visual_explanation_template": "WINGLET_FLOW",
        "grounding": grounding,
        "additional_api_calls": 0,
    }
    print(
        f"[{RECOVERY_MARKER}] status=recovered scene={scene_index} "
        f"from=noise_reduction to=airflow template=WINGLET_FLOW grounding={grounding}"
    )
    return result
