"""Finish Visual Quality V1 production wiring without new API/provider calls."""
from pathlib import Path

path = Path("main.py")
text = path.read_text(encoding="utf-8")
if "VISUAL_QUALITY_V1_SUBTITLE_SIGNAL" not in text:
    old = '''                observations.append({
                    "scene_index": scene_index, "role": role,
                    "source_id": item.get("source_id", ""),
                    "start_sec": round(elapsed, 3), "end_sec": round(elapsed + duration, 3),
                    "scores": {
'''
    new = '''                # VISUAL_QUALITY_V1_SUBTITLE_SIGNAL: inspect the same base footage
                # used by the renderer, with the existing subtitle region scorer only.
                from quality.subtitle_safety import assess_subtitle_placement, position_name_for_y
                rendered_scene = scene_clips[scene_index]
                layers = list(getattr(rendered_scene, "clips", []) or [])
                base_footage = layers[0] if layers else rendered_scene
                subtitle_y = None
                if len(layers) > 1:
                    try:
                        subtitle_y = layers[1].pos(0)[1]
                    except Exception:
                        subtitle_y = None
                current_position = position_name_for_y(subtitle_y, hook_mode=(role == "hook"))
                subtitle_safety = assess_subtitle_placement(
                    base_footage, current_position=current_position, hook_mode=(role == "hook")
                )
                observations.append({
                    "scene_index": scene_index, "role": role,
                    "source_id": item.get("source_id", ""),
                    "start_sec": round(elapsed, 3), "end_sec": round(elapsed + duration, 3),
                    "subtitle_safety": subtitle_safety,
                    "subtitle_obstruction": bool(subtitle_safety.get("subtitle_obstruction")),
                    "subtitle_all_positions_unsafe": bool(subtitle_safety.get("subtitle_all_positions_unsafe")),
                    "scores": {
'''
    if old not in text:
        raise RuntimeError("Visual Quality subtitle observation anchor missing")
    text = text.replace(old, new, 1)

    old = '''            if repair.get("subtitle_only") and not repair.get("scene_indexes"):
                # Never throw away a good visual for a subtitle-only defect.
                raise RuntimeError("VISUAL_QUALITY_SUBTITLE_RELOCATION_REQUIRED")
            repair_indexes = list(repair.get("scene_indexes") or [])[:2]
'''
    new = '''            subtitle_indexes = list(repair.get("subtitle_only") or [])
            if subtitle_indexes:
                # Subtitle-only repair reuses the exact existing footage/audio/timing.
                # No create_scene/provider/TTS/API call is allowed on this path.
                from moviepy.editor import CompositeVideoClip
                from quality.subtitle_safety import position_y
                for subtitle_index in subtitle_indexes:
                    obs = _visual_quality_observations()[subtitle_index]
                    safety = dict(obs.get("subtitle_safety") or {})
                    recommended = safety.get("recommended_position")
                    if not recommended:
                        raise RuntimeError("VISUAL_QUALITY_SUBTITLE_UNRESOLVABLE")
                    scene_clip = scene_clips[subtitle_index]
                    layers = list(getattr(scene_clip, "clips", []) or [])
                    if len(layers) < 2:
                        raise RuntimeError("VISUAL_QUALITY_SUBTITLE_UNRESOLVABLE")
                    new_y = position_y(recommended, hook_mode=bool(safety.get("hook_mode")))
                    relocated = [layers[0]] + [layer.set_position(("center", new_y)) for layer in layers[1:]]
                    rebuilt = CompositeVideoClip(relocated, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
                    rebuilt = rebuilt.set_audio(scene_clip.audio).set_duration(scene_clip.duration)
                    scene_clips[subtitle_index] = rebuilt
                    print(
                        f"[SubtitleSafety] relocation={safety.get('selected_position')}->{recommended} "
                        f"scene={subtitle_index} risk={safety.get('selected_risk')} ceiling={safety.get('safe_ceiling')}"
                    )
            repair_indexes = list(repair.get("scene_indexes") or [])[:2]
'''
    if old not in text:
        raise RuntimeError("Visual Quality subtitle repair anchor missing")
    text = text.replace(old, new, 1)

    old = '''            if not repair_indexes:
                raise RuntimeError("VISUAL_QUALITY_DIRECTOR_HOLD no concrete repairable scene")
'''
    new = '''            if not repair_indexes and not subtitle_indexes:
                raise RuntimeError("VISUAL_QUALITY_DIRECTOR_HOLD no concrete repairable scene")
'''
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")

print("VISUAL_QUALITY_V1_SUBTITLE_SIGNAL installed")
