from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")


def _replace_function(source, name, next_name, replacement):
    start_marker = f"def {name}("
    end_marker = f"def {next_name}("
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[:start] + replacement + source[end:]


# ============================================================
# Imports / generation count
# ============================================================
import_marker = "import json\nimport os\nimport re\n"
import_replacement = (
    "import hashlib\n"
    "import json\n"
    "import os\n"
    "import re\n"
    "from collections import Counter\n"
)
if import_replacement not in text:
    if text.count(import_marker) != 1:
        raise RuntimeError("Hook generation import marker mismatch")
    text = text.replace(import_marker, import_replacement, 1)

generation_marker = "HOOK_MAX_REGENERATIONS = max(\n"
generation_block = '''HOOK_GENERATION_COUNT = max(
    HOOK_CANDIDATE_COUNT,
    int(os.environ.get("HOOK_GENERATION_COUNT", "10")),
)
HOOK_MAX_REGENERATIONS = max(
'''
if "HOOK_GENERATION_COUNT = max(" not in text:
    if text.count(generation_marker) != 1:
        raise RuntimeError("Hook generation count marker mismatch")
    text = text.replace(generation_marker, generation_block, 1)


# ============================================================
# Deterministic validation + reason-code observability
# ============================================================
normalize_replacement = '''def _candidate_text_key(text):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", str(text or "")).lower()


def _empty_hook_diagnostics():
    return {
        "raw_candidate_count": 0,
        "parsed_candidate_count": 0,
        "normalized_candidate_count": 0,
        "length_valid_count": 0,
        "shape_valid_count": 0,
        "speech_style_valid_count": 0,
        "clarity_valid_count": 0,
        "specificity_valid_count": 0,
        "visual_potential_valid_count": 0,
        "fact_safety_valid_count": 0,
        "scoring_pool_count": 0,
        "eligible_candidate_count": 0,
        "rejected": Counter(),
    }


def _diagnose_candidates(payload):
    diagnostics = _empty_hook_diagnostics()

    if not isinstance(payload, dict):
        diagnostics["rejected"]["invalid_schema"] += 1
        diagnostics["rejected"] = dict(diagnostics["rejected"])
        return [], diagnostics

    raw_candidates = payload.get("candidates", [])
    if not isinstance(raw_candidates, list):
        diagnostics["rejected"]["invalid_schema"] += 1
        diagnostics["rejected"] = dict(diagnostics["rejected"])
        return [], diagnostics

    diagnostics["raw_candidate_count"] = len(raw_candidates)
    seen_texts = set()
    normalized = []

    for index, item in enumerate(raw_candidates, start=1):
        if not isinstance(item, dict):
            diagnostics["rejected"]["invalid_schema"] += 1
            continue

        diagnostics["parsed_candidate_count"] += 1

        text = str(item.get("text", "")).strip()
        visual_goal = str(item.get("visual_goal", "")).strip()
        keyword = " ".join(str(item.get("keyword", "")).strip().split())

        if not text or not visual_goal or not keyword:
            diagnostics["rejected"]["invalid_schema"] += 1
            continue

        diagnostics["normalized_candidate_count"] += 1

        text_key = _candidate_text_key(text)
        if not text_key or text_key in seen_texts:
            diagnostics["rejected"]["duplicate"] += 1
            continue
        seen_texts.add(text_key)

        visible_len = _visible_len(text)
        if visible_len < HOOK_MIN_CHARS:
            diagnostics["rejected"]["too_short"] += 1
            continue
        if visible_len > HOOK_MAX_CHARS:
            diagnostics["rejected"]["too_long"] += 1
            continue

        diagnostics["length_valid_count"] += 1

        if len(re.findall(r"[.!?…]+", text)) > 1:
            diagnostics["rejected"]["too_many_sentences"] += 1
            continue

        words = keyword.split()
        if len(words) < 2 or len(words) > 7:
            diagnostics["rejected"]["invalid_keyword_word_count"] += 1
            continue
        if not re.search(r"[A-Za-z]", keyword):
            diagnostics["rejected"]["invalid_keyword_language"] += 1
            continue

        keyword_words = _keyword_words(keyword)
        invisible_hits = keyword_words & INVISIBLE_VISUAL_TERMS
        observable_hits = keyword_words & OBSERVABLE_VISUAL_TERMS
        if invisible_hits and not observable_hits:
            diagnostics["rejected"]["invisible_visual_only"] += 1
            continue

        diagnostics["shape_valid_count"] += 1

        speech_valid, _ = validate_korean_speech_text(
            text,
            allow_nominal=True,
        )
        if not speech_valid:
            diagnostics["rejected"]["speech_style_failure"] += 1
            continue

        diagnostics["speech_style_valid_count"] += 1

        scores, total_score = _score_hook(item)
        criteria_pass = True

        if scores["clarity"] < HOOK_CRITERIA_FLOORS["clarity"]:
            diagnostics["rejected"]["clarity_below_floor"] += 1
            criteria_pass = False
        else:
            diagnostics["clarity_valid_count"] += 1

            if scores["specificity"] < HOOK_CRITERIA_FLOORS["specificity"]:
                diagnostics["rejected"]["specificity_below_floor"] += 1
                criteria_pass = False
            else:
                diagnostics["specificity_valid_count"] += 1

                if scores["visual_potential"] < HOOK_CRITERIA_FLOORS["visual_potential"]:
                    diagnostics["rejected"]["visual_potential_below_floor"] += 1
                    criteria_pass = False
                else:
                    diagnostics["visual_potential_valid_count"] += 1

                    if scores["fact_safety"] < HOOK_CRITERIA_FLOORS["fact_safety"]:
                        diagnostics["rejected"]["fact_safety_below_floor"] += 1
                        criteria_pass = False
                    else:
                        diagnostics["fact_safety_valid_count"] += 1
                        diagnostics["scoring_pool_count"] += 1
                        if total_score >= HOOK_MIN_SCORE:
                            diagnostics["eligible_candidate_count"] += 1
                        else:
                            diagnostics["rejected"]["score_below_threshold"] += 1

        normalized.append({
            "id": str(item.get("id") or f"hook_{index}"),
            "text": text,
            "visual_goal": visual_goal,
            "keyword": keyword,
            "scores": scores,
            "criteria_pass": criteria_pass,
            "total_score": total_score,
            "reason": str(item.get("reason", "")).strip(),
        })

    diagnostics["rejected"] = dict(sorted(diagnostics["rejected"].items()))
    return normalized, diagnostics


def _normalize_candidates(payload):
    candidates, _ = _diagnose_candidates(payload)
    return candidates


def _print_hook_diagnostics(diagnostics):
    print(
        "[HOOK] "
        f"raw_candidate_count={diagnostics.get('raw_candidate_count', 0)} "
        f"parsed_candidate_count={diagnostics.get('parsed_candidate_count', 0)} "
        f"normalized_candidate_count={diagnostics.get('normalized_candidate_count', 0)} "
        f"length_valid_count={diagnostics.get('length_valid_count', 0)} "
        f"speech_style_valid_count={diagnostics.get('speech_style_valid_count', 0)} "
        f"scoring_pool_count={diagnostics.get('scoring_pool_count', 0)} "
        f"eligible_candidate_count={diagnostics.get('eligible_candidate_count', 0)}"
    )
    print(
        "[HOOK] floors="
        + json.dumps(
            {
                "clarity": diagnostics.get("clarity_valid_count", 0),
                "specificity": diagnostics.get("specificity_valid_count", 0),
                "visual_potential": diagnostics.get("visual_potential_valid_count", 0),
                "fact_safety": diagnostics.get("fact_safety_valid_count", 0),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    print(
        "[HOOK] rejected="
        + json.dumps(
            diagnostics.get("rejected", {}),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


'''
text = _replace_function(
    text,
    "_normalize_candidates",
    "_request_candidates",
    normalize_replacement,
)


# ============================================================
# Generation prompt + bounded rejection feedback
# ============================================================
request_replacement = '''def _request_candidates(
    topic_info,
    candidate,
    generation_round,
    rejection_feedback=None,
):
    feedback = dict(rejection_feedback or {})
    feedback_text = (
        json.dumps(feedback, ensure_ascii=False, sort_keys=True)
        if feedback
        else "없음"
    )

    prompt = f"""
너는 YouTube Shorts 첫 1~3초 Hook Selector다.
Candidate Explorer와 Candidate Gate가 이미 소재를 확정했다.
새 소재나 새로운 사실을 만들지 말고 아래 확정 Candidate 안에서만 작업한다.

[TOPIC INFO]
{json.dumps(topic_info, ensure_ascii=False, indent=2)}

[CANDIDATE LOCK]
{json.dumps(candidate, ensure_ascii=False, indent=2)}

서로 다른 Hook 후보를 정확히 {HOOK_GENERATION_COUNT}개 만든다.
최종 validator가 최소 {HOOK_CANDIDATE_COUNT}개의 강한 후보를 확보할 수 있도록 여유 있게 만든다.
각 Hook을 0~10점으로 평가한다.
평가 기준: stop_power, curiosity_gap, clarity, specificity, visual_potential, fact_safety.

필수 규칙:
- 실제 TTS가 1~3초에 들어오도록 아주 짧은 한국어 한 문장만 쓴다.
- text는 공백만 제외한 길이가 반드시 {HOOK_MIN_CHARS}~{HOOK_MAX_CHARS}자다.
- 안정적으로 범위 안에 들어오도록 13~15자를 목표로 쓴다.
- 출력 직전에 각 text의 공백을 제거해 글자 수를 다시 세고, 12자 미만 또는 16자 초과면 반드시 다시 쓴다.
- 모든 spoken Hook은 자연스러운 한국어 존댓말로 끝낸다. 예: ~요, ~죠, ~니다, ~니까, ~세요.
- 반말/해라체 종결인 ~다, ~한다, ~했다, ~이다를 사용하지 않는다.
- 첫 구절에 구체적 대상 이름을 바로 넣는다.
- "이것", "이 기술", "이 시스템"처럼 대상을 늦게 밝히지 않는다.
- 후보끼리 같은 문장을 복제하거나 조사만 바꿔 반복하지 않는다.
- 첫 화면은 대사의 핵심 의미를 영상만 봐도 즉시 이해할 수 있어야 한다.
- 방향, 효율, 안전성처럼 카메라로 바로 확인하기 어려운 속성만 검색하지 마라.
- 그런 속성이 핵심이면 햇빛, 그림자, 움직임, 구조 변화 같은 관찰 가능한 결과를 첫 화면으로 선택한다.
- visual_goal은 핵심 피사체 하나를 모바일에서 즉시 알아볼 수 있는 단순한 구도/클로즈업으로 쓴다.
- keyword는 그 관찰 가능한 화면을 찾는 Pexels용 2~7단어 영어 검색어다.
- Candidate의 micro_narrative, fact_check_focus, visual_proof 범위를 넘지 않는다.
- fact_safety와 visual_potential을 과장 채점하지 않는다.
- generation_round={generation_round}

[PREVIOUS REJECTION SUMMARY]
{feedback_text}
이전 탈락 사유가 있으면 가장 많이 발생한 사유부터 이번 출력에서 직접 고친다.
길이 탈락이면 13~15자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.

JSON 객체만 출력한다. candidates 이외의 최상위 필드를 만들지 않는다.
{{
  "candidates": [
    {{
      "id": "hook_1",
      "text": "한국어 존댓말 Hook 한 문장",
      "visual_goal": "첫 화면에 반드시 보여야 할 구체적 대상과 관찰 가능한 현상",
      "keyword": "specific observable visual search",
      "stop_power": 0,
      "curiosity_gap": 0,
      "clarity": 0,
      "specificity": 0,
      "visual_potential": 0,
      "fact_safety": 0,
      "reason": "짧은 평가 근거"
    }}
  ]
}}
"""

    call_number = authorize_call(MODEL)
    print(f"🪝 Hook API call authorized: #{call_number}")

    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "확정된 Shorts 소재 안에서만 사실 안전성, 실제 1~3초 길이, "
                    "자연스러운 한국어 존댓말, 화면으로 직접 증명 가능한 첫 장면을 "
                    "함께 평가하는 Hook Selector다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.75,
        response_format={"type": "json_object"},
    )

    usage = record_usage(MODEL, response)
    print(f"💰 Hook call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    raw_text = str(response.choices[0].message.content or "")
    raw_fingerprint = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:12]
    print(
        f"[HOOK] raw_response_chars={len(raw_text)} "
        f"raw_response_sha256={raw_fingerprint}"
    )

    try:
        payload = _extract_json(raw_text)
    except Exception as exc:
        diagnostics = _empty_hook_diagnostics()
        diagnostics["rejected"] = {"parse_failure": 1}
        _print_hook_diagnostics(diagnostics)
        print(f"[HOOK] parse_error_type={type(exc).__name__}")
        return [], diagnostics

    candidates, diagnostics = _diagnose_candidates(payload)
    _print_hook_diagnostics(diagnostics)
    return candidates, diagnostics


'''
text = _replace_function(
    text,
    "_request_candidates",
    "_best_passing_candidate",
    request_replacement,
)


# ============================================================
# Preserve bounded two-attempt policy, feed rejection summary forward
# ============================================================
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

    best = None
    rejection_feedback = None

    for attempt in range(1, HOOK_MAX_REGENERATIONS + 2):
        candidates, diagnostics = _request_candidates(
            topic_info,
            candidate,
            attempt,
            rejection_feedback=rejection_feedback,
        )
        candidates.sort(key=lambda item: item["total_score"], reverse=True)
        round_best = _best_passing_candidate(candidates)

        audit["attempts"].append({
            "attempt": attempt,
            "candidate_count": len(candidates),
            "raw_candidate_count": diagnostics.get("raw_candidate_count", 0),
            "parsed_candidate_count": diagnostics.get("parsed_candidate_count", 0),
            "normalized_candidate_count": diagnostics.get("normalized_candidate_count", 0),
            "length_valid_count": diagnostics.get("length_valid_count", 0),
            "speech_style_valid_count": diagnostics.get("speech_style_valid_count", 0),
            "scoring_pool_count": diagnostics.get("scoring_pool_count", 0),
            "eligible_candidate_count": diagnostics.get("eligible_candidate_count", 0),
            "rejected": diagnostics.get("rejected", {}),
            "best_score": (
                round_best.get("total_score")
                if round_best
                else None
            ),
        })

        if round_best and (
            best is None
            or round_best["total_score"] > best["total_score"]
        ):
            best = round_best

        if (
            diagnostics.get("scoring_pool_count", 0) >= HOOK_CANDIDATE_COUNT
            and round_best
        ):
            break

        rejection_feedback = diagnostics.get("rejected", {})
        if attempt <= HOOK_MAX_REGENERATIONS:
            print(
                "[HOOK] bounded_retry_feedback="
                + json.dumps(
                    rejection_feedback,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

    if best is None:
        audit["fallback"] = True
        audit["fallback_reason"] = (
            "최소 후보 수/길이/개별 기준/종합 점수를 모두 통과한 Hook이 없습니다."
        )
        print("[HOOK] selected=none fallback=true")
        return None, audit

    audit["selected"] = best
    print(f"[HOOK] selected={best.get('id', '')} fallback=false")
    return best, audit


'''
text = _replace_function(
    text,
    "select_hook",
    "print_hook_audit",
    select_replacement,
)

path.write_text(text, encoding="utf-8")
print("✅ Hook generation stability + observability hotfix applied")
