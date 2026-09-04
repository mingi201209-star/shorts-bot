from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# EARLY_VERIFIED_ASSET_PRESENTATION_V1"


_HELPERS = r'''

# EARLY_VERIFIED_ASSET_PRESENTATION_V1
# Keep #268 physical asset reuse intact while giving an early question beat a
# deterministic, semantically-derived presentation distinct from Scene 1.
def _verified_question_presentation(scene, cached):
    scene = scene if isinstance(scene, dict) else {}
    cached = cached if isinstance(cached, dict) else {}
    if not _is_question_subject_beat(scene):
        return None

    contract = _canonical_still_contract(scene)
    required = {
        str(value or "").strip().lower()
        for value in cached.get("required_subject_groups") or []
        if str(value or "").strip()
    }
    trusted_terms = {
        str(value or "").strip().lower().replace("-", " ")
        for value in (
            list(contract.get("trusted_visual_discriminators") or [])
            + list(contract.get("subject_proof_priority") or [])
        )
        if str(value or "").strip()
    }

    # This presentation policy is intentionally narrow: only the verified
    # rear-nozzle/chevron physical subject that caused the HUMAN-QA repetition.
    # Generic still reuse and explanatory Scene 3-5 assets remain untouched.
    has_rear_structure = bool(trusted_terms & {"rear", "trailing", "nozzle", "nacelle", "edge"})
    has_edge_feature = bool(required & {"chevron"}) and bool(
        trusted_terms & {"chevron", "serrated", "sawtooth", "edge"}
    )
    if not (has_rear_structure and has_edge_feature):
        return None

    effective = cached.get("effective_subject_groups") or {}
    raw = cached.get("raw_visible_subject_groups") or {}
    if not bool(effective.get("engine", False)):
        return None
    if not bool(raw.get("chevron", False)):
        return None

    # The generated canonical still contract already places the verified proof
    # component large and central. A bounded center-only inspection zoom changes
    # perceptual composition without inventing an unverified spatial coordinate.
    return {
        "presentation_id": "QUESTION_FEATURE_INSPECTION_CENTER_V1",
        "scene_role": "question",
        "visual_beat": "inspect_verified_feature",
        "subject_focal_region": "verified_rear_nozzle_chevron_center",
        "safe_crop_constraint": "center_only_max_1.12x",
        "zoom_start": 1.05,
        "zoom_max": 1.12,
        "zoom_step": 0.0010,
        "pan_x": "center",
        "pan_y": "center",
    }


def _still_presentation_identity(presentation=None):
    presentation = dict(presentation or {})
    if not presentation:
        return (
            "ESTABLISH_SUBJECT_CENTER_V1",
            1.00,
            1.08,
            0.0007,
            "center",
            "center",
        )
    return (
        str(presentation.get("presentation_id") or ""),
        round(float(presentation.get("zoom_start", 1.0)), 4),
        round(float(presentation.get("zoom_max", 1.08)), 4),
        round(float(presentation.get("zoom_step", 0.0007)), 5),
        str(presentation.get("pan_x") or "center"),
        str(presentation.get("pan_y") or "center"),
    )


def _assert_early_presentation_distinct(presentation):
    identity = _still_presentation_identity(presentation)
    baseline = _still_presentation_identity(None)
    if identity == baseline:
        raise RuntimeError("early verified-asset presentation repetition detected")
    zoom_start = float(presentation.get("zoom_start", 0.0))
    zoom_max = float(presentation.get("zoom_max", 0.0))
    zoom_step = float(presentation.get("zoom_step", 0.0))
    if not (1.0 <= zoom_start <= 1.06):
        raise RuntimeError("question presentation unsafe zoom_start")
    if not (zoom_start < zoom_max <= 1.12):
        raise RuntimeError("question presentation excessive zoom")
    if not (0.0 < zoom_step <= 0.0012):
        raise RuntimeError("question presentation unsafe zoom_step")
    if presentation.get("pan_x") != "center" or presentation.get("pan_y") != "center":
        raise RuntimeError("question presentation must keep verified focal region centered")
    return identity
'''


_MOTION_FUNCTION = r'''def _motion_clip(image_path, output_path, duration, presentation=None):
    duration = max(1.0, float(duration))
    fade = min(0.35, duration / 4.0)
    fade_out_start = max(0.0, duration - fade)
    presentation = dict(presentation or {})
    if presentation:
        _assert_early_presentation_distinct(presentation)
        zoom_start = float(presentation["zoom_start"])
        zoom_max = float(presentation["zoom_max"])
        zoom_step = float(presentation["zoom_step"])
        # zoompan emits one output frame per repeated still input (d=1). Use
        # pzoom to carry the prior input-frame zoom; plain zoom resets here and
        # makes the Scene-2 inspection presentation effectively static.
        zoom_expr = (
            f"if(eq(on,0),{zoom_start:.4f},min(max(zoom,pzoom)+{zoom_step:.4f},{zoom_max:.4f}))"
        )
    else:
        zoom_expr = "min(zoom+0.0007,1.08)"
    vf = (
        "scale=1280:1920:force_original_aspect_ratio=increase,"
        "crop=1280:1920,"
        f"zoompan=z='{zoom_expr}':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade:.3f},"
        "format=yuv420p"
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
            "-t", f"{duration:.3f}", "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("still-image motion ffmpeg failed: " + result.stderr[-1200:])
    if not Path(output_path).exists():
        raise RuntimeError("still-image motion output missing")
'''


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} mismatch count={count}")
    return text.replace(old, new, 1)


def main():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    if "QUESTION_SUBJECT_REUSE_RUN_33371268494_V1" not in text:
        raise RuntimeError("early presentation patch requires #268 verified subject reuse")

    helper_anchor = "\ndef _reuse_verified_question_subject(scene, *, output_path, duration, trigger_reason):\n"
    text = _replace_once(
        text,
        helper_anchor,
        _HELPERS + helper_anchor,
        "early presentation helper anchor",
    )

    motion_start = text.find("def _motion_clip(image_path, output_path, duration):")
    motion_end = text.find("\ndef _verify_motion_clip(", motion_start)
    if motion_start < 0 or motion_end < 0:
        raise RuntimeError("early presentation motion function anchor missing")
    text = text[:motion_start] + _MOTION_FUNCTION + text[motion_end:]

    reuse_start = text.find("def _reuse_verified_question_subject(")
    reuse_end = text.find("\ndef ", reuse_start + 1)
    if reuse_start < 0:
        raise RuntimeError("question reuse function missing")
    if reuse_end < 0:
        reuse_end = len(text)
    section = text[reuse_start:reuse_end]
    call_anchor = "        _motion_clip(image_path, output_path, duration)\n"
    call_replacement = '''        presentation = _verified_question_presentation(scene, cached)\n        if presentation is None:\n            # No semantic presentation policy exists for this subject; preserve\n            # the established #268 behavior rather than inventing a transform.\n            _motion_clip(image_path, output_path, duration)\n            presentation_identity = _still_presentation_identity(None)\n        else:\n            presentation_identity = _assert_early_presentation_distinct(presentation)\n            _motion_clip(image_path, output_path, duration, presentation=presentation)\n'''
    section = _replace_once(section, call_anchor, call_replacement, "question reuse motion call")

    result_anchor = '''            "verification_evidence_reused": True,\n'''
    result_replacement = result_anchor + '''            "presentation_id": presentation_identity[0],\n            "presentation_identity": list(presentation_identity),\n            "presentation_focal_region": str((presentation or {}).get("subject_focal_region") or "verified_subject_center"),\n'''
    section = _replace_once(section, result_anchor, result_replacement, "question reuse presentation lineage")
    text = text[:reuse_start] + section + text[reuse_end:]

    path.write_text(text.rstrip() + "\n\n" + MARKER + "\n", encoding="utf-8")
    print("✅ Early verified-asset question presentation differentiation installed; zero new calls")


if __name__ == "__main__":
    main()
