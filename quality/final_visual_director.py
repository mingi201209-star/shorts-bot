"""Visual Quality V1: deterministic, budget-neutral director gates.

This module does not call an API and never rewrites narration or FACT content.
It consumes scores/observations already produced by visual verification and turns
those observations into role-aware hard floors, best-valid-candidate selection,
and a bounded selective-repair plan.
"""
from collections import Counter

MAX_DIRECTOR_REPAIR_SCENES = 2
MAX_DIRECTOR_RECOVERY_ROUNDS = 2
MECHANISM_ROLES = {"cause", "mechanism", "solution"}
HOOK_ROLES = {"hook", "reveal"}
TRANSITION_ROLES = {"setup", "transition", "atmosphere"}
PAYOFF_ROLES = {"result", "conclusion"}

ROLE_HINTS = {
    "hook": ("왜", "사실", "보이", "놀랍"),
    "cause": ("때문", "원인", "생기", "발생"),
    "mechanism": ("원리", "구조", "작동", "줄입", "줄이", "막아", "흐름", "소용돌"),
    "solution": ("해결", "설계", "바꿨", "개선"),
    "result": ("결과", "그래서", "덕분"),
    "conclusion": ("결국", "즉", "핵심"),
}


def infer_scene_role(scene, index=0, total=1):
    explicit = str(scene.get("role") or scene.get("scene_role") or "").strip().lower()
    if explicit in {"hook", "reveal", "setup", "problem", "cause", "mechanism", "contrast", "solution", "result", "conclusion", "transition", "atmosphere"}:
        return explicit
    text = " ".join(str(scene.get(k) or "") for k in ("text", "visual_goal")).lower()
    if index == 0:
        return "hook"
    for role in ("cause", "mechanism", "solution", "result", "conclusion"):
        if any(hint in text for hint in ROLE_HINTS[role]):
            return role
    if index == total - 1:
        return "conclusion"
    return "setup"


def hard_floors_for_role(role):
    # Additive floors only; existing visual thresholds remain authoritative.
    if role in HOOK_ROLES:
        return {"subject_prominence": 7.0, "mobile_clarity": 8.0, "hook_visual_strength": 7.0}
    if role in MECHANISM_ROLES:
        return {"semantic_match": 7.0, "explanatory_power": 7.0, "subject_prominence": 6.0}
    if role in PAYOFF_ROLES:
        return {"semantic_match": 7.0, "payoff_visual_strength": 6.5}
    if role in TRANSITION_ROLES:
        return {"semantic_match": 6.0, "explanatory_power": 4.0}
    return {"semantic_match": 7.0, "explanatory_power": 5.5}


def evaluate_candidate(candidate, role):
    scores = dict(candidate.get("scores") or {})
    floors = hard_floors_for_role(role)
    failures = []
    for metric, floor in floors.items():
        value = float(scores.get(metric, 0.0) or 0.0)
        if value < floor:
            failures.append({"metric": metric, "score": value, "floor": floor})
    if float(scores.get("artifact_risk", 0.0) or 0.0) > 4.0:
        failures.append({"metric": "artifact_risk", "score": float(scores["artifact_risk"]), "ceiling": 4.0})
    if float(scores.get("obstruction_risk", 0.0) or 0.0) > 4.0:
        failures.append({"metric": "obstruction_risk", "score": float(scores["obstruction_risk"]), "ceiling": 4.0})
    return {"valid": not failures, "failures": failures, "role": role}


def candidate_quality_score(candidate):
    s = dict(candidate.get("scores") or {})
    positive = (
        1.5 * float(s.get("semantic_match", 0) or 0)
        + 1.8 * float(s.get("explanatory_power", 0) or 0)
        + 1.2 * float(s.get("subject_prominence", 0) or 0)
        + 1.1 * float(s.get("mobile_clarity", 0) or 0)
        + float(s.get("composition_quality", 0) or 0)
        + float(s.get("motion_quality", 0) or 0)
        + .8 * float(s.get("novelty", 0) or 0)
        + .7 * float(s.get("continuity_with_previous_scene", 0) or 0)
        + .7 * float(s.get("continuity_with_next_scene", 0) or 0)
    )
    risk = float(s.get("artifact_risk", 0) or 0) + float(s.get("obstruction_risk", 0) or 0)
    return positive - risk


def select_best_valid_candidate(candidates, role, *, max_candidates=2):
    """Compare at most two supplied candidates; never creates extra candidates."""
    evaluated = []
    for candidate in list(candidates or [])[:max_candidates]:
        result = evaluate_candidate(candidate, role)
        score = candidate_quality_score(candidate)
        evaluated.append((candidate, result, score))
        print(f"[VisualQuality] candidate={candidate.get('id', '?')} role={role} explanatory_power={float((candidate.get('scores') or {}).get('explanatory_power', 0) or 0):.1f} valid={result['valid']} score={score:.2f}")
    valid = [item for item in evaluated if item[1]["valid"]]
    if not valid:
        return None
    selected = max(valid, key=lambda item: item[2])[0]
    print(f"[VisualQuality] candidate={selected.get('id', '?')} SELECTED")
    return selected


def director_qa(scene_observations):
    issues = []
    source_ids = [str(x.get("source_id") or "") for x in scene_observations]
    counts = Counter(x for x in source_ids if x)
    for obs in scene_observations:
        idx = int(obs.get("scene_index", 0))
        role = str(obs.get("role") or "setup")
        scores = dict(obs.get("scores") or {})
        result = evaluate_candidate({"scores": scores}, role)
        for failure in result["failures"]:
            metric = failure["metric"]
            issue_type = "low_explanatory_power" if metric == "explanatory_power" else metric
            issues.append({"scene_index": idx, "start_sec": obs.get("start_sec"), "end_sec": obs.get("end_sec"), "severity": "high", "type": issue_type, "reason": f"{metric} hard floor failed"})
        source_id = str(obs.get("source_id") or "")
        repetition_count = counts.get(source_id, 0)
        if repetition_count >= 3:
            issues.append({
                "scene_index": idx,
                "start_sec": obs.get("start_sec"),
                "end_sec": obs.get("end_sec"),
                "severity": "high",
                "type": "repetition_risk",
                "reason": "same visual source appears in at least three scenes",
                "source_id": source_id,
                "repetition_count": repetition_count,
            })
        if bool(obs.get("subtitle_obstruction")):
            issues.append({"scene_index": idx, "severity": "high", "type": "subtitle_obstruction", "reason": "subtitle overlaps protected visual region", "repair": "subtitle_relocation"})
        if float(scores.get("ai_artifact_risk", scores.get("artifact_risk", 0)) or 0) > 4.0:
            issues.append({"scene_index": idx, "severity": "high", "type": "ai_artifact_risk", "reason": "visible AI/structural artifact risk exceeds ceiling"})
        if bool(obs.get("information_beat_changed")) and bool(obs.get("same_visual_as_previous")):
            issues.append({"scene_index": idx, "severity": "medium", "type": "stale_information_beat", "reason": "new information beat starts without a meaningful visual change"})
    deduped = []
    seen = set()
    for issue in issues:
        key = (issue["scene_index"], issue["type"])
        if key not in seen:
            seen.add(key); deduped.append(issue)
    score_values = []
    for obs in scene_observations:
        s = obs.get("scores") or {}
        for key in ("hook_visual_strength", "semantic_match", "explanatory_power", "mobile_clarity", "payoff_visual_strength"):
            if key in s: score_values.append(float(s[key]))
    overall = round(sum(score_values) / len(score_values), 2) if score_values else 0.0
    payload = {"overall_pass": not any(x["severity"] == "high" for x in deduped), "overall_score": overall, "issues": deduped}
    print(f"[DirectorQA] overall_score={overall:.2f} {'PASS' if payload['overall_pass'] else 'FAIL'}")
    for issue in deduped:
        print(f"[DirectorQA] FAIL scene={issue['scene_index']} reason={issue['type']}")
    return payload


REPAIR_PRIORITY = {"hook_visual_strength": 0, "subject_prominence": 0, "low_explanatory_power": 1, "semantic_match": 2, "ai_artifact_risk": 3, "subtitle_obstruction": 4, "repetition_risk": 5, "stale_information_beat": 6}


def _minimal_repetition_repairs(visual_issues):
    """Return the minimum scene replacements needed for repetition-only QA.

    A source used N times only needs N-2 replacements to satisfy the existing
    hard rule (no source may appear in 3+ scenes). This does not relax the rule;
    it avoids recreating an extra healthy scene before Director re-evaluates.
    """
    if not visual_issues or any(x.get("type") != "repetition_risk" for x in visual_issues):
        return None
    if any(not x.get("source_id") or int(x.get("repetition_count", 0) or 0) < 3 for x in visual_issues):
        return None

    by_source = {}
    source_order = []
    for issue in visual_issues:
        source_id = str(issue["source_id"])
        if source_id not in by_source:
            by_source[source_id] = []
            source_order.append(source_id)
        by_source[source_id].append(issue)

    selected = []
    for source_id in source_order:
        group = sorted(by_source[source_id], key=lambda x: int(x["scene_index"]))
        repetition_count = max(int(x.get("repetition_count", 0) or 0) for x in group)
        needed = max(1, repetition_count - 2)
        for issue in group[:needed]:
            idx = int(issue["scene_index"])
            if idx not in selected:
                selected.append(idx)
            if len(selected) == MAX_DIRECTOR_REPAIR_SCENES:
                return selected
    return selected


def selective_repair_plan(qa_result, recovery_round):
    if recovery_round >= MAX_DIRECTOR_RECOVERY_ROUNDS:
        return {"status": "HOLD", "reason": "director recovery limit reached", "scene_indexes": [], "subtitle_only": []}
    issues = list(qa_result.get("issues") or [])
    if not issues:
        return {"status": "PASS", "scene_indexes": [], "subtitle_only": []}
    subtitle_only = sorted({int(x["scene_index"]) for x in issues if x["type"] == "subtitle_obstruction" and x.get("repair") == "subtitle_relocation"})
    visual_issues = [x for x in issues if int(x["scene_index"]) not in subtitle_only]
    visual_issues.sort(key=lambda x: (REPAIR_PRIORITY.get(x["type"], 99), int(x["scene_index"])))
    selected = _minimal_repetition_repairs(visual_issues)
    if selected is None:
        selected = []
        for issue in visual_issues:
            idx = int(issue["scene_index"])
            if idx not in selected:
                selected.append(idx)
            if len(selected) == MAX_DIRECTOR_REPAIR_SCENES:
                break
    print(f"[DirectorQA] selective_repair scenes={selected} subtitle_only={subtitle_only}")
    return {"status": "REPAIR", "scene_indexes": selected, "subtitle_only": subtitle_only}
