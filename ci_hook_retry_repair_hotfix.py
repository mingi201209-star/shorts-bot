from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

request_marker = '''    candidates, diagnostics = _diagnose_candidates(payload)
    _print_hook_diagnostics(diagnostics)
    return candidates, diagnostics
'''
request_replacement = '''    candidates, diagnostics = _diagnose_candidates(payload)

    raw_candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
    repair_candidates = []
    length_histogram = {}

    if isinstance(raw_candidates, list):
        for raw_item in raw_candidates:
            if not isinstance(raw_item, dict):
                continue

            raw_text = str(raw_item.get("text", "")).strip()
            if not raw_text:
                continue

            visible_len = _visible_len(raw_text)
            length_key = str(visible_len)
            length_histogram[length_key] = length_histogram.get(length_key, 0) + 1

            if visible_len < HOOK_MIN_CHARS:
                repair_candidates.append({
                    "text": raw_text,
                    "visible_len": visible_len,
                    "visual_goal": str(raw_item.get("visual_goal", "")).strip(),
                    "keyword": str(raw_item.get("keyword", "")).strip(),
                })

    diagnostics["length_histogram"] = dict(
        sorted(
            length_histogram.items(),
            key=lambda pair: int(pair[0]),
        )
    )
    diagnostics["repair_candidates"] = repair_candidates[:HOOK_GENERATION_COUNT]

    _print_hook_diagnostics(diagnostics)
    print(
        "[HOOK] length_histogram="
        + json.dumps(
            diagnostics.get("length_histogram", {}),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return candidates, diagnostics
'''

prompt_marker = '''이전 탈락 사유가 있으면 가장 많이 발생한 사유부터 이번 출력에서 직접 고친다.
길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.
'''
prompt_replacement = '''이전 탈락 사유가 있으면 가장 많이 발생한 사유부터 이번 출력에서 직접 고친다.
길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.
rejection_feedback 안에 repair_candidates가 있으면 그 문장들은 실제 1차에서 too_short로 탈락한 Hook이다.
각 repair candidate의 핵심 대상과 의미를 유지하면서 공백 제외 14~16자로 자연스럽게 늘려 다시 작성한다.
단순 조사 추가만 하지 말고 짧은 관찰 가능한 동작/결과를 보태되 Candidate Lock의 사실 범위를 넘지 않는다.
repair candidate만 복제하지 말고 필요하면 같은 Candidate Lock 안에서 서로 다른 새 Hook도 함께 만든다.
'''

select_replacement = '''def select_hook(topic_info, candidate):
    audit = {
        "enabled": True,
        "candidate_count_required": HOOK_CANDIDATE_COUNT,
        "generation_candidate_count": HOOK_GENERATION_COUNT,
        "hook_char_range": [HOOK_MIN_CHARS, HOOK_MAX_CHARS],
        "criteria": list(HOOK_CRITERIA),
        "criteria_floors": dict(HOOK_CRITERIA_FLOORS),
        "threshold": HOOK_MIN_SCORE,
        "max_regenerations": HOOK_MAX_REGENERATIONS,
        "attempts": [],
        "selected": None,
        "fallback": False,
    }

    cumulative_pool = {}
    rejection_feedback = None

    for attempt in range(1, HOOK_MAX_REGENERATIONS + 2):
        try:
            request_result = _request_candidates(
                topic_info,
                candidate,
                attempt,
                rejection_feedback=rejection_feedback,
            )
        except TypeError as exc:
            if "rejection_feedback" not in str(exc):
                raise
            request_result = _request_candidates(
                topic_info,
                candidate,
                attempt,
            )

        if (
            isinstance(request_result, tuple)
            and len(request_result) == 2
            and isinstance(request_result[1], dict)
        ):
            candidates, diagnostics = request_result
        else:
            candidates = list(request_result or [])
            diagnostics = _empty_hook_diagnostics()
            count = len(candidates)
            scoring_pool_count = sum(
                1
                for item in candidates
                if item.get("criteria_pass", False)
            )
            eligible_candidate_count = sum(
                1
                for item in candidates
                if item.get("criteria_pass", False)
                and float(item.get("total_score", 0.0)) >= HOOK_MIN_SCORE
            )
            diagnostics.update({
                "raw_candidate_count": count,
                "parsed_candidate_count": count,
                "normalized_candidate_count": count,
                "length_valid_count": count,
                "shape_valid_count": count,
                "speech_style_valid_count": count,
                "clarity_valid_count": scoring_pool_count,
                "specificity_valid_count": scoring_pool_count,
                "visual_potential_valid_count": scoring_pool_count,
                "fact_safety_valid_count": scoring_pool_count,
                "scoring_pool_count": scoring_pool_count,
                "eligible_candidate_count": eligible_candidate_count,
                "rejected": {},
                "repair_candidates": [],
            })

        candidates.sort(key=lambda item: item["total_score"], reverse=True)

        for item in candidates:
            if not item.get("criteria_pass", False):
                continue
            text_key = _candidate_text_key(item.get("text", ""))
            if not text_key:
                continue
            previous = cumulative_pool.get(text_key)
            if (
                previous is None
                or float(item.get("total_score", 0.0))
                > float(previous.get("total_score", 0.0))
            ):
                cumulative_pool[text_key] = item

        combined_candidates = sorted(
            cumulative_pool.values(),
            key=lambda item: item["total_score"],
            reverse=True,
        )
        combined_best = _best_passing_candidate(combined_candidates)

        audit["attempts"].append({
            "attempt": attempt,
            "candidate_count": len(candidates),
            "raw_candidate_count": diagnostics.get("raw_candidate_count", 0),
            "parsed_candidate_count": diagnostics.get("parsed_candidate_count", 0),
            "normalized_candidate_count": diagnostics.get("normalized_candidate_count", 0),
            "length_valid_count": diagnostics.get("length_valid_count", 0),
            "speech_style_valid_count": diagnostics.get("speech_style_valid_count", 0),
            "scoring_pool_count": diagnostics.get("scoring_pool_count", 0),
            "cumulative_scoring_pool_count": len(combined_candidates),
            "eligible_candidate_count": diagnostics.get("eligible_candidate_count", 0),
            "rejected": diagnostics.get("rejected", {}),
            "length_histogram": diagnostics.get("length_histogram", {}),
            "best_score": (
                combined_best.get("total_score")
                if combined_best
                else None
            ),
        })

        print(
            "[HOOK] cumulative_scoring_pool_count="
            f"{len(combined_candidates)}"
        )

        if (
            len(combined_candidates) >= HOOK_CANDIDATE_COUNT
            and combined_best
        ):
            audit["selected"] = combined_best
            print(
                f"[HOOK] selected={combined_best.get('id', '')} "
                "fallback=false"
            )
            return combined_best, audit

        rejection_feedback = {
            "rejection_counts": diagnostics.get("rejected", {}),
            "repair_candidates": diagnostics.get("repair_candidates", []),
        }

        if attempt <= HOOK_MAX_REGENERATIONS:
            print(
                "[HOOK] bounded_retry_feedback="
                + json.dumps(
                    rejection_feedback["rejection_counts"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            print(
                "[HOOK] bounded_retry_repair_count="
                f"{len(rejection_feedback['repair_candidates'])}"
            )

    audit["fallback"] = True
    audit["fallback_reason"] = (
        "두 번의 bounded Hook 생성 후에도 검증된 scoring pool 후보 5개를 확보하지 못했습니다."
    )
    print("[HOOK] selected=none fallback=true")
    return None, audit


'''

if request_replacement not in text:
    if text.count(request_marker) != 1:
        raise RuntimeError(
            "Hook retry repair request marker mismatch: "
            f"{text.count(request_marker)}"
        )
    text = text.replace(request_marker, request_replacement, 1)

if prompt_replacement not in text:
    if text.count(prompt_marker) != 1:
        raise RuntimeError(
            "Hook retry repair prompt marker mismatch: "
            f"{text.count(prompt_marker)}"
        )
    text = text.replace(prompt_marker, prompt_replacement, 1)

if select_replacement not in text:
    select_start = text.index("def select_hook(topic_info, candidate):")
    select_end = text.index("def print_hook_audit(", select_start)
    current_select = text[select_start:select_end]
    text = text.replace(current_select, select_replacement, 1)

path.write_text(text, encoding="utf-8")
print("✅ Hook bounded repair + cumulative five-candidate pool hotfix applied")
