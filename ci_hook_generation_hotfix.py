from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

import_marker = "import json\nimport os\nimport re\n"
import_replacement = "import hashlib\nimport json\nimport os\nimport re\nfrom collections import Counter\n"

normalize_start = text.index("def _normalize_candidates(payload):")
request_start = text.index("def _request_candidates(", normalize_start)
normalize_block = text[normalize_start:request_start]

replacement_block = '''def _candidate_text_key(text):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", str(text or "")).lower()


def _diagnose_candidates(payload):
    diagnostics = {
        "raw_candidate_count": 0,
        "parsed_candidate_count": 0,
        "normalized_candidate_count": 0,
        "length_valid_count": 0,
        "speech_style_valid_count": 0,
        "clarity_floor_count": 0,
        "specificity_floor_count": 0,
        "visual_potential_floor_count": 0,
        "fact_safety_floor_count": 0,
        "scoring_pool_count": 0,
        "rejected": Counter(),
    }

    if not isinstance(payload, dict):
        diagnostics["rejected"]["invalid_schema"] += 1
        return [], diagnostics

    raw_candidates = payload.get("candidates", [])
    if not isinstance(raw_candidates, list):
        diagnostics["rejected"]["invalid_schema"] += 1
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

        text_key = _candidate_text_key(text)
        if not text_key or text_key in seen_texts:
            diagnostics["rejected"]["duplicate"] += 1
            continue
        seen_texts.add(text_key)

        diagnostics["normalized_candidate_count"] += 1

        speech_valid, _ = validate_korean_speech_text(
            text,
            allow_nominal=True,
        )
        if not speech_valid:
            diagnostics["rejected"]["speech_style_failure"] += 1
            continue

        diagnostics["speech_style_valid_count"] += 1

        scores, total_score = _score_hook(item)

        floor_failures = []
        for key, minimum in HOOK_CRITERIA_FLOORS.items():
            if float(scores.get(key, 0.0)) < minimum:
                floor_failures.append(f"{key}_below_floor")
            else:
                diagnostics[f"{key}_floor_count"] += 1

        if floor_failures:
            for reason in floor_failures:
                diagnostics["rejected"][reason] += 1

        normalized.append({
            "id": str(item.get("id") or f"hook_{index}"),
            "text": text,
            "visual_goal": visual_goal,
            "keyword": keyword,
            "scores": scores,
            "criteria_pass": not floor_failures,
            "total_score": total_score,
            "reason": str(item.get("reason", "")).strip(),
        })

    diagnostics["scoring_pool_count"] = len(normalized)
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
        f"scoring_pool_count={diagnostics.get('scoring_pool_count', 0)}"
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

request_return_marker = '''    return _normalize_candidates(
        _extract_json(response.choices[0].message.content)
    )
'''
request_return_replacement = '''    raw_text = str(response.choices[0].message.content or "")
    raw_fingerprint = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:12]
    print(
        f"[HOOK] raw_response_chars={len(raw_text)} "
        f"raw_response_sha256={raw_fingerprint}"
    )

    try:
        payload = _extract_json(raw_text)
    except Exception as exc:
        diagnostics = {
            "raw_candidate_count": 0,
            "parsed_candidate_count": 0,
            "normalized_candidate_count": 0,
            "length_valid_count": 0,
            "speech_style_valid_count": 0,
            "scoring_pool_count": 0,
            "rejected": {"parse_failure": 1},
        }
        _print_hook_diagnostics(diagnostics)
        print(f"[HOOK] parse_error_type={type(exc).__name__}")
        return []

    candidates, diagnostics = _diagnose_candidates(payload)
    _print_hook_diagnostics(diagnostics)
    return candidates
'''

if import_replacement not in text:
    if text.count(import_marker) != 1:
        raise RuntimeError("hook instrumentation import marker mismatch")
    text = text.replace(import_marker, import_replacement, 1)

if replacement_block not in text:
    if text.count(normalize_block) != 1:
        raise RuntimeError("hook instrumentation normalize block mismatch")
    text = text.replace(normalize_block, replacement_block, 1)

if request_return_replacement not in text:
    if text.count(request_return_marker) != 1:
        raise RuntimeError("hook instrumentation request return marker mismatch")
    text = text.replace(request_return_marker, request_return_replacement, 1)

path.write_text(text, encoding="utf-8")
print("✅ Hook generation observability hotfix applied")
