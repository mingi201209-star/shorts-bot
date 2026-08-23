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
    scene_alias_replacement = '''    if not str(result.get("text", "")).strip():\n        for key in (\n            "narration", "narration_text", "narration_line", "narration_ko",\n            "voiceover", "voiceover_text", "spoken_text", "spoken_line",\n            "speech", "speech_text", "dialogue", "dialogue_text",\n            "script", "script_text", "line", "sentence", "utterance",\n        ):\n            value = result.get(key)\n            if isinstance(value, str) and value.strip():\n                result["text"] = value.strip()\n                break\n\n    # Some writer models emit semantically named narration fields that are not\n    # stable aliases. Recover only from keys whose names clearly denote spoken\n    # narration, while explicitly excluding visual/search metadata.\n    if not str(result.get("text", "")).strip():\n        positive_tokens = (\n            "narration", "voiceover", "spoken", "speech", "dialogue",\n            "script", "utterance", "sentence", "line", "text",\n        )\n        negative_tokens = (\n            "visual", "image", "shot", "keyword", "query", "search",\n            "title", "description", "goal", "prompt",\n        )\n        candidates = []\n        for raw_key, raw_value in result.items():\n            if not isinstance(raw_value, str) or not raw_value.strip():\n                continue\n            key = str(raw_key).strip().lower().replace("-", "_").replace(" ", "_")\n            if any(token in key for token in negative_tokens):\n                continue\n            if any(token in key for token in positive_tokens):\n                candidates.append(raw_value.strip())\n        if len(candidates) == 1:\n            result["text"] = candidates[0]\n\n'''
    text = replace_once(text, scene_alias_marker, scene_alias_replacement, "scene text aliases")

    helper_marker = '''\ndef _normalize_script_contracts_without_api(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:\n'''
    helper_replacement = '''\ndef _deterministic_visual_goal(\n    scene: Dict[str, Any],\n    contract: Dict[str, Any],\n    index: int,\n) -> str:\n    \"\"\"Fill only missing/too-short visual metadata from already-approved scene data.\"\"\"\n    current = str(scene.get(\"visual_goal\", \"\")).strip()\n    if len(current) >= 8:\n        return current\n\n    keyword = str(scene.get(\"keyword\", \"\")).strip()\n    narration = str(\n        scene.get(\"text\")\n        or contract.get(\"locked_text\")\n        or \"\"\n    ).strip()\n\n    if narration:\n        return f\"{keyword} 중심 장면: {narration}\".strip()\n\n    role = str(contract.get(\"role\", \"\")).strip() or f\"scene {index}\"\n    return f\"{keyword} 중심으로 {role} 내용을 시각적으로 설명하는 장면\".strip()\n\n\ndef _normalize_script_contracts_without_api(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:\n'''
    text = replace_once(text, helper_marker, helper_replacement, "helper")

    counters_marker = '''    changed_keywords = 0\n    changed_endings = 0\n'''
    counters_replacement = '''    changed_keywords = 0\n    changed_visual_goals = 0\n    changed_endings = 0\n'''
    text = replace_once(text, counters_marker, counters_replacement, "counters")

    keyword_marker = '''        if scene[\"keyword\"] != before_keyword:\n            changed_keywords += 1\n        if not contract.get(\"locked\"):\n'''
    keyword_replacement = '''        if scene[\"keyword\"] != before_keyword:\n            changed_keywords += 1\n\n        before_visual_goal = str(scene.get(\"visual_goal\", \"\")).strip()\n        scene[\"visual_goal\"] = _deterministic_visual_goal(scene, contract, index)\n        if scene[\"visual_goal\"] != before_visual_goal:\n            changed_visual_goals += 1\n\n        if not contract.get(\"locked\"):\n'''
    text = replace_once(text, keyword_marker, keyword_replacement, "normalization")

    log_marker = '''    if changed_keywords or changed_endings:\n        print(\n            \"🧩 V2 deterministic contract normalization without API: \"\n            f\"keywords={changed_keywords} endings={changed_endings}\"\n        )\n'''
    log_replacement = '''    if changed_keywords or changed_visual_goals or changed_endings:\n        print(\n            \"🧩 V2 deterministic contract normalization without API: \"\n            f\"keywords={changed_keywords} visual_goals={changed_visual_goals} \"\n            f\"endings={changed_endings}\"\n        )\n'''
    text = replace_once(text, log_marker, log_replacement, "logging")

    RUNNER_PATH.write_text(text, encoding="utf-8")
    print("✅ Script Engine V2 deterministic text-alias + visual_goal recovery hotfix applied")


if __name__ == "__main__":
    main()
