from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# 1) Hook declarative ending contract.
path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")
if "[DECLARATIVE HOOK CONTRACT]" not in text:
    text = text.replace(
        "필수 규칙:\n",
        "필수 규칙:\n"
        "- [DECLARATIVE HOOK CONTRACT] 한국어 Hook은 가능하면 자연스러운 단정형 한 문장으로 쓰고 '~다.'로 끝낸다.\n"
        "- '왜 그럴까요?', '뭘까요?', '알고 계셨나요?'처럼 generic question Hook은 만들지 않는다.\n"
        "- 첫 문장에서 정답 전체를 공개하지 않되, 구체적 관찰 사실/이상현상을 단정적으로 제시한다.\n",
        1,
    )
text = append_once(
    text,
    "OUTPUT_QUALITY_DECLARATIVE_HOOK",
    r'''
# OUTPUT_QUALITY_DECLARATIVE_HOOK
_GENERIC_QUESTION_ENDINGS = (
    "까요", "나요", "뭘까요", "무엇일까요", "왜일까요",
    "알고 계셨나요", "아시나요", "일까요", "인가요", "습니까",
)


def _output_quality_is_declarative_hook(text):
    compact = str(text or "").strip()
    if not compact:
        return False
    if "?" in compact:
        return False
    body = compact.rstrip(".!… ")
    if any(body.endswith(item) for item in _GENERIC_QUESTION_ENDINGS):
        return False
    return body.endswith("다")


_output_quality_original_valid_hook_shape = _valid_hook_shape


def _valid_hook_shape(text, keyword):
    if not _output_quality_original_valid_hook_shape(text, keyword):
        return False
    return _output_quality_is_declarative_hook(text)
''',
)
path.write_text(text, encoding="utf-8")


# 2) Hook subject visibility: reuse the existing real early-frame vision judge,
# but make the most specific Hook subject/detail an explicit score and gate.
path = Path("video/hook_visual_dominance.py")
text = path.read_text(encoding="utf-8")
if "hook_subject_visibility (0-10)" not in text:
    text = text.replace(
        "Identify the concrete subject explicitly promised by the Hook. Then score:\n",
        "Identify the MOST SPECIFIC concrete subject/detail explicitly promised by the Hook. "
        "If the Hook names a small part (for example a tiny hole in an airplane window), do not accept the broader object (airplane/window) as sufficient. Then score:\n"
        "- hook_subject_visibility (0-10): the exact Hook subject/detail itself is visibly present, large enough, and immediately identifiable on a phone. A broad category match does not count.\n",
        1,
    )
    text = text.replace(
        '  "subject_dominance": 0,\n',
        '  "hook_subject_visibility": 0,\n  "subject_dominance": 0,\n',
        1,
    )
text = append_once(
    text,
    "OUTPUT_QUALITY_HOOK_SUBJECT_VISIBILITY",
    r'''
# OUTPUT_QUALITY_HOOK_SUBJECT_VISIBILITY
HOOK_SUBJECT_VISIBILITY_MIN = 8.0
_output_quality_original_normalize_dominance_result = normalize_dominance_result
_output_quality_original_passes_dominance_gate = passes_dominance_gate


def normalize_dominance_result(payload, *, action_required):
    result = _output_quality_original_normalize_dominance_result(
        payload,
        action_required=action_required,
    )
    try:
        visibility = float(payload.get("hook_subject_visibility"))
    except Exception:
        visibility = (
            float(result.get("subject_dominance", 0.0))
            if result.get("vertical_crop_subject_visible")
            else 0.0
        )
    result["hook_subject_visibility"] = round(
        max(0.0, min(10.0, visibility)),
        3,
    )
    return result


def passes_dominance_gate(result):
    if not _output_quality_original_passes_dominance_gate(result):
        return False
    return float(result.get("hook_subject_visibility", 0.0)) >= HOOK_SUBJECT_VISIBILITY_MIN
''',
)
path.write_text(text, encoding="utf-8")


# 3) General scene selection: before the existing bounded filters/quality choice,
# prefer candidates whose provider metadata directly matches the current scene query.
# If there is no strong direct match, keep the exact existing fallback behavior.
path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "OUTPUT_QUALITY_DIRECT_NARRATION_MATCH",
    r'''
# OUTPUT_QUALITY_DIRECT_NARRATION_MATCH
_DIRECT_MATCH_GENERIC_TERMS = {
    "airplane", "aircraft", "plane", "airport", "aviation", "flight",
    "building", "city", "road", "bridge", "people", "person", "video",
}


def current_narration_semantic_match(candidate, scene_query):
    query_words = set(normalize_search_query(scene_query).split())
    metadata_words = set(_candidate_metadata(candidate).split())
    specific = {
        word for word in query_words
        if len(word) >= 3 and word not in _DIRECT_MATCH_GENERIC_TERMS
    }
    generic = query_words - specific
    specific_hits = len(specific & metadata_words)
    generic_hits = len(generic & metadata_words)
    # Specific current-scene terms dominate category-only overlap.
    return round(specific_hits * 3.0 + generic_hits * 0.35, 3)


_output_quality_original_choose_best_candidate = choose_best_candidate


def choose_best_candidate(
    candidates,
    relevant_top_n=None,
    *,
    historical=False,
    subject_filter_query=None,
):
    if candidates and subject_filter_query and not historical:
        scored = [
            (current_narration_semantic_match(item, subject_filter_query), item)
            for item in candidates
        ]
        best_direct = max((score for score, _ in scored), default=0.0)
        # Require at least one specific-term hit (3.0). Otherwise preserve legacy fallback.
        if best_direct >= 3.0:
            direct_pool = [
                item for score, item in scored
                if score >= best_direct - 0.001
            ]
            selected = _output_quality_original_choose_best_candidate(
                direct_pool,
                relevant_top_n=relevant_top_n,
                historical=historical,
                subject_filter_query=subject_filter_query,
            )
            if selected:
                print(
                    "[CURRENT_NARRATION_SEMANTIC_MATCH] "
                    f"score={best_direct:.3f} candidates={len(direct_pool)}/{len(candidates)}"
                )
                return selected

    return _output_quality_original_choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )
''',
)
path.write_text(text, encoding="utf-8")


# 4) Information density: generation hard check + quality/rewrite guidance.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
if "[INFORMATION DENSITY — REQUIRED]" not in text:
    text = text.replace(
        "[QUESTION COVERAGE — REQUIRED]\n",
        "[INFORMATION DENSITY — REQUIRED]\n"
        "목표 길이를 채우기 위해 이미 설명한 사실을 다시 말하지 마라.\n"
        "핵심 payoff가 끝났다면 자연스럽게 종료한다.\n"
        "'역할을 합니다', '설계된 것입니다' 같은 결론 문구가 앞 문장의 의미를 반복할 뿐이면 삭제한다.\n"
        "새 정보 없는 요약, 결론 이후 추가 설명, 같은 의미의 ending expansion을 만들지 마라.\n"
        "정보가 충분하면 40~50초대 종료도 허용하며, 실제 정보가 필요하면 55초 이상도 허용한다. 길이보다 정보 밀도를 우선한다.\n\n"
        "[QUESTION COVERAGE — REQUIRED]\n",
        1,
    )
text = append_once(
    text,
    "OUTPUT_QUALITY_INFORMATION_DENSITY",
    r'''
# OUTPUT_QUALITY_INFORMATION_DENSITY
_INFORMATION_DENSITY_FILLER_PATTERNS = (
    r"역할을\s*합니다[.!…]?$",
    r"설계된\s*것입니다[.!…]?$",
    r"의미가\s*있습니다[.!…]?$",
)
_INFORMATION_DENSITY_STOPWORDS = {
    "그리고", "하지만", "그래서", "결국", "이것", "이렇게", "것입니다",
    "합니다", "있습니다", "됩니다", "때문", "역할", "설계",
}


def _output_quality_information_tokens(text):
    return {
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣]+", str(text or ""))
        if len(token) >= 2 and token not in _INFORMATION_DENSITY_STOPWORDS
    }


def detect_information_density_issue(scenes):
    if not isinstance(scenes, list) or len(scenes) < 2:
        return None
    seen = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        text = str(scene.get("text", "")).strip()
        tokens = _output_quality_information_tokens(text)
        if not tokens:
            continue
        for prior in seen:
            union = tokens | prior
            overlap = len(tokens & prior) / max(1, len(union))
            if overlap >= 0.72:
                return f"scene {index + 1} repeats previously explained information"
        seen.append(tokens)

    ending = str(scenes[-1].get("text", "")).strip() if isinstance(scenes[-1], dict) else ""
    if any(re.search(pattern, ending) for pattern in _INFORMATION_DENSITY_FILLER_PATTERNS):
        ending_tokens = _output_quality_information_tokens(ending)
        prior_tokens = set().union(*seen[:-1]) if len(seen) > 1 else set()
        if ending_tokens and len(ending_tokens - prior_tokens) <= 1:
            return "ending expansion adds no meaningful new information"
    return None


_output_quality_original_validate_script = validate_script


def validate_script(result):
    valid, reason = _output_quality_original_validate_script(result)
    if not valid:
        return valid, reason
    issue = detect_information_density_issue(result.get("scenes", []))
    if issue:
        return False, f"정보 밀도 실패: {issue}"
    return True, reason
''',
)
path.write_text(text, encoding="utf-8")


path = Path("quality/explanation_judge.py")
text = path.read_text(encoding="utf-8")
if "5. INFORMATION DENSITY" not in text:
    text = text.replace(
        "4. 범위 제한\n",
        "4. INFORMATION DENSITY\n"
        "- 이미 설명한 사실의 반복, 새 정보 없는 요약, payoff 이후의 추가 설명은 감점한다.\n"
        "- '역할을 합니다', '설계된 것입니다'처럼 앞 문장을 말만 바꿔 반복하는 ending expansion은 정보 보상이 아니다.\n"
        "- 길이가 짧다는 이유만으로 감점하지 말고, 실제 필요한 정보가 있으면 긴 대본도 허용한다. duration이 아니라 정보 밀도를 평가한다.\n\n"
        "5. 범위 제한\n",
        1,
    )
path.write_text(text, encoding="utf-8")


path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
if "[INFORMATION DENSITY 수정]" not in text:
    text = text.replace(
        "[EXPLANATION 수정]\n",
        "[EXPLANATION 수정]\n"
        "[INFORMATION DENSITY 수정]\n"
        "- 이미 설명한 사실을 다시 말하는 문장, 새 정보 없는 요약, payoff 이후의 ending expansion은 제거하거나 압축한다.\n"
        "- 길이를 채우기 위해 문장을 추가하지 말고 핵심 payoff가 끝났다면 자연스럽게 종료한다.\n"
        "- 실제 필요한 새 정보가 있으면 55초 이상도 허용하며 duration 자체를 목표로 삼지 않는다.\n",
        1,
    )
path.write_text(text, encoding="utf-8")

print("✅ Output quality hotfix applied: declarative hook, subject visibility, direct scene match, information density")
