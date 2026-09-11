from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Production uses content.script_generator_router -> Script Engine V2.  Run
# 34616204901 proved that improving only the legacy generator does not protect
# the actual Writer path, so install the Human Quality floor at the V2 boundary.

router_path = Path("content/script_generator_router.py")
router_text = router_path.read_text(encoding="utf-8")
router_text = append_once(
    router_text,
    "RUN_34616204901_V2_OPENING_PROJECTION_V1",
    r'''
# RUN_34616204901_V2_OPENING_PROJECTION_V1
from quality.human_quality_floor import normalize_aircraft_window_opening as _hq_normalize_aircraft_window_opening

_hq_previous_normalize_locked_candidate_narration = _normalize_locked_candidate_narration


def _normalize_locked_candidate_narration(candidate):
    result = _hq_previous_normalize_locked_candidate_narration(candidate)
    normalized = _hq_normalize_aircraft_window_opening(result)
    if normalized != result:
        print("🧩 Human Quality opening normalized before Script Engine V2")
    return normalized
''',
)
router_path.write_text(router_text, encoding="utf-8")


engine_path = Path("content/script_engine_v2.py")
engine_text = engine_path.read_text(encoding="utf-8")
engine_text = append_once(
    engine_text,
    "RUN_34616204901_V2_WRITER_RULES_V1",
    r'''
# RUN_34616204901_V2_WRITER_RULES_V1
_hq_previous_writer_payload = writer_payload


def writer_payload(candidate, plan):
    payload = _hq_previous_writer_payload(candidate, plan)
    rules = dict(payload.get("rules") or {})
    rules.update({
        "natural_concise_korean": True,
        "avoid_repeating_full_subject_phrase_in_adjacent_scenes": True,
        "avoid_hype_beyond_grounded_fact_strength": True,
        "prefer_direct_subject_verb_sentences": True,
    })
    payload["rules"] = rules
    return payload
''',
)
engine_path.write_text(engine_text, encoding="utf-8")


validation_path = Path("content/script_engine_v2_validation.py")
validation_text = validation_path.read_text(encoding="utf-8")
validation_text = append_once(
    validation_text,
    "RUN_34616204901_V2_OPENING_VALIDATION_V1",
    r'''
# RUN_34616204901_V2_OPENING_VALIDATION_V1
from quality.human_quality_floor import opening_repeat_issue as _hq_opening_repeat_issue

_hq_previous_validate_script_v2 = validate_script_v2


def validate_script_v2(script, plan):
    result = _hq_previous_validate_script_v2(script, plan)
    scenes = script.get("scenes", []) if isinstance(script, dict) else []
    issue = _hq_opening_repeat_issue(scenes)
    if not issue:
        return result

    failures = list(result.get("failures") or [])
    marker = {"scene_index": 2, "reason": f"human-quality opening: {issue}"}
    if marker not in failures:
        failures.append(marker)

    failed_indexes = sorted({
        int(item["scene_index"])
        for item in failures
        if isinstance(item, dict) and isinstance(item.get("scene_index"), int)
    })
    return {
        "valid": False,
        "failures": failures,
        "failed_scene_indexes": failed_indexes,
        "reasons": [str(item.get("reason", "")) for item in failures if isinstance(item, dict)],
    }
''',
)
validation_path.write_text(validation_text, encoding="utf-8")

print("✅ Run 34616204901 Human Quality floor wired into Script Engine V2 production path")
