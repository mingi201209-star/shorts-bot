from pathlib import Path


def _replace_once(text, old, new, label):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} marker mismatch")
    return text.replace(old, new, 1)


# Script Generator: require reversal queries to preserve appearance + reveal sides.
script_path = Path("content/script_generator.py")
script_text = script_path.read_text(encoding="utf-8")
script_text = _replace_once(
    script_text,
    "from quality.budget_guard import (\n",
    "from quality.first5_visual_contract import validate_reversal_query\n\nfrom quality.budget_guard import (\n",
    "script first5 visual contract import",
)
script_text = _replace_once(
    script_text,
    '''        if normalized in BAD_VISUAL_KEYWORDS:\n            return False, (\n                f"{idx + 1}번 검색어가 너무 추상적임: {keyword}"\n            )\n''',
    '''        if normalized in BAD_VISUAL_KEYWORDS:\n            return False, (\n                f"{idx + 1}번 검색어가 너무 추상적임: {keyword}"\n            )\n\n        if idx < 2:\n            concept_ok, concept_reason = validate_reversal_query(scene)\n            if not concept_ok:\n                return False, (\n                    f"{idx + 1}번 첫 5초 visual concept lock 실패: "\n                    f"{concept_reason}"\n                )\n''',
    "script first5 visual concept validation",
)
script_text = _replace_once(
    script_text,
    '''- 단순 자극보다 대사와 화면의 직접 일치를 우선한다.\n''',
    '''- 단순 자극보다 대사와 화면의 직접 일치를 우선한다.\n- A처럼 보이지만 실제 B인 반전이면 첫 두 Scene의 visual_goal과 영어 keyword에 겉보기 A와 실제 B를 모두 남긴다.\n- 반전 소재를 실제 B의 정체만 남는 검색어로 축약하지 않는다. 모든 appearance-vs-reality 반전에 동일하게 적용한다.\n''',
    "script first5 reversal prompt",
)
script_path.write_text(script_text, encoding="utf-8")


# Hook generation: preserve the original Candidate reversal in visual metadata and scoring pool.
hook_path = Path("content/hook_experiment.py")
hook_text = hook_path.read_text(encoding="utf-8")
hook_text = _replace_once(
    hook_text,
    "import openai\n\n",
    "import openai\n\nfrom quality.first5_visual_contract import validate_reversal_context\n\n",
    "Hook visual concept contract import",
)
hook_text = _replace_once(
    hook_text,
    '''- 첫 화면은 대사의 핵심 의미를 영상만 봐도 즉시 이해할 수 있어야 한다.\n''',
    '''- 첫 화면은 대사의 핵심 의미를 영상만 봐도 즉시 이해할 수 있어야 한다.\n- 확정 Candidate가 A처럼 보이지만 실제 B인 반전이면 visual_goal과 keyword에 겉보기 A와 실제 B를 모두 보존한다. 실제 B의 정체만 남는 검색어로 축약하지 않는다.\n''',
    "Hook reversal visual prompt",
)
hook_text = _replace_once(
    hook_text,
    '''        candidates.sort(key=lambda item: item["total_score"], reverse=True)\n''',
    '''        concept_filtered = []\n        concept_rejected = 0\n        for item in candidates:\n            concept_ok, _ = validate_reversal_context(\n                candidate,\n                item.get("keyword", ""),\n            )\n            if concept_ok:\n                concept_filtered.append(item)\n            else:\n                concept_rejected += 1\n\n        if concept_rejected:\n            rejected = dict(diagnostics.get("rejected", {}))\n            rejected["reversal_concept_loss"] = (\n                rejected.get("reversal_concept_loss", 0)\n                + concept_rejected\n            )\n            diagnostics["rejected"] = rejected\n            diagnostics["scoring_pool_count"] = sum(\n                1 for item in concept_filtered\n                if item.get("criteria_pass", False)\n            )\n            diagnostics["eligible_candidate_count"] = sum(\n                1 for item in concept_filtered\n                if item.get("criteria_pass", False)\n                and float(item.get("total_score", 0.0)) >= HOOK_MIN_SCORE\n            )\n        candidates = concept_filtered\n\n        candidates.sort(key=lambda item: item["total_score"], reverse=True)\n''',
    "Hook reversal scoring-pool filter",
)
hook_path.write_text(hook_text, encoding="utf-8")


# Hook visual: remember strict scene1 concept and require scene2 progression.
visual_path = Path("video/hook_visual.py")
visual_text = visual_path.read_text(encoding="utf-8")
visual_text = _replace_once(
    visual_text,
    '''import json\nimport re\n\nfrom config import (\n''',
    '''import json\nimport re\n\nfrom quality.first5_visual_contract import (\n    progression_passes,\n    validate_reversal_query,\n    visual_signature,\n)\n\nfrom config import (\n''',
    "hook visual contract import",
)
visual_text = _replace_once(
    visual_text,
    '''HOOK_DOMINANCE_MAX_CANDIDATES = 3\n\n\ndef _tokens(text):\n''',
    '''HOOK_DOMINANCE_MAX_CANDIDATES = 3\nOPENING_FIRST_VISUAL_SIGNATURE = None\n\n\ndef _tokens(text):\n''',
    "opening visual state",
)
visual_text = _replace_once(
    visual_text,
    '''        audit["selected"] = {\n            "id": video_id,\n''',
    '''        global OPENING_FIRST_VISUAL_SIGNATURE\n        OPENING_FIRST_VISUAL_SIGNATURE = visual_signature(\n            scene.get("keyword", ""),\n            _page_slug(candidate.get("page_url")),\n        )\n\n        audit["selected"] = {\n            "id": video_id,\n''',
    "remember strict opening visual",
)
visual_text = _replace_once(
    visual_text,
    '''def fetch_early_retention_pexels_video(scene):\n    """Use the existing Hook metadata strict gate for the 2~5s scene."""\n\n    original_query = str(scene.get("keyword", "")).strip()\n''',
    '''def fetch_early_retention_pexels_video(scene):\n    """Use the existing Hook metadata strict gate plus opening progression."""\n\n    original_query = str(scene.get("keyword", "")).strip()\n    concept_ok, concept_reason = validate_reversal_query(scene)\n    if not concept_ok:\n        raise RuntimeError(\n            "First-5 visual concept lock rejected scene2 query: "\n            f"{concept_reason}"\n        )\n''',
    "early visual concept lock",
)
visual_text = _replace_once(
    visual_text,
    '''        strict = [item for item in scored if _passes_strict_gate(item)]\n        if strict:\n            best = strict[0]\n''',
    '''        strict = [item for item in scored if _passes_strict_gate(item)]\n        progressive = []\n        for item in strict:\n            candidate = item["candidate"]\n            second_signature = visual_signature(\n                search_query,\n                _page_slug(candidate.get("page_url")),\n            )\n            progression_ok, progression_reason = progression_passes(\n                OPENING_FIRST_VISUAL_SIGNATURE,\n                second_signature,\n            )\n            if progression_ok:\n                progressive.append(item)\n            else:\n                print(\n                    "[RETENTION5] opening_candidate_rejected "\n                    f"id={candidate.get('id')} reason={progression_reason}"\n                )\n\n        if progressive:\n            best = progressive[0]\n''',
    "opening progression candidate filter",
)
visual_text = _replace_once(
    visual_text,
    '''    print(\n        "[RETENTION5] early_visual_strict=false "\n        "fallback=legacy_pexels"\n    )\n    return fetch_pexels_video(original_query)\n''',
    '''    if OPENING_FIRST_VISUAL_SIGNATURE:\n        raise RuntimeError(\n            "First-5 opening progression candidate not found; "\n            "refusing visually repetitive scene2 fallback"\n        )\n\n    print(\n        "[RETENTION5] early_visual_strict=false "\n        "fallback=legacy_pexels"\n    )\n    return fetch_pexels_video(original_query)\n''',
    "opening progression fallback guard",
)
visual_path.write_text(visual_text, encoding="utf-8")

print("✅ First-5 visual concept lock + opening progression hotfix applied")
