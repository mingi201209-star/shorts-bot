from pathlib import Path

path = Path("quality/final_visual_director.py")
text = path.read_text(encoding="utf-8")
if "subtitle_unresolvable" not in text:
    anchor = '''        if bool(obs.get("subtitle_obstruction")):
            issues.append({"scene_index": idx, "severity": "high", "type": "subtitle_obstruction", "reason": "subtitle overlaps protected visual region", "repair": "subtitle_relocation"})
'''
    replacement = '''        if bool(obs.get("subtitle_all_positions_unsafe")):
            issues.append({"scene_index": idx, "severity": "high", "type": "subtitle_unresolvable", "reason": "all calibrated subtitle positions exceed safe ceiling", "repair": "hold"})
        elif bool(obs.get("subtitle_obstruction")):
            issues.append({"scene_index": idx, "severity": "high", "type": "subtitle_obstruction", "reason": "calibrated current subtitle position is unsafe and a safe alternative exists", "repair": "subtitle_relocation"})
'''
    if anchor not in text:
        raise RuntimeError("subtitle director anchor missing")
    text = text.replace(anchor, replacement, 1)
    # Unresolvable subtitle defects must never enter visual scene regeneration.
    anchor2 = '''    issues = list(qa_result.get("issues") or [])
    if not issues:
'''
    replacement2 = '''    issues = list(qa_result.get("issues") or [])
    if any(x.get("type") == "subtitle_unresolvable" for x in issues):
        return {"status": "HOLD", "reason": "VISUAL_QUALITY_SUBTITLE_UNRESOLVABLE", "scene_indexes": [], "subtitle_only": []}
    if not issues:
'''
    if anchor2 not in text:
        raise RuntimeError("repair plan anchor missing")
    text = text.replace(anchor2, replacement2, 1)
    path.write_text(text, encoding="utf-8")
print("VISUAL_QUALITY_SUBTITLE_DIRECTOR_V1 installed")
