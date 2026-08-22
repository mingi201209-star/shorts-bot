from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

replacements = [
    ("- 안정적으로 범위 안에 들어오도록 13~15자를 목표로 쓴다.", "- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다."),
    ("길이 탈락이면 13~15자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.", "길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다."),
    ('''각 Hook을 0~10점으로 평가한다.
평가 기준: stop_power, curiosity_gap, clarity, specificity, visual_potential, fact_safety.
''', '''각 Hook을 0~10점으로 평가한다.
각 candidate에 char_count를 함께 출력한다. char_count는 text에서 공백만 제거한 실제 글자 수다.
평가 기준: stop_power, curiosity_gap, clarity, specificity, visual_potential, fact_safety.
'''),
    ('''- 출력 직전에 각 text의 공백을 제거해 글자 수를 다시 세고, 12자 미만 또는 16자 초과면 반드시 다시 쓴다.
- 모든 spoken Hook은 자연스러운 한국어 존댓말로 끝낸다. 예: ~요, ~죠, ~니다, ~니까, ~세요.
''', '''- 출력 직전에 각 text의 공백을 제거해 글자 수를 다시 세고, 12자 미만 또는 16자 초과면 반드시 다시 쓴다.
- 길이 감각 예시(내용을 복사하지 말고 길이만 참고):
  * "드론 카메라는 균열을 먼저 찾아내요" = 공백 제외 15자
  * "남극 기지는 눈 위로 더 높이 올라가요" = 공백 제외 15자
  * "사막여우 귀는 열을 밖으로 내보내요" = 공백 제외 15자
- 모든 spoken Hook은 자연스러운 한국어 존댓말로 끝낸다. 예: ~요, ~죠, ~니다, ~니까, ~세요.
'''),
    ('''      "text": "한국어 존댓말 Hook 한 문장",
      "visual_goal": "첫 화면에 반드시 보여야 할 구체적 대상과 관찰 가능한 현상",
''', '''      "text": "한국어 존댓말 Hook 한 문장",
      "char_count": 15,
      "visual_goal": "첫 화면에 반드시 보여야 할 구체적 대상과 관찰 가능한 현상",
'''),
    ("        temperature=0.75,\n", "        temperature=0.5,\n"),
    ('''    best = None
    rejection_feedback = None
''', '''    best = None
    pool_ready = False
    rejection_feedback = None
'''),
    ('''        candidates, diagnostics = _request_candidates(
            topic_info,
            candidate,
            attempt,
            rejection_feedback=rejection_feedback,
        )
        candidates.sort(key=lambda item: item["total_score"], reverse=True)
''', '''        try:
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
            scoring_pool_count = sum(1 for item in candidates if item.get("criteria_pass", False))
            eligible_candidate_count = sum(
                1 for item in candidates
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
            })

        candidates.sort(key=lambda item: item["total_score"], reverse=True)
'''),
    ('''        if (
            diagnostics.get("scoring_pool_count", 0) >= HOOK_CANDIDATE_COUNT
            and round_best
        ):
            break
''', '''        if (
            diagnostics.get("scoring_pool_count", 0) >= HOOK_CANDIDATE_COUNT
            and round_best
        ):
            pool_ready = True
            break
'''),
    ("    if best is None:\n", "    if best is None or not pool_ready:\n"),
]

for old, new in replacements:
    if new in text:
        continue
    if text.count(old) != 1:
        raise RuntimeError("Hook scoring-pool guard marker mismatch: " f"{old[:60]!r} count={text.count(old)}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("✅ Hook measurable length guidance + pool guard + legacy request compatibility applied")

repair_hotfix = Path("ci_hook_retry_repair_hotfix.py")
if not repair_hotfix.exists():
    raise RuntimeError("ci_hook_retry_repair_hotfix.py not found")
exec(compile(repair_hotfix.read_text(encoding="utf-8"), str(repair_hotfix), "exec"), {"__name__": "__main__"})

structure_hotfix = Path("ci_hook_structure_guidance_hotfix.py")
if not structure_hotfix.exists():
    raise RuntimeError("ci_hook_structure_guidance_hotfix.py not found")
exec(compile(structure_hotfix.read_text(encoding="utf-8"), str(structure_hotfix), "exec"), {"__name__": "__main__"})

observable_hotfix = Path("ci_observable_statement_hook_hotfix.py")
if not observable_hotfix.exists():
    raise RuntimeError("ci_observable_statement_hook_hotfix.py not found")
exec(compile(observable_hotfix.read_text(encoding="utf-8"), str(observable_hotfix), "exec"), {"__name__": "__main__"})
