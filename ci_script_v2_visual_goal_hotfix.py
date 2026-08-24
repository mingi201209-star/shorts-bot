from pathlib import Path


RUNNER_PATH = Path("content/script_engine_v2_runner.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"V2 visual-goal {label} marker mismatch: {count}")
    return text.replace(marker, replacement, 1)


def main():
    text = RUNNER_PATH.read_text(encoding="utf-8")

    scene_alias_marker = '''    if not str(result.get("text", "")).strip():\n        for key in ("narration", "narration_text", "voiceover", "script", "line", "sentence"):\n            value = result.get(key)\n            if isinstance(value, str) and value.strip():\n                result["text"] = value.strip()\n                break\n\n'''
    scene_alias_replacement = '''    def _spoken_string(value: Any) -> str:\n        if isinstance(value, str) and value.strip():\n            return value.strip()\n        if isinstance(value, dict):\n            for nested_key in (\n                "text", "content", "body", "line", "sentence", "utterance",\n                "narration", "voiceover", "spoken_text", "speech", "dialogue",\n            ):\n                nested = value.get(nested_key)\n                if isinstance(nested, str) and nested.strip():\n                    return nested.strip()\n        return ""\n\n    if not str(result.get("text", "")).strip():\n        for key in (\n            "narration", "narration_text", "narration_line", "narration_ko",\n            "voiceover", "voiceover_text", "spoken_text", "spoken_line",\n            "speech", "speech_text", "dialogue", "dialogue_text",\n            "script", "script_text", "line", "sentence", "utterance",\n            "content", "body",\n        ):\n            value = _spoken_string(result.get(key))\n            if value:\n                result["text"] = value\n                break\n\n    # Some writer/repair models emit semantically named narration fields,\n    # sometimes as one-level nested objects. Recover only from keys whose names\n    # clearly denote spoken narration, while excluding visual/search metadata.\n    if not str(result.get("text", "")).strip():\n        positive_tokens = (\n            "narration", "voiceover", "spoken", "speech", "dialogue",\n            "script", "utterance", "sentence", "line", "text",\n        )\n        negative_tokens = (\n            "visual", "image", "shot", "keyword", "query", "search",\n            "title", "description", "goal", "prompt", "role", "type",\n            "label", "id", "index", "number",\n        )\n        candidates = []\n        for raw_key, raw_value in result.items():\n            key = str(raw_key).strip().lower().replace("-", "_").replace(" ", "_")\n            if any(token in key for token in negative_tokens):\n                continue\n            if not any(token in key for token in positive_tokens):\n                continue\n            value = _spoken_string(raw_value)\n            if value:\n                candidates.append(value)\n        candidates = list(dict.fromkeys(candidates))\n        if len(candidates) == 1:\n            result["text"] = candidates[0]\n\n'''
    text = replace_once(text, scene_alias_marker, scene_alias_replacement, "scene text aliases")

    repair_marker = '''    result = deepcopy(script)\n    scenes = result.get("scenes") or []\n    repairs = response.get("repairs") or []\n    if not isinstance(repairs, list):\n        raise ValueError("local repair response repairs must be a list")\n'''
    repair_replacement = '''    result = deepcopy(script)\n    scenes = result.get("scenes") or []\n\n    normalized_response = response if isinstance(response, dict) else {}\n    repairs = normalized_response.get("repairs")\n    if not isinstance(repairs, list):\n        for envelope_key in ("result", "output", "data", "response", "repair_result"):\n            nested = normalized_response.get(envelope_key)\n            if isinstance(nested, dict) and isinstance(nested.get("repairs"), list):\n                repairs = nested.get("repairs")\n                print(f"🧩 V2 local-repair envelope normalized without API: {envelope_key}")\n                break\n    if not isinstance(repairs, list):\n        for alias_key in ("scene_repairs", "changes", "fixed_scenes", "items"):\n            value = normalized_response.get(alias_key)\n            if isinstance(value, list):\n                repairs = value\n                print(f"🧩 V2 local-repair list alias normalized without API: {alias_key}")\n                break\n    if repairs is None:\n        repairs = []\n    if not isinstance(repairs, list):\n        raise ValueError("local repair response repairs must be a list")\n'''
    text = replace_once(text, repair_marker, repair_replacement, "local repair envelope")

    ending_marker = '''    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n)\n'''
    ending_replacement = '''    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n    (r"가져온다(?=[.!?…]*$)", "가져옵니다"),\n    (r"이어진다(?=[.!?…]*$)", "이어집니다"),\n    (r"나타난다(?=[.!?…]*$)", "나타납니다"),\n    (r"생긴다(?=[.!?…]*$)", "생깁니다"),\n    (r"커진다(?=[.!?…]*$)", "커집니다"),\n    (r"작아진다(?=[.!?…]*$)", "작아집니다"),\n    (r"바뀐다(?=[.!?…]*$)", "바뀝니다"),\n    (r"유지된다(?=[.!?…]*$)", "유지됩니다"),\n    (r"향상시킨다(?=[.!?…]*$)", "향상시킵니다"),\n)\n'''
    text = replace_once(text, ending_marker, ending_replacement, "formal endings")

    helper_marker = '''\ndef _normalize_script_contracts_without_api(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:\n'''
    helper_replacement = '''\ndef _deterministic_missing_text(contract: Dict[str, Any]) -> str:\n    \"\"\"Recover a missing unlocked narration line from approved contract concepts only.\"\"\"\n    concepts = [str(item).strip() for item in (contract.get(\"required_concepts\") or []) if str(item).strip()]\n    if not concepts:\n        return \"\"\n    concept = concepts[0].rstrip(\".!?\")\n    role = str(contract.get(\"role\", \"\"))\n    if role == \"causal_clue\":\n        return f\"원인의 첫 단서는 {concept}입니다.\"\n    if role.startswith(\"mechanism_\"):\n        return f\"이 과정의 핵심은 {concept}입니다.\"\n    if role == \"consequence\":\n        return f\"이 과정은 {concept}과 연결됩니다.\"\n    return f\"핵심은 {concept}입니다.\"\n\n\ndef _deterministic_visual_goal(\n    scene: Dict[str, Any],\n    contract: Dict[str, Any],\n    index: int,\n) -> str:\n    \"\"\"Fill only missing/too-short visual metadata from already-approved scene data.\"\"\"\n    current = str(scene.get(\"visual_goal\", \"\")).strip()\n    if len(current) >= 8:\n        return current\n\n    keyword = str(scene.get(\"keyword\", \"\")).strip()\n    narration = str(\n        scene.get(\"text\")\n        or contract.get(\"locked_text\")\n        or \"\"\n    ).strip()\n\n    if narration:\n        return f\"{keyword} 중심 장면: {narration}\".strip()\n\n    role = str(contract.get(\"role\", \"\")).strip() or f\"scene {index}\"\n    return f\"{keyword} 중심으로 {role} 내용을 시각적으로 설명하는 장면\".strip()\n\n\ndef _normalize_script_contracts_without_api(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:\n'''
    text = replace_once(text, helper_marker, helper_replacement, "helper")

    counters_marker = '''    changed_keywords = 0\n    changed_endings = 0\n'''
    counters_replacement = '''    changed_keywords = 0\n    changed_visual_goals = 0\n    changed_missing_text = 0\n    changed_endings = 0\n'''
    text = replace_once(text, counters_marker, counters_replacement, "counters")

    keyword_marker = '''        if scene[\"keyword\"] != before_keyword:\n            changed_keywords += 1\n        if not contract.get(\"locked\"):\n'''
    keyword_replacement = '''        if scene[\"keyword\"] != before_keyword:\n            changed_keywords += 1\n\n        before_visual_goal = str(scene.get(\"visual_goal\", \"\")).strip()\n        scene[\"visual_goal\"] = _deterministic_visual_goal(scene, contract, index)\n        if scene[\"visual_goal\"] != before_visual_goal:\n            changed_visual_goals += 1\n\n        if not contract.get(\"locked\") and not str(scene.get(\"text\", \"\")).strip():\n            fallback_text = _deterministic_missing_text(contract)\n            if fallback_text:\n                scene[\"text\"] = fallback_text\n                changed_missing_text += 1\n\n        if not contract.get(\"locked\"):\n'''
    text = replace_once(text, keyword_marker, keyword_replacement, "normalization")

    log_marker = '''    if changed_keywords or changed_endings:\n        print(\n            \"🧩 V2 deterministic contract normalization without API: \"\n            f\"keywords={changed_keywords} endings={changed_endings}\"\n        )\n'''
    log_replacement = '''    if changed_keywords or changed_visual_goals or changed_missing_text or changed_endings:\n        print(\n            \"🧩 V2 deterministic contract normalization without API: \"\n            f\"keywords={changed_keywords} visual_goals={changed_visual_goals} \"\n            f\"missing_text={changed_missing_text} endings={changed_endings}\"\n        )\n'''
    text = replace_once(text, log_marker, log_replacement, "logging")

    RUNNER_PATH.write_text(text, encoding="utf-8")
    print("✅ Script Engine V2 nested aliases + repair envelope + visual_goal + missing-text recovery hotfix applied")


if __name__ == "__main__":
    main()
